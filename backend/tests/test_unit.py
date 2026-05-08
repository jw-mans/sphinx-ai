"""
Unit tests — testing CRUD layer directly without HTTP.
"""
import pytest
import pytest_asyncio

from src.app.db.crud.user import create_user, get_user, get_user_by_telegram_id
from src.app.schemas.user import UserCreate


class TestCreateUserUnit:
    """Unit tests for create_user CRUD function."""

    @pytest.mark.asyncio
    async def test_create_user_returns_user_with_correct_telegram_id(self, db):
        schema = UserCreate(telegram_id="unit_tg_001")
        user = await create_user(db, schema)

        assert user.id is not None
        assert user.telegram_id == "unit_tg_001"
        assert user.created_at is not None

    @pytest.mark.asyncio
    async def test_create_user_persists_to_db(self, db):
        schema = UserCreate(telegram_id="unit_tg_002")
        created = await create_user(db, schema)

        fetched = await get_user(db, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.telegram_id == "unit_tg_002"

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_returns_correct_user(self, db):
        schema = UserCreate(telegram_id="unit_tg_003")
        await create_user(db, schema)

        found = await get_user_by_telegram_id(db, "unit_tg_003")
        assert found is not None
        assert found.telegram_id == "unit_tg_003"

    @pytest.mark.asyncio
    async def test_get_user_nonexistent_returns_none(self, db):
        result = await get_user(db, 999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_unknown_telegram_id_returns_none(self, db):
        result = await get_user_by_telegram_id(db, "nonexistent_tg")
        assert result is None
