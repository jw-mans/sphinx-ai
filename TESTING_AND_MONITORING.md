# Тестирование и мониторинг — Sphinx

> Документ охватывает все 8 пунктов ТЗ: тесты, GUI-сценарий, безопасность,
> приемо-сдаточные сценарии, дашборды Grafana, алерты, логирование и метрики NPS/CSAT/CES.
> Все команды и результаты проверены на реальном стеке (Docker, 2026-05-09).

---

## Содержание

1. [Запуск стека](#0-запуск-стека)
2. [Тесты (Unit / Regression / Security)](#1-тесты)
3. [Нагрузочный тест (Locust)](#2-нагрузочный-тест)
4. [GUI-тестирование (Playwright)](#3-gui-тестирование)
5. [Безопасность: SQL-инъекции и горизонтальные привилегии](#4-безопасность)
6. [Приемо-сдаточные сценарии (UAT)](#5-uat)
7. [Дашборды Grafana](#6-дашборды-grafana)
8. [Алерт на недоступность сервиса](#7-алерт)
9. [Логирование в Grafana (Loki)](#8-логирование)
10. [Метрики NPS / CSAT / CES](#9-nps--csat--ces)

---

## 0. Запуск стека

```powershell
# Запустить все сервисы
docker compose up -d

# Проверить состояние
docker compose ps
```

| Сервис | URL | Что делает |
|--------|-----|-----------|
| Backend API | http://localhost:8000 | FastAPI + PostgreSQL |
| Frontend | http://localhost:5173 | React (сайт или TG WebApp) |
| Prometheus | http://localhost:9090 | Сбор метрик |
| Alertmanager | http://localhost:9093 | Email-алерты |
| Loki | http://localhost:3100 | Агрегация логов |
| Grafana | http://localhost:3000 | Дашборды |

**Grafana:** логин `daniiljermakiw`, пароль из `.env` → `GRAFANA_PASSWORD`.

### Применение миграций БД

После первого запуска или добавления новых миграций — обязательно:

```powershell
# Показать текущее состояние
docker compose exec backend sh -c "cd /app/src && alembic -c alembic/alembic.ini current"

# Применить все pending-миграции
docker compose exec backend sh -c "cd /app/src && alembic -c alembic/alembic.ini upgrade head"
```

> **Важно:** если таблицы уже существуют в БД (созданы до Alembic), сначала нужно
> проставить stamp на уже применённые ревизии, чтобы Alembic знал текущее состояние:
> ```powershell
> docker compose exec backend sh -c "cd /app/src && alembic -c alembic/alembic.ini stamp <revision_id>"
> docker compose exec backend sh -c "cd /app/src && alembic -c alembic/alembic.ini upgrade head"
> ```

---

## 1. Тесты

### Структура

```
backend/
├── pytest.ini               # asyncio_mode=auto, testpaths=tests
└── tests/
    ├── conftest.py          # Фикстуры: NullPool engine, mock LLM, HTTP-клиент
    ├── test_health.py       # Существующие тесты healthcheck
    ├── test_users.py        # Существующие тесты CRUD пользователей
    ├── test_interview.py    # Существующие тесты флоу интервью
    ├── test_unit.py         # ★ Unit-тесты (CRUD-слой напрямую)
    ├── test_regression.py   # ★ Регрессионные тесты
    └── test_security.py     # ★ SQL-инъекции + горизонтальные привилегии
locustfile.py                # ★ Нагрузочный тест (Locust)
```

### Запуск тестов

```powershell
# Все unit + regression + security тесты (рекомендуется)
docker compose exec backend sh -c "cd /app && python -m pytest tests/test_unit.py tests/test_regression.py tests/test_security.py -v"

# С HTML-отчётом и XML для CI
docker compose exec backend sh -c "cd /app && python -m pytest tests/test_unit.py tests/test_regression.py tests/test_security.py -v --junit-xml=junit.xml"
```

> **Примечание:** pytest и pytest-asyncio не входят в `requirements.txt` (это prod-зависимости).
> При первом запуске в контейнере их нужно установить:
> ```powershell
> docker compose exec backend sh -c "pip install pytest pytest-asyncio httpx -q"
> ```

### Фактические результаты (2026-05-09)

```
======================== 34 passed, 76 warnings in 7.25s ========================

  5 unit tests       — test_unit.py        PASSED
  4 regression tests — test_regression.py  PASSED
 25 security tests   — test_security.py    PASSED
```

### Что проверяет `test_unit.py` (5 тестов)

| Тест | Что проверяет |
|------|---------------|
| `test_create_user_returns_user_with_correct_telegram_id` | CRUD `create_user` создаёт объект с корректным `telegram_id` |
| `test_create_user_persists_to_db` | Созданный пользователь доступен через `get_user` |
| `test_get_user_by_telegram_id_returns_correct_user` | Поиск по `telegram_id` работает |
| `test_get_user_nonexistent_returns_none` | Несуществующий `user_id` возвращает `None` |
| `test_get_user_by_unknown_telegram_id_returns_none` | Несуществующий `telegram_id` возвращает `None` |

### Что проверяет `test_regression.py` (4 теста)

| Тест | Закрытый баг |
|------|--------------|
| `test_duplicate_telegram_id_returns_same_user` | Bug-1: двойной POST /users не даёт 500, возвращает тот же объект |
| `test_double_answer_returns_409_not_500` | Bug-2: повторный ответ без вопроса → 409, не 500 |
| `test_result_with_no_answers_is_empty_list` | Bug-3: result на пустом интервью → 200 + пустой список, не краш |
| `test_unknown_interview_is_404_on_all_endpoints` | Bug-4: все endpoint с несуществующим id → 404 |

### Техническое устройство conftest.py

Тесты используют **отдельный движок с `NullPool`** (без пула соединений).
Это решает проблему «Future attached to a different loop» при использовании
`asyncpg` + `pytest-asyncio` с разными event loop-ами на сессионных фикстурах:

```python
_test_engine = create_async_engine(settings.DB_URL, poolclass=NullPool)
```

`NullPool` создаёт новое соединение при каждом запросе и закрывает его сразу,
без кэширования в пуле — поэтому нет привязки к конкретному event loop.

---

## 2. Нагрузочный тест

### Запуск

```bash
pip install locust

# С web-интерфейсом
locust -f locustfile.py --host http://localhost:8000
# Открыть: http://localhost:8089

# Headless (CI)
locust -f locustfile.py --host http://localhost:8000 \
  --headless -u 50 -r 10 --run-time 60s --csv=load_results
```

### Сценарий (`locustfile.py`)

Симулирует полный флоу: регистрация пользователя → старт интервью →
ответ на вопрос → получение результата.

**Рекомендуемые параметры для smoke-проверки:**
- Users: 20, Spawn rate: 5, Duration: 60 s
- Ожидаемые результаты: P95 < 3 s, error rate < 1 %

> **Важно:** endpoint `/interview/start` требует доступного LLM (YandexGPT).
> В среде с VPN на западный сервер YandexGPT блокирует запросы — тест LLM-зависимых
> endpoint-ов нужно проводить с российским IP (без VPN или через российский прокси).

---

## 3. GUI-тестирование

### Стек

[Playwright](https://playwright.dev/) + TypeScript.

### Установка

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
```

### Запуск

```bash
# Запустить dev-стек
docker compose up -d

# Выполнить тесты
cd frontend
npx playwright test

# С UI (интерактивный режим)
npx playwright test --ui

# С отчётом
npx playwright show-report
```

### Сценарии (`frontend/tests/e2e/interview_flow.spec.ts`)

| № | Сценарий |
|---|----------|
| 1 | Главная страница (или AuthPage): логотип, заголовок и форма видны |
| 2 | Кнопка «Начать» активируется после выбора уровня + стека |
| 3 | Запуск интервью: переход на `/interview/:id`, виден первый вопрос |
| 4 | Ввод и отправка ответа показывает feedback/оценку |
| 5 | Страница результата отображает средний балл (с mock API) |
| 6 | Неизвестный роут: приложение показывает fallback или редиректит |

### Переменные окружения

```bash
# Если frontend не на 5173
PLAYWRIGHT_BASE_URL=http://localhost:5173 npx playwright test
```

---

## 4. Безопасность

### Запуск тестов безопасности

```powershell
docker compose exec backend sh -c "cd /app && python -m pytest tests/test_security.py -v"
```

### SQL-инъекции (`TestSQLInjection`) — 21 тест

Тестируются **7 payload-ов** против **3 endpoint-ов**:

**Payload-ы:**
```
' OR '1'='1
'; DROP TABLE users; --
' UNION SELECT * FROM users --
1; SELECT pg_sleep(5) --
\x27 OR 1=1 --
<script>alert(1)</script>
" OR ""="
```

**Endpoint-ы:**
- `POST /users` — поле `telegram_id`
- `GET /users/{id}` — path-параметр
- `POST /interview/{id}/answer` — поле `text`

**Результат:** FastAPI + SQLAlchemy ORM параметризуют все запросы → инъекция невозможна.
Payload сохраняется как литеральная строка, возвращается 400/422/404, но не 500.

### Горизонтальные привилегии (`TestHorizontalPrivilege`) — 4 теста

| Тест | Что проверяет |
|------|---------------|
| `test_user_cannot_read_other_users_profile` | GET /users/{id} возвращает данные только запрошенного юзера |
| `test_user_a_cannot_get_user_b_interview_question` | Ответ не содержит данных user A |
| `test_user_a_cannot_answer_user_b_interview` | Кросс-юзерный ответ не вызывает 500 |
| `test_user_a_cannot_get_user_b_result` | Result не содержит `telegram_id` чужого юзера |

> **Статус:** JWT-аутентификация реализована (`/auth/register`, `/auth/login`, `/auth/me`).
> Endpoint-ы интервью пока публичны — изоляция обеспечивается на уровне БД-ключей.

---

## 5. UAT

Полные сценарии в [docs/acceptance_scenarios.md](docs/acceptance_scenarios.md).

**Краткий список 10 сценариев:**

| № | Название |
|---|----------|
| 1 | Регистрация / создание пользователя (email+пароль или Telegram) |
| 2 | Запуск интервью |
| 3 | Ответ на вопрос и получение оценки |
| 4 | Получение результата интервью |
| 5 | Адаптивный режим (v2) |
| 6 | Сохранность данных при перезапуске |
| 7 | Обработка недоступности LLM |
| 8 | Проверка CORS |
| 9 | Healthcheck и мониторинг |
| 10 | NPS / CSAT / CES метрики |

---

## 6. Дашборды Grafana

### Открыть

```
http://localhost:3000
Логин: daniiljermakiw  (или значение GRAFANA_USER из .env)
Пароль: из .env → GRAFANA_PASSWORD
```

Дашборды провизионируются автоматически при старте Grafana из папки
`monitoring/grafana/dashboards/`. Datasources (Prometheus + Loki) тоже подключаются автоматически.

### Фактически загруженные дашборды (проверено 2026-05-09)

```
Datasource: Prometheus [prometheus] — uid: PBFA97CFB590B2093  ✅
Datasource: Loki       [loki]       — uid: P8E80F9AEF21F6940  ✅

Dashboard: Sphinx — Executive / Business Overview   uid: sphinx-executive  ✅
Dashboard: Sphinx — Service Overview               uid: sphinx-service    ✅
Dashboard: Sphinx — Infrastructure / Resource      uid: sphinx-infra      ✅
Dashboard: Sphinx — Debugging / Deep Dive          uid: sphinx-debug      ✅
```

### Уровень 1 — Executive / Business Overview (`sphinx-executive`)

**Аудитория:** руководство, стейкхолдеры.

| Панель | Метрика |
|--------|---------|
| Total Interviews Started | `sphinx_interviews_started_total` |
| Average Score | `sphinx_average_score` |
| NPS Promoters % | `sphinx_nps_total{score=~"9\|10"}` |
| CSAT Average | `sphinx_csat_total` |
| Интервью по часам | rate за 1h |
| Интервью по уровням | pie chart by `level` |

### Уровень 2 — Service Overview (`sphinx-service`)

**Аудитория:** тимлиды, DevOps.

| Панель | Метрика |
|--------|---------|
| Backend Status (UP/DOWN) | `up{job="sphinx_backend"}` |
| Request Rate | `http_requests_total` |
| P95 Latency | `histogram_quantile(0.95, ...)` |
| Error Rate 5xx | rate статусов 5xx |
| Latency P50/P95/P99 | timeseries |
| HTTP Requests by Endpoint | по `handler` |
| HTTP Status Codes | по `status` |
| LLM Duration by Operation | `sphinx_llm_request_duration_seconds` |

### Уровень 3 — Infrastructure / Resource (`sphinx-infra`)

**Аудитория:** DevOps, SRE.

| Панель | Метрика |
|--------|---------|
| CPU Usage | `process_cpu_seconds_total` |
| RSS Memory | `process_resident_memory_bytes` |
| Active HTTP Requests | `sphinx_active_requests` |
| Open File Descriptors | `process_open_fds` |
| CPU / Memory timeseries | — |
| GC Collections | `python_gc_collections_total` |

### Уровень 4 — Debugging / Deep Dive (`sphinx-debug`)

**Аудитория:** разработчики при инциденте.

| Панель | Описание |
|--------|----------|
| Error Rate by Endpoint | 4xx/5xx по handler |
| P99 Latency by Endpoint | замедляющиеся endpoint-ы |
| Backend ERROR Logs (Loki) | фильтр `\|= "ERROR"` |
| All Backend Logs (Loki) | полный лог-стрим |
| Answers Submitted | rate ответов |
| LLM Duration Heatmap | P50/P95/P99 по операции |

---

## 7. Алерт на недоступность сервиса

### Как работает

```
Backend DOWN → Prometheus не может собрать /metrics →
rule BackendDown (up==0, 1m) → Alertmanager → Email на Gmail
```

### Конфигурация SMTP

Настройки прописаны **напрямую** в `monitoring/alertmanager/alertmanager.yml`
(Alertmanager не поддерживает `${ENV_VAR}` подстановку в конфиг-файле):

```yaml
global:
  smtp_smarthost: "smtp.gmail.com:587"
  smtp_from: "your@gmail.com"
  smtp_auth_username: "your@gmail.com"
  smtp_auth_password: "xxxx xxxx xxxx xxxx"   # App Password (не обычный пароль)
  smtp_require_tls: true
```

**Как получить App Password для Gmail:**
1. Аккаунт Google → Безопасность → Двухэтапная аутентификация (включить)
2. Безопасность → Пароли приложений → создать для «Почта» / «Другое»
3. Скопировать 16-значный пароль вида `xxxx xxxx xxxx xxxx`

### Тест алерта

```powershell
# 1. Убедиться, что всё запущено
docker compose ps

# 2. Остановить только backend
docker compose stop backend

# 3. Ждать ~1 минуту (for: 1m в alert rule)

# 4. Проверить статус алерта в Prometheus
Invoke-WebRequest http://localhost:9090/api/v1/alerts | ConvertFrom-Json

# 5. Проверить очередь в Alertmanager
# Открыть: http://localhost:9093

# 6. Email должен прийти на адрес из alertmanager.yml

# 7. Восстановить сервис
docker compose start backend
```

### Правила алертов (`monitoring/prometheus/alert_rules.yml`)

| Alert | Условие | Severity |
|-------|---------|----------|
| `BackendDown` | `up == 0` > 1 мин | critical |
| `HighErrorRate` | 5xx > 5% за 5 мин | warning |
| `HighLatency` | P95 > 3s за 5 мин | warning |

---

## 8. Логирование в Grafana (Loki)

### Архитектура

```
Все Docker-контейнеры → stdout/stderr
           ↓
     Promtail (docker_sd_configs — подключается к Docker socket)
           ↓
       Loki :3100
           ↓
    Grafana → Explore / Loki datasource / Panels
```

### Фактически собираемые сервисы (проверено 2026-05-09)

```
Loki labels: container, project, service

Services logging to Loki:
  alertmanager  ✅
  backend       ✅
  db            ✅
  frontend      ✅
  grafana       ✅
  loki          ✅
  prometheus    ✅
  promtail      ✅
```

### Запросы в Grafana Explore

1. Открыть Grafana → **Explore** → выбрать datasource **Loki**
2. Примеры запросов:

```logql
# Все логи backend
{service="backend"}

# Только ошибки
{service="backend"} |= "ERROR"

# LLM-связанные события
{service="backend"} |= "LLM"

# Логи БД
{service="db"}

# Все сервисы сразу
{project="sphinx"}
```

3. Дашборд **Debugging / Deep Dive** содержит готовые Loki-панели с ERROR-фильтром.

### Конфигурация Loki (`monitoring/loki/loki-config.yml`)

Используется схема `tsdb` + `filesystem` store через `common.path_prefix`.
Схема `boltdb-shipper` не используется — она несовместима с Windows Docker volumes.

---

## 9. NPS / CSAT / CES

### Endpoint-ы

| Method | URL | Payload | Ограничения |
|--------|-----|---------|-------------|
| `POST` | `/feedback/nps` | `{"score": 9, "user_id": 7}` | score: 0–10 |
| `POST` | `/feedback/csat` | `{"score": 4, "user_id": 7}` | score: 1–5 |
| `POST` | `/feedback/ces` | `{"score": 2, "user_id": 7}` | score: 1–7 |

### Пример запроса (проверено)

```powershell
# NPS
Invoke-WebRequest -Uri "http://localhost:8000/feedback/nps" `
  -Method POST -ContentType "application/json" `
  -Body '{"score": 9, "user_id": 7}'
# → 200 {"status":"ok","category":"promoter"}

# CSAT
Invoke-WebRequest -Uri "http://localhost:8000/feedback/csat" `
  -Method POST -ContentType "application/json" `
  -Body '{"score": 4, "user_id": 7}'
# → 200 {"status":"ok","category":"satisfied"}

# CES
Invoke-WebRequest -Uri "http://localhost:8000/feedback/ces" `
  -Method POST -ContentType "application/json" `
  -Body '{"score": 2, "user_id": 7}'
# → 200 {"status":"ok","category":"low_effort"}
```

### Метрики в Prometheus (`/metrics`)

```
# HELP sphinx_nps_total NPS responses bucketed by score (0-10)
sphinx_nps_total{score="9"} 1.0

# HELP sphinx_csat_total CSAT responses bucketed by score (1-5)
sphinx_csat_total{score="4"} 1.0

# HELP sphinx_ces_total CES responses bucketed by score (1-7)
sphinx_ces_total{score="2"} 1.0
```

### PromQL для дашборда Executive

```promql
# NPS Score = % Promoters - % Detractors
(
  sum(sphinx_nps_total{score=~"9|10"}) - sum(sphinx_nps_total{score=~"0|1|2|3|4|5|6"})
) / sum(sphinx_nps_total) * 100

# CSAT средний балл (взвешенная сумма)
sum by() (
  label_replace(sphinx_csat_total, "score_n", "$1", "score", "(.+)")
) / sum(sphinx_csat_total)

# CES (чем ниже — тем лучше)
sum by() (
  label_replace(sphinx_ces_total, "score_n", "$1", "score", "(.+)")
) / sum(sphinx_ces_total)
```

---

## Быстрый старт (всё сразу)

```powershell
# 1. Скопировать и заполнить .env
Copy-Item .env.example .env
# Проверить: DB_*, YANDEX_*, BOT_TOKEN, JWT_SECRET, GRAFANA_PASSWORD, BACKEND_URL, FRONTEND_URL

# 2. Заполнить alertmanager.yml реальными SMTP-данными
# monitoring/alertmanager/alertmanager.yml → smtp_auth_password = App Password

# 3. Запустить всё
docker compose up -d

# 4. Применить миграции БД
docker compose exec backend sh -c "cd /app/src && alembic -c alembic/alembic.ini upgrade head"

# 5. Проверить сервисы
Invoke-WebRequest http://localhost:8000/health    # {"status":"ok"}
Start-Process http://localhost:8000/docs          # Swagger UI
Start-Process http://localhost:3000               # Grafana
Start-Process http://localhost:9090               # Prometheus
Start-Process http://localhost:9093               # Alertmanager
Start-Process http://localhost:5173               # Frontend

# 6. Установить pytest в контейнер и запустить тесты
docker compose exec backend sh -c "pip install pytest pytest-asyncio httpx -q"
docker compose exec backend sh -c "cd /app && python -m pytest tests/test_unit.py tests/test_regression.py tests/test_security.py -v"

# 7. Нагрузочный тест (требует локального Python)
pip install locust
locust -f locustfile.py --host http://localhost:8000
# Открыть: http://localhost:8089

# 8. GUI-тесты
cd frontend
npx playwright test
```

---

## Проверка состояния всего стека одной командой

```powershell
$checks = @(
  @{name="Backend health";  url="http://localhost:8000/health"},
  @{name="Prometheus";      url="http://localhost:9090/-/healthy"},
  @{name="Alertmanager";    url="http://localhost:9093/-/healthy"},
  @{name="Grafana";         url="http://localhost:3000/api/health"},
  @{name="Loki";            url="http://localhost:3100/ready"}
)
foreach ($s in $checks) {
  try {
    $r = Invoke-WebRequest -Uri $s.url -ErrorAction Stop
    Write-Host "OK  [$($r.StatusCode)] $($s.name)"
  } catch {
    Write-Host "ERR $($s.name)"
  }
}
```

**Ожидаемый вывод:**
```
OK  [200] Backend health
OK  [200] Prometheus
OK  [200] Alertmanager
OK  [200] Grafana
OK  [200] Loki
```

---

## Структура добавленных файлов

```
sphinx/
├── backend/
│   ├── pytest.ini                                # asyncio_mode=auto, testpaths=tests
│   ├── src/app/
│   │   ├── metrics.py                            # Custom Prometheus metrics (NPS/CSAT/CES/LLM)
│   │   ├── core/security.py                      # JWT + bcrypt (без passlib)
│   │   └── api/routers/
│   │       ├── auth.py                           # /auth/register, /auth/login, /auth/telegram, /auth/me
│   │       └── feedback.py                       # /feedback/nps, /feedback/csat, /feedback/ces
│   └── tests/
│       ├── conftest.py                           # NullPool engine + MockLLMClient
│       ├── test_unit.py                          # 5 unit-тестов CRUD
│       ├── test_regression.py                    # 4 regression-теста
│       └── test_security.py                      # 25 security-тестов
├── frontend/
│   ├── tests/e2e/
│   │   └── interview_flow.spec.ts                # 6 Playwright E2E сценариев
│   └── playwright.config.ts
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml                        # Scrape config (backend + loki)
│   │   └── alert_rules.yml                       # BackendDown, HighErrorRate, HighLatency
│   ├── alertmanager/
│   │   └── alertmanager.yml                      # Gmail SMTP (заполнить App Password)
│   ├── loki/
│   │   ├── loki-config.yml                       # tsdb + filesystem (совместим с Windows Docker)
│   │   └── promtail-config.yml                   # docker_sd_configs → все контейнеры
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/datasources.yml       # Prometheus + Loki auto-connect
│       │   └── dashboards/dashboards.yml         # Dashboard folder config
│       └── dashboards/
│           ├── 01_executive_overview.json        # Level 1: Executive / Business
│           ├── 02_service_overview.json          # Level 2: Service Overview
│           ├── 03_infrastructure.json            # Level 3: Infrastructure / Resource
│           └── 04_debugging.json                 # Level 4: Debugging / Deep Dive
├── docs/
│   └── acceptance_scenarios.md                   # 10 UAT сценариев
├── locustfile.py                                  # Нагрузочный тест (Locust)
├── docker-compose.yml                             # Полный стек с мониторингом
└── .env.example                                   # Шаблон переменных окружения
```
