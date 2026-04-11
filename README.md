# Sphinx

AI-ассистент для подготовки к техническому интервью. Telegram Web App (TWA): задаёт вопросы по выбранному стеку и уровню, оценивает ответы через LLM, даёт обратную связь и итоговое саммари.

---

## Стек

**Backend** — FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic + YandexGPT (через OpenAI-compatible API)

**Frontend** — React + TypeScript + Vite + Tailwind CSS + TMA SDK (Telegram Mini Apps)

---

## Структура проекта

```
sphinx/
├── backend/
│   └── src/app/
│       ├── api/routers/        # FastAPI роутеры
│       ├── core/               # LLM клиенты
│       ├── db/                 # модели, crud, сессия
│       ├── services/           # бизнес-логика
│       ├── schemas/            # Pydantic схемы
│       └── config.py           # настройки из .env
└── frontend/
    └── src/
        ├── api/                # HTTP-клиент (interview.ts)
        ├── components/         # UI компоненты
        ├── hooks/              # useInterview, useTelegramUser
        └── pages/              # HomePage, InterviewPage, ResultPage
```

---

## Переменные окружения

Файл `.env` в корне проекта (рядом с `backend/`):

```env
DB_USER=
DB_PASSWORD=
DB_NAME=
DB_HOST=
DB_PORT=

YANDEX_API_KEY=          # API-ключ YandexGPT
YANDEX_API_KEY_ID=       # ID ключа (для service account)
YANDEX_API_MODEL_URI=    # URI модели
YANDEX_CLOUD_CATALOG_ID= # ID каталога в Yandex Cloud

BOT_TOKEN=               # Telegram Bot токен (опционально)
WEBAPP_URL=              # URL TWA
FRONTEND_URL=            # URL фронтенда
```

Переменная окружения фронтенда — `VITE_API_URL` в `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

---

## Запуск

**Backend:**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn src.app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## API эндпоинты

### Пользователи

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/users` | Get-or-create пользователь по `telegram_id` |
| GET | `/users/{user_id}` | Получить пользователя по внутреннему ID |

### Интервью (v1 — стандартная генерация)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/interview/start` | Создать интервью, получить первый вопрос |
| GET | `/interview/{id}/question` | Получить текущий вопрос |
| POST | `/interview/{id}/answer` | Отправить ответ, получить оценку |
| GET | `/interview/{id}/result` | Итоги сессии |

### Интервью (v2 — адаптивная генерация)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/interview/{id}/question/v2` | Вопрос с адаптацией сложности + семантической дедупликацией |
| POST | `/interview/{id}/answer/v2` | Оценка с калибровкой по running avg score |
| GET | `/interview/{id}/result/v2` | Итоги с анализом тренда производительности |

Фронт сейчас смотрит на v2. Чтобы переключиться обратно — раскомментировать старые строки в `frontend/src/api/interview.ts`.

---

## Идентификация пользователей

- В Telegram: `user.id` из TMA launch params → сохраняется как `telegram_id` в БД
- В браузере (dev): генерируется анонимный ID, хранится в `localStorage` как `sphinx_anon_id`
- Внутренний DB ID (`user.id`) кешируется в `localStorage` как `sphinx_user_id`
- `POST /users` — idempotent: если `telegram_id` уже есть, возвращает существующего пользователя

---

## LLM клиенты

В `backend/src/app/core/` два клиента с одинаковым интерфейсом:

**`llm_client.py`** — оригинальный клиент. Простая генерация промптов, всё в одном user-сообщении.

**`llm_client_new.py`** — улучшенный клиент (`LLMClientNew`). Используется v2 эндпоинтами.

Отличия `LLMClientNew`:
- **System/user role split** — системный промпт отделён от задачи на каждом вызове
- **Embedding-based дедупликация** — после генерации вопроса считает косинусное сходство через Yandex Embeddings REST API; если > 0.87 с уже заданными — генерирует заново
- **Адаптивная сложность** — если `avg_score >= 7.5`, в промпт добавляется инструкция усложнить; если `<= 4.5` — облегчить
- **Ротация типов вопросов** — `conceptual → practical → debug → ...` по позиции вопроса в сессии
- **Anchored scoring rubric** — явные якоря для каждого балла (9-10, 7-8, 5-6, 3-4, 1-2), исключают grade inflation
- **Score trend в саммари** — сравнивает первую и вторую половины сессии, определяет динамику (улучшается / падает / стабильно)
- **Retry на невалидный JSON** — при ошибке парсинга делает один дополнительный вызов с просьбой исправить JSON
- **Pydantic-валидация** вывода LLM

Эмбеддинги кешируются в памяти процесса. Если Yandex Embeddings API недоступен — fallback на текстовое сравнение.

---

## Страница результатов

`/result/:interviewId` — одна страница, скролл сверху вниз:

1. Общий балл + грейд (Отлично / Хорошо / Удовлетворительно / Нужно поработать)
2. Средние баллы по 5 критериям (полоски)
3. Итоговое саммари (overall + сильные стороны + слабые места + рекомендации)
4. Разбор по каждому вопросу (вопрос → балл → фидбек → weak topic теги)
