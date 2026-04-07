import openai
import json
from typing import Dict, List, Any

from src.app.config import settings


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

    async def generate_question(self, level: str, stack: str, topic: str = None) -> Dict[str, Any]:
        """Генерирует вопрос для интервью"""
        prompt = f"""
        Ты технический интервьюер уровня Senior.
        Сгенерируй вопрос уровня {level} по {stack}.
        {"Тема: " + topic if topic else ""}

        Верни JSON с полями:
        - text: текст вопроса
        - topic: тема вопроса
        - hints: массив подсказок (опционально)
        """

        response = await self.chat.completions.create(
            model=settings.YANDEX_GPT_MODEL_URI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback если не JSON
            return {
                "text": content,
                "topic": topic or "general",
                "hints": []
            }

    async def evaluate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """Оценивает ответ кандидата"""
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

        response = await self.chat.completions.create(
            model=settings.YANDEX_GPT_MODEL_URI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback
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
        """Извлекает слабые темы из фидбека"""
        prompt = f"""
        Из этого фидбека извлеки список слабых тем кандидата:
        {feedback}

        Верни только JSON массив строк, без дополнительного текста.
        Пример: ["алгоритмы", "структуры данных"]
        """

        response = await self.chat.completions.create(
            model=settings.YANDEX_GPT_MODEL_URI,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        content = response.choices[0].message.content.strip()
        # Попытаться найти JSON в ответе
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            json_part = content[start:end]
            try:
                return json.loads(json_part)
            except json.JSONDecodeError:
                pass
        # Fallback: парсинг простого списка
        topics = [t.strip().strip('"').strip("'") for t in content.replace('[', '').replace(']', '').split(',') if t.strip()]
        return topics
