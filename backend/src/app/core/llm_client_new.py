"""
Improved LLM client.

Key upgrades over llm_client.py:
- System / user role separation on every call (better instruction-following)
- Embedding-based semantic deduplication (Yandex Embeddings REST API + cosine similarity)
  so conceptually-identical questions are never repeated even when phrased differently
- Adaptive difficulty: nudge wording up/down based on running average score
- Question-type rotation: conceptual → practical → debug → conceptual …
  so the candidate never gets five conceptual questions in a row
- Anchored scoring rubric in evaluate_answer (what 3 / 6 / 9 actually means)
- Score-trend analysis in generate_session_summary (improving / declining / stable)
- Pydantic output validation + single retry on JSON parse failure

Backward-compatible with the original interface.
New optional parameters (avg_score, next_question_type, asked_qa_history,
prior_avg_score) are ignored by the old InterviewService; update the service
to pass them in order to unlock adaptive behaviour.
"""

import json
import logging
import math
from typing import Any, Dict, List, Literal, Optional

import httpx
import openai
from pydantic import BaseModel, ValidationError

from src.app.config import settings
from src.app.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


# Output schemas 

class _ScoreModel(BaseModel):
    correctness: float
    optimality: float
    complexity: float
    explanation: float
    gaps: float


class _QuestionModel(BaseModel):
    text: str
    topic: str
    hints: List[str] = []
    question_type: Literal["conceptual", "practical", "debug"] = "conceptual"


class _EvaluationModel(BaseModel):
    score: _ScoreModel
    feedback: str
    weak_topics: List[str] = []


class _SummaryModel(BaseModel):
    overall: str
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []


# Static prompt content 

_LEVEL_GUIDANCE: Dict[str, str] = {
    "junior": (
        "- Структуры данных: массивы, хеш-таблицы, множества, стеки, очереди — нетривиальное применение.\n"
        "- Алгоритмы: двоичный поиск, два указателя, скользящее окно, базовая рекурсия с мемоизацией.\n"
        "- Строки: анаграммы, палиндромы, перестановки, парсинг.\n"
        "- Сортировка: реализация merge sort / quick sort, поиск k-го элемента.\n"
        "- Математика: простые числа, НОД/НОК, Фибоначчи (итеративно и с мемоизацией).\n"
        "- НЕ задавай: «сложи/вычти числа», простые if/else, однострочные функции."
    ),
    "middle": (
        "- Алгоритмы: BFS/DFS, топологическая сортировка, базовое DP (LCS, рюкзак), деревья (BST).\n"
        "- Конкурентность: потоки, блокировки, базовые паттерны параллелизма для стека.\n"
        "- Специфика стека (примеры): Python — asyncio, генераторы, декораторы, SQLAlchemy;\n"
        "  JS/TS — event loop, Promises, React hooks, прототипы;\n"
        "  Go — горутины, каналы, defer/panic/recover, interfaces.\n"
        "- Проектирование: SOLID, паттерны GoF, REST API дизайн.\n"
        "- Оптимизация: O(n log n) решения, кеширование, N+1 в ORM."
    ),
    "senior": (
        "- Системный дизайн: rate limiter, кеширующий слой, очереди, балансировщик — trade-offs обязательны.\n"
        "- Сложные алгоритмы: продвинутое DP, сегментные деревья, union-find, Дейкстра, A*.\n"
        "- Конкурентность: гонки данных, дедлоки, lock-free структуры, compare-and-swap.\n"
        "- Архитектура: микросервисы vs монолит, event sourcing, CQRS, saga pattern.\n"
        "- Производительность: профилирование, GC паузы, EXPLAIN ANALYZE, индексы.\n"
        "- Глубина стека: GIL, V8 JIT, Go scheduler, JVM GC.\n"
        "- Code review: найди баги/антипаттерны, объясни проблему и исправление."
    ),
}

_SCORE_RUBRIC = """
ШКАЛА ОЦЕНОК — применяй строго, не завышай:
• 9-10  Эталонный ответ: охватывает edge cases, объясняет trade-offs, без неточностей.
• 7-8   Хороший ответ: концепция верна, есть мелкие упущения.
• 5-6   Удовлетворительно: базовое понимание есть, важные детали упущены.
• 3-4   Слабо: концепция в целом понята, но ответ поверхностный или частично неверный.
• 1-2   Неудовлетворительно: серьёзные ошибки или непонимание темы.
Для «gaps»: 10 = пробелов нет, 1 = критические пробелы в знаниях."""

_QUESTION_TYPE_ROTATION: List[str] = ["conceptual", "practical", "debug"]

_QUESTION_TYPE_DESCRIPTIONS = {
    "conceptual": (
        "Концептуальный вопрос: «Как работает X?», «В чём разница между X и Y?», "
        "«Когда ты выберешь X вместо Y?»"
    ),
    "practical": (
        "Небольшая практическая задача: написать, исправить или объяснить 5–15 строк кода "
        "по одной конкретной концепции."
    ),
    "debug": (
        "Задача на рассуждение / отладку: «Что произойдёт, если…», "
        "«Почему этот код ведёт себя так?», найди баг в сниппете."
    ),
}


# Utilities 

def _strip_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _score_avg(score: Dict[str, float]) -> float:
    vals = list(score.values())
    return sum(vals) / len(vals) if vals else 5.0


def _difficulty_hint(avg_score: Optional[float]) -> str:
    if avg_score is None:
        return ""
    if avg_score >= 7.5:
        return (
            "\nАДАПТАЦИЯ СЛОЖНОСТИ: кандидат набирает в среднем {:.1f}/10 — "
            "задай более сложный или нюансированный вопрос, чем обычно для этого уровня.".format(avg_score)
        )
    if avg_score <= 4.5:
        return (
            "\nАДАПТАЦИЯ СЛОЖНОСТИ: кандидат набирает в среднем {:.1f}/10 — "
            "задай более доступный вопрос в рамках уровня, фокусируясь на фундаменте.".format(avg_score)
        )
    return ""


# Main client

class LLMClientNew(openai.AsyncOpenAI):
    """Drop-in replacement for LLMClient with enhanced question generation."""

    def __init__(
        self,
        api_key: str = settings.YANDEX_API_KEY,
        base_url: str = settings.YANDEX_API_URL,
        project: str = settings.YANDEX_CLOUD_CATALOG_ID,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_headers={"x-folder-id": project},
        )
        # In-process embedding cache: question text → embedding vector
        self._embedding_cache: Dict[str, List[float]] = {}

    # Embedding helpers 

    async def _fetch_embedding(self, text: str) -> Optional[List[float]]:
        """
        Calls the Yandex Embeddings REST API.
        Returns None on any error so callers can fall back to text matching.
        Responses are cached for the lifetime of the process.
        """
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        model_uri = (
            f"emb://{settings.YANDEX_CLOUD_CATALOG_ID}/text-search-doc/latest"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding",
                    headers={
                        "Authorization": f"Api-Key {settings.YANDEX_API_KEY}",
                        "x-folder-id": settings.YANDEX_CLOUD_CATALOG_ID,
                    },
                    json={"modelUri": model_uri, "text": text},
                )
                if resp.status_code == 200:
                    embedding: List[float] = resp.json()["embedding"]
                    self._embedding_cache[text] = embedding
                    return embedding
                logger.warning("Embedding API returned %s", resp.status_code)
        except Exception as exc:
            logger.warning("Embedding fetch failed: %s", exc)
        return None

    async def _is_semantically_duplicate(
        self,
        candidate: str,
        existing: List[str],
        threshold: float = 0.87,
    ) -> bool:
        """
        Returns True if `candidate` is semantically too close to any question
        in `existing`.  Falls back to substring check when embeddings are
        unavailable.
        """
        if not existing:
            return False

        cand_emb = await self._fetch_embedding(candidate)
        if cand_emb is None:
            # Fallback: naive substring overlap
            c = candidate.lower()
            return any(c in q.lower() or q.lower() in c for q in existing)

        for text in existing:
            emb = await self._fetch_embedding(text)
            if emb and _cosine_similarity(cand_emb, emb) >= threshold:
                return True
        return False

    # LLM call wrapper 

    async def _chat(
        self,
        system: str,
        user: str,
        temperature: float,
    ) -> str:
        """Single-shot chat completion, maps API errors to LLMServiceError."""
        try:
            response = await self.chat.completions.create(
                model=settings.YANDEX_GPT_MODEL_URI,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except openai.APIConnectionError as exc:
            raise LLMServiceError("Не удалось подключиться к LLM сервису") from exc
        except openai.RateLimitError as exc:
            raise LLMServiceError("Превышен лимит запросов к LLM сервису") from exc
        except openai.APIStatusError as exc:
            logger.error("LLM API error %s: %s", exc.status_code, exc.message)
            raise LLMServiceError(f"Ошибка LLM сервиса: {exc.status_code}") from exc

    async def _parse_json(
        self,
        raw: str,
        model_cls: type,
        retry_system: str,
        retry_user: str,
        temperature: float,
    ) -> Dict[str, Any]:
        """
        Parse JSON from raw LLM output, validated with a Pydantic model.
        On failure makes one retry asking the LLM to fix the JSON.
        """
        for attempt in (1, 2):
            text = _strip_markdown(raw)
            try:
                data = json.loads(text)
                return model_cls(**data).model_dump()
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 2:
                    logger.error("JSON parse failed after retry: %s | raw: %s", exc, raw[:300])
                    raise LLMServiceError("LLM вернул невалидный JSON") from exc
                # Ask the model to fix it
                raw = await self._chat(
                    system=retry_system,
                    user=(
                        f"Исправь следующий JSON так, чтобы он соответствовал схеме, "
                        f"и верни ТОЛЬКО валидный JSON без markdown:\n\n{text}"
                    ),
                    temperature=0.1,
                )

    # Public API 

    async def generate_question(
        self,
        level: str,
        stack: str,
        # original params
        weak_topic_hint: Optional[str] = None,
        asked_questions: Optional[List[str]] = None,
        user_notes: Optional[str] = None,
        # new optional params (service doesn't need to pass these to stay compatible)
        avg_score: Optional[float] = None,
        next_question_type: Optional[str] = None,
        asked_qa_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generates one interview question.

        New params:
          avg_score          – running average of all scores so far (triggers difficulty nudge)
          next_question_type – "conceptual" | "practical" | "debug"  (type rotation)
          asked_qa_history   – list of {"question": str, "answer": str, "score": dict}
                               for richer context when choosing the next topic
        """
        level_guidance = _LEVEL_GUIDANCE.get(level.lower(), _LEVEL_GUIDANCE["junior"])

        # Topic directive
        if user_notes:
            topic_block = (
                f"ПРИОРИТЕТ: Кандидат хочет вопросы по следующим темам/технологиям: «{user_notes}». "
                f"Выбирай тему строго из этого списка."
            )
            if weak_topic_hint:
                topic_block += (
                    f" Если возможно, сделай акцент на слабом месте: «{weak_topic_hint}»."
                )
        elif weak_topic_hint:
            topic_block = f"Предпочтительная тема (слабое место кандидата): «{weak_topic_hint}»."
        else:
            topic_block = ""

        # Already-asked questions block
        avoid_block = ""
        if asked_questions:
            lines = "\n".join(f"  {i+1}. {q}" for i, q in enumerate(asked_questions))
            avoid_block = (
                f"\nУЖЕ ЗАДАННЫЕ ВОПРОСЫ — не повторять эти концепции и не задавать "
                f"вариации на те же темы:\n{lines}"
            )

        # Question type
        qtype = next_question_type or "conceptual"
        if qtype not in _QUESTION_TYPE_DESCRIPTIONS:
            qtype = "conceptual"
        type_block = f"\nТИП ВОПРОСА: {_QUESTION_TYPE_DESCRIPTIONS[qtype]}"

        # Difficulty adaptation
        difficulty_block = _difficulty_hint(avg_score)

        # Recent QA context (last 2 exchanges) so the model sees the pattern
        history_block = ""
        if asked_qa_history:
            tail = asked_qa_history[-2:]
            lines = []
            for i, pair in enumerate(tail, 1):
                avg = _score_avg(pair.get("score", {}))
                lines.append(
                    f"  Вопрос {i}: {pair.get('question', '')[:120]}\n"
                    f"  Ответ:   {pair.get('answer', '')[:150]}\n"
                    f"  Оценка:  {avg:.1f}/10"
                )
            history_block = "\nПОСЛЕДНИЕ ВОПРОСЫ И ОТВЕТЫ КАНДИДАТА (для контекста):\n" + "\n\n".join(lines)

        system_prompt = (
            f"Ты опытный технический интервьюер. "
            f"Ты проводишь собеседование уровня {level} по стеку {stack}. "
            f"Твоя задача — задавать чёткие, конкретные, неповторяющиеся вопросы "
            f"строго в соответствии с инструкциями."
        )

        user_prompt = f"""Сгенерируй один вопрос для кандидата.
{topic_block}{avoid_block}{type_block}{difficulty_block}{history_block}

ТРЕБОВАНИЯ К СЛОЖНОСТИ:
{level_guidance}

ЗАПРЕЩЕНО:
- Вопросы-техзадания: не просить реализовать целую систему с ORM, тестами и логированием
- Перечислять несколько требований через «и»: «реализуй X, учитывай Y, опиши Z»
- Вопрос длиннее 3 предложений

Верни ТОЛЬКО JSON без markdown-обёртки:
{{
  "text": "текст вопроса (не длиннее 3 предложений)",
  "topic": "краткое название темы (2-4 слова)",
  "hints": ["подсказка 1", "подсказка 2"],
  "question_type": "{qtype}"
}}"""

        raw = await self._chat(system_prompt, user_prompt, temperature=0.85)
        result = await self._parse_json(raw, _QuestionModel, system_prompt, user_prompt, 0.85)

        # Semantic deduplication: if too similar to prior questions, ask once more
        if asked_questions and await self._is_semantically_duplicate(
            result["text"], asked_questions
        ):
            logger.info("Generated question too similar to existing ones — retrying.")
            extra = f"\n\nОСОБО ВАЖНО: предыдущая попытка дала вопрос, слишком похожий на уже заданные. Выбери ДРУГУЮ концепцию."
            raw2 = await self._chat(system_prompt, user_prompt + extra, temperature=0.95)
            result = await self._parse_json(raw2, _QuestionModel, system_prompt, user_prompt, 0.95)

        return result

    async def evaluate_answer(
        self,
        question: str,
        answer: str,
        prior_avg_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate answer.

        New param:
          prior_avg_score – running average before this question, used to
                            calibrate the evaluator's expectations.
        """
        context_block = ""
        if prior_avg_score is not None:
            context_block = (
                f"\nКОНТЕКСТ: средний балл кандидата по предыдущим вопросам — "
                f"{prior_avg_score:.1f}/10. Оценивай этот ответ независимо и объективно."
            )

        system_prompt = (
            "Ты Senior-инженер и технический интервьюер. "
            "Твоя задача — объективно и строго оценивать ответы кандидата, "
            "давать конкретный конструктивный фидбек."
        )

        user_prompt = f"""Оцени ответ кандидата по 5 критериям.
{context_block}

Вопрос: {question}

Ответ кандидата: {answer}

{_SCORE_RUBRIC}

КРИТЕРИИ:
- correctness  — техническая правильность ответа
- optimality   — насколько оптимально предложенное решение
- complexity   — демонстрирует ли кандидат понимание временной/пространственной сложности
- explanation  — качество и ясность объяснения
- gaps         — отсутствие пробелов (10 = пробелов нет, 1 = критические пробелы)

Верни ТОЛЬКО JSON без markdown-обёртки:
{{
  "score": {{
    "correctness": число от 1 до 10,
    "optimality": число от 1 до 10,
    "complexity": число от 1 до 10,
    "explanation": число от 1 до 10,
    "gaps": число от 1 до 10
  }},
  "feedback": "3-5 предложений: что хорошо, что упущено, что исправить",
  "weak_topics": ["конкретная тема 1", "конкретная тема 2"]
}}"""

        raw = await self._chat(system_prompt, user_prompt, temperature=0.2)
        return await self._parse_json(raw, _EvaluationModel, system_prompt, user_prompt, 0.2)

    async def extract_weak_topics(self, feedback: str) -> List[str]:
        """Kept for backward compatibility. Prefer using weak_topics from evaluate_answer."""
        system_prompt = "Ты аналитик результатов технических интервью."
        user_prompt = (
            f"Из этого фидбека извлеки список слабых тем кандидата в виде коротких меток (2-4 слова).\n\n"
            f"{feedback}\n\n"
            f"Верни ТОЛЬКО JSON-массив строк без markdown. Пример: [\"asyncio\", \"индексы БД\"]"
        )
        raw = await self._chat(system_prompt, user_prompt, temperature=0.1)
        text = _strip_markdown(raw)
        start, end = text.find("["), text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return [t.strip().strip('"\'') for t in text.replace("[", "").replace("]", "").split(",") if t.strip()]

    async def generate_session_summary(
        self,
        level: str,
        stack: str,
        questions_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generates a session summary.
        Now includes score trend analysis (improving / declining / stable).
        """
        # Build per-question averages to detect trend
        per_q_avgs = [_score_avg(r.get("score", {})) for r in questions_results]
        if len(per_q_avgs) >= 3:
            first_half = per_q_avgs[: len(per_q_avgs) // 2]
            second_half = per_q_avgs[len(per_q_avgs) // 2 :]
            delta = sum(second_half) / len(second_half) - sum(first_half) / len(first_half)
            if delta > 0.8:
                trend = "улучшающийся (кандидат разогревался в процессе)"
            elif delta < -0.8:
                trend = "ухудшающийся (кандидат терял концентрацию или сталкивался с незнакомыми темами)"
            else:
                trend = "стабильный"
        else:
            trend = "недостаточно данных для анализа тренда"

        qa_text = "\n\n".join(
            f"Вопрос {i+1} [{r.get('question', '')[:120]}]\n"
            f"  Ответ: {r.get('answer', '')[:200]}\n"
            f"  Оценка: {r.get('score', {})} (среднее: {_score_avg(r.get('score', {})):.1f})\n"
            f"  Слабые темы: {', '.join(r.get('weak_topics') or []) or '—'}"
            for i, r in enumerate(questions_results)
        )

        system_prompt = (
            "Ты опытный технический интервьюер, составляющий финальный отчёт "
            "по результатам собеседования. Будь конкретным и конструктивным."
        )

        user_prompt = f"""Проанализируй результаты технического собеседования уровня {level} по стеку {stack}.

ТРЕНД ПРОИЗВОДИТЕЛЬНОСТИ: {trend}

ДЕТАЛИ ПО ВОПРОСАМ:
{qa_text}

Составь итоговое саммари на русском языке. Учти тренд при формулировке выводов.
Верни ТОЛЬКО JSON без markdown-обёртки:
{{
  "overall": "2-3 предложения об общем уровне и тренде кандидата",
  "strengths": ["конкретная сильная сторона 1", "конкретная сильная сторона 2"],
  "weaknesses": ["конкретное слабое место 1", "конкретное слабое место 2"],
  "recommendations": [
    "конкретная рекомендация со ссылкой на тему 1",
    "конкретная рекомендация 2",
    "конкретная рекомендация 3"
  ]
}}"""

        raw = await self._chat(system_prompt, user_prompt, temperature=0.35)
        return await self._parse_json(raw, _SummaryModel, system_prompt, user_prompt, 0.35)
