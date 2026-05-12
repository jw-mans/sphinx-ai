import os

os.environ.setdefault("DB_USER", "sphinx_user")
os.environ.setdefault("DB_PASSWORD", "sphinx_pass")
os.environ.setdefault("DB_NAME", "sphinx_db")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("YANDEX_API_KEY", "test_key")
os.environ.setdefault("YANDEX_API_KEY_ID", "test_key_id")
os.environ.setdefault("YANDEX_API_MODEL_URI", "test_model_uri")
os.environ.setdefault("YANDEX_CLOUD_CATALOG_ID", "test_catalog_id")
os.environ.setdefault("BOT_TOKEN", "")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-only")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from src.app.main import app
from src.app.db.base import Base
from src.app.db.session import get_db
from src.app.dependencies import get_llm_client, get_llm_client_new
from src.app.config import settings


# Allow overriding the DB for local development via TEST_DB_URL env var.
# Defaults to an in-process SQLite database so tests run without a real
# PostgreSQL instance.  In CI the DB service sets TEST_DB_URL to the
# PostgreSQL URL (or keeps it unset and relies on settings.DB_URL).
_TEST_DB_URL = os.environ.get("TEST_DB_URL", "sqlite+aiosqlite:///:memory:")

_is_sqlite = _TEST_DB_URL.startswith("sqlite")

# StaticPool keeps a single in-memory connection alive for the whole session
# (required for SQLite :memory:).  PostgreSQL uses NullPool to avoid
# "Future attached to a different loop" errors with pytest-asyncio.
if _is_sqlite:
    _test_engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    _test_engine = create_async_engine(_TEST_DB_URL, poolclass=NullPool)

_TestSession = async_sessionmaker(_test_engine, expire_on_commit=False)


class MockLLMClient:
    async def generate_question(self, level: str, stack: str, **kwargs) -> dict:
        return {
            "text": "What is a Python decorator and how does it work?",
            "topic": "Python decorators",
            "hints": ["Think about function wrapping"],
        }

    async def evaluate_answer(self, question: str, answer: str, **kwargs) -> dict:
        return {
            "score": {
                "correctness": 8,
                "optimality": 7,
                "complexity": 7,
                "explanation": 8,
                "gaps": 8,
            },
            "feedback": "Good answer with a clear explanation.",
            "weak_topics": [],
        }

    async def generate_session_summary(self, level: str, stack: str, results: list) -> dict:
        return {
            "overall": "Strong candidate overall.",
            "strengths": ["Python basics"],
            "weaknesses": [],
            "recommendations": ["Study advanced topics"],
        }

    async def extract_weak_topics(self, feedback: str) -> list:
        return []


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with _test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db():
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_client] = lambda: MockLLMClient()
    app.dependency_overrides[get_llm_client_new] = lambda: MockLLMClient()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
