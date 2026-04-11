import os

os.environ.setdefault("DB_USER", "sphinx_user")
os.environ.setdefault("DB_PASSWORD", "sphinx_pass")
os.environ.setdefault("DB_NAME", "sphinx_test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("YANDEX_API_KEY", "test_key")
os.environ.setdefault("YANDEX_API_KEY_ID", "test_key_id")
os.environ.setdefault("YANDEX_API_MODEL_URI", "test_model_uri")
os.environ.setdefault("YANDEX_CLOUD_CATALOG_ID", "test_catalog_id")
os.environ.setdefault("BOT_TOKEN", "")   # prevent Telegram bot from starting

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from src.app.main import app
from src.app.db.session import AsyncSessionLocal, engine
from src.app.db.base import Base
from src.app.db.session import get_db
from src.app.dependencies import get_llm_client, get_llm_client_new

# Mock LLM client — returns deterministic responses without hitting the API

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

# Fixtures

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once for the test session; drop them at the end."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Delete all rows after each test so tests are fully isolated."""
    yield
    async with AsyncSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db):
    """HTTP test client with DB and LLM dependencies overridden."""
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_client] = lambda: MockLLMClient()
    app.dependency_overrides[get_llm_client_new] = lambda: MockLLMClient()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
