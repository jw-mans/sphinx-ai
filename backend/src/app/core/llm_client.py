import openai
import json
import logging
from typing import Dict, List, Any

from src.app.config import settings
from src.app.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


def _strip_markdown(text: str) -> str:
    """
    Убирает markdown code-block обёртку (```json ... ```) из ответа LLM.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] 
        text = text.rsplit("```", 1)[0] 
    return text.strip()


_LEVEL_GUIDANCE: Dict[str, str] = {
    "junior": """
- Структуры данных: массивы, хеш-таблицы, множества, стеки, очереди — нетривиальное применение.
- Алгоритмы: двоичный поиск, два указателя, скользящее окно, базовая рекурсия с мемоизацией.
- Строки: анаграммы, палиндромы, перестановки, парсинг.
- Сортировка: реализация merge sort / quick sort, поиск k-го элемента.
- Математика: простые числа (решето Эратосфена), НОД/НОК, степени, Фибоначчи (итеративно и с мемоизацией).
- НЕ задавай: «сложи/вычти/умножь числа», простые if/else, однострочные функции без алгоритмической сложности.""",

    "middle": """
- Алгоритмы: обход графов (BFS/DFS), топологическая сортировка, базовое динамическое программирование (LCS, задача о рюкзаке), деревья (BST, обходы).
- Конкурентность: потоки, блокировки, базовые паттерны параллелизма для указанного стека.
- Специфика стека: используй конкретные библиотеки, инструменты и паттерны стека.
  Примеры для Python: asyncio, генераторы, декораторы, контекстные менеджеры, SQLAlchemy, pytest, type hints.
  Примеры для JavaScript/TypeScript: event loop, Promises, замыкания, React hooks, прототипы, Node.js streams.
  Примеры для Go: горутины, каналы, defer/panic/recover, interfaces, sync.Mutex.
  Примеры для Java: JVM internals, Streams API, CompletableFuture, synchronized, volatile.
  Примеры для других стеков — аналогично их экосистеме.
- Проектирование: SOLID, базовые паттерны GoF (Factory, Observer, Strategy, Decorator), REST API дизайн.
- Оптимизация: O(n log n) решения, кеширование, N+1 проблема в ORM.""",

    "senior": """
- Системный дизайн: проектирование rate limiter, кеширующего слоя, очереди сообщений, балансировщика нагрузки; обсуждение trade-offs.
- Сложные алгоритмы: продвинутое DP (longest increasing subsequence, edit distance), сегментные деревья, union-find, алгоритм Дейкстры, A*.
- Конкурентность: гонки данных, дедлоки, lock-free структуры, акторная модель, compare-and-swap.
- Архитектура: микросервисы vs монолит с конкретными аргументами, event sourcing, CQRS, saga pattern.
- Производительность: профилирование, утечки памяти, GC паузы, оптимизация запросов (EXPLAIN ANALYZE), индексы.
- Глубина стека: внутреннее устройство рантайма/фреймворка (GIL в Python, V8 JIT, Go scheduler, JVM GC алгоритмы).
- Code review: найди баги/антипаттерны в предложенном коде, объясни почему это проблема и как исправить.""",
}


class LLMClient(openai.AsyncOpenAI):
    def __init__(self,
                 api_key: str = settings.YANDEX_API_KEY,
                 base_url: str = settings.YANDEX_API_URL,
                 project: str = settings.YANDEX_CLOUD_CATALOG_ID,
                 ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_headers={"x-folder-id": project}
        )

    async def generate_question(
        self,
        level: str,
        stack: str,
        weak_topic_hint: str = None,
        asked_questions: List[str] = None,
        user_notes: str = None,
    ) -> Dict[str, Any]:
        """
        Генерирует вопрос для интервью
        """

        level_guidance = _LEVEL_GUIDANCE.get(level.lower(), _LEVEL_GUIDANCE["junior"])

        avoid_block = ""
        if asked_questions:
            questions_list = "\n".join(f'  {i+1}. {q}' for i, q in enumerate(asked_questions))
            avoid_block = (
                f"\nУЖЕ ЗАДАННЫЕ ВОПРОСЫ (не повторять эту же концепцию, "
                f"не задавать вариации на ту же тему):\n{questions_list}"
            )

        if user_notes:
            topic_directive = (
                f"\nПРИОРИТЕТ: Кандидат хочет вопросы по следующим темам/технологиям: «{user_notes}». "
                f"Выбирай тему строго из этого списка."
            )
            if weak_topic_hint:
                topic_directive += (
                    f" Если возможно, сделай акцент на слабом месте кандидата: «{weak_topic_hint}»."
                )
        elif weak_topic_hint:
            topic_directive = f"\nПредпочтительная тема (слабое место кандидата): «{weak_topic_hint}»."
        else:
            topic_directive = ""

        prompt = f"""Ты опытный технический интервьюер. Сгенерируй один вопрос для кандидата уровня {level} по стеку {stack}.
{topic_directive}{avoid_block}

ТРЕБОВАНИЯ К СЛОЖНОСТИ:
{level_guidance}

ФОРМАТ ВОПРОСА — строго одно из:
- Концептуальный: «Как работает X?», «В чём разница между X и Y?», «Когда ты выберешь X вместо Y?»
- Задача на рассуждение: «Что произойдёт, если...», «Почему этот код ведёт себя так?»
- Небольшая практическая задача: написать/исправить/объяснить 5–15 строк кода по одной конкретной концепции

ЗАПРЕЩЕНО:
- Вопросы-техзадания: не просить реализовать целую систему, сервис, pipeline с ORM, тестами и логированием одновременно
- Перечислять несколько требований через «и»: «реализуй X, учитывай Y, опиши тестирование Z»
- Вопрос длиннее 3 предложений

Верни ТОЛЬКО JSON без markdown-обёртки:
{{
  "text": "текст вопроса (не длиннее 3 предложений)",
  "topic": "краткое название темы (2-4 слова)",
  "hints": ["подсказка 1", "подсказка 2"]
}}"""

        try:
            response = await self.chat.completions.create(
                model=settings.YANDEX_GPT_MODEL_URI,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
            )
        except openai.APIConnectionError as e:
            raise LLMServiceError("Не удалось подключиться к LLM сервису") from e
        except openai.RateLimitError as e:
            raise LLMServiceError("Превышен лимит запросов к LLM сервису") from e
        except openai.APIStatusError as e:
            logger.error(f"LLM API error {e.status_code}: {e.message}")
            raise LLMServiceError(f"Ошибка LLM сервиса: {e.status_code}") from e

        content = _strip_markdown(response.choices[0].message.content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "text": content,
                "topic": weak_topic_hint or (asked_questions[-1][:30] if asked_questions else "general"),
                "hints": [],
            }

    async def evaluate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Оценивает ответ кандидата
        """

        prompt = f"""
        Ты технический интервьюер уровня Senior.
        Оцени ответ кандидата по 5 критериям:
        - correctness (корректность)
        - optimality (оптимальность)
        - complexity (понимание сложности)
        - explanation (качество объяснения)
        - gaps (пробелы в знаниях)

        Вопрос: {question}
        Ответ кандидата: {answer}

        Верни JSON:
        {{
          "score": {{
            "correctness": число от 1 до 10,
            "optimality": число от 1 до 10,
            "complexity": число от 1 до 10,
            "explanation": число от 1 до 10,
            "gaps": число от 1 до 10
          }},
          "feedback": "подробный фидбек",
          "weak_topics": ["тема1", "тема2"]
        }}
        """

        try:
            response = await self.chat.completions.create(
                model=settings.YANDEX_GPT_MODEL_URI,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
        except openai.APIConnectionError as e:
            raise LLMServiceError("Не удалось подключиться к LLM сервису") from e
        except openai.RateLimitError as e:
            raise LLMServiceError("Превышен лимит запросов к LLM сервису") from e
        except openai.APIStatusError as e:
            logger.error(f"LLM API error {e.status_code}: {e.message}")
            raise LLMServiceError(f"Ошибка LLM сервиса: {e.status_code}") from e

        content = _strip_markdown(response.choices[0].message.content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "score": {
                    "correctness": 5,
                    "optimality": 5,
                    "complexity": 5,
                    "explanation": 5,
                    "gaps": 5
                },
                "feedback": content,
                "weak_topics": []
            }

    async def extract_weak_topics(self, feedback: str) -> List[str]:
        """
        Извлекает слабые темы из фидбека
        """
        
        prompt = f"""
        Из этого фидбека извлеки список слабых тем кандидата:
        {feedback}

        Верни только JSON массив строк, без дополнительного текста.
        Пример: ["алгоритмы", "структуры данных"]
        """

        try:
            response = await self.chat.completions.create(
                model=settings.YANDEX_GPT_MODEL_URI,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
        except openai.APIConnectionError as e:
            raise LLMServiceError("Не удалось подключиться к LLM сервису") from e
        except openai.RateLimitError as e:
            raise LLMServiceError("Превышен лимит запросов к LLM сервису") from e
        except openai.APIStatusError as e:
            logger.error(f"LLM API error {e.status_code}: {e.message}")
            raise LLMServiceError(f"Ошибка LLM сервиса: {e.status_code}") from e

        content = _strip_markdown(response.choices[0].message.content)
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            json_part = content[start:end]
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
        topics = [t.strip().strip('"').strip("'") for t in content.replace('[', '').replace(']', '').split(',') if t.strip()]
        return topics

    async def generate_session_summary(
        self,
        level: str,
        stack: str,
        questions_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Генерирует общее саммари по итогам всего интервью
        """
        
        qa_text = "\n\n".join(
            f"Вопрос {i + 1} ({r.get('question', '')[:120]}):\n"
            f"  Ответ: {r.get('answer', '')[:200]}\n"
            f"  Оценка: {r.get('score', {})}\n"
            f"  Слабые темы: {', '.join(r.get('weak_topics') or [])}"
            for i, r in enumerate(questions_results)
        )

        prompt = f"""Ты опытный технический интервьюер. Проанализируй результаты технического собеседования уровня {level} по стеку {stack}.

{qa_text}

Составь итоговое саммари на русском языке. Верни ТОЛЬКО JSON без markdown-обёртки:
{{
  "overall": "2-3 предложения об общем уровне кандидата",
  "strengths": ["сильная сторона 1", "сильная сторона 2"],
  "weaknesses": ["слабое место 1", "слабое место 2"],
  "recommendations": ["конкретная рекомендация 1", "конкретная рекомендация 2", "конкретная рекомендация 3"]
}}"""

        try:
            response = await self.chat.completions.create(
                model=settings.YANDEX_GPT_MODEL_URI,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
            )
        except openai.APIConnectionError as e:
            raise LLMServiceError("Не удалось подключиться к LLM сервису") from e
        except openai.RateLimitError as e:
            raise LLMServiceError("Превышен лимит запросов к LLM сервису") from e
        except openai.APIStatusError as e:
            logger.error(f"LLM API error {e.status_code}: {e.message}")
            raise LLMServiceError(f"Ошибка LLM сервиса: {e.status_code}") from e

        content = _strip_markdown(response.choices[0].message.content)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "overall": content,
                "strengths": [],
                "weaknesses": [],
                "recommendations": [],
            }
