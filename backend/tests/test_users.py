from httpx import AsyncClient


async def test_create_user(client: AsyncClient):
    response = await client.post("/users", json={"telegram_id": "123456789"})
    assert response.status_code == 200
    data = response.json()
    assert data["telegram_id"] == "123456789"
    assert "id" in data
    assert "created_at" in data


async def test_create_user_is_idempotent(client: AsyncClient):
    """Posting the same telegram_id twice must return the same user record."""
    r1 = await client.post("/users", json={"telegram_id": "same_user"})
    r2 = await client.post("/users", json={"telegram_id": "same_user"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


async def test_get_user_by_id(client: AsyncClient):
    create_resp = await client.post("/users", json={"telegram_id": "fetch_me"})
    user_id = create_resp.json()["id"]

    response = await client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["id"] == user_id
    assert response.json()["telegram_id"] == "fetch_me"


async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/users/99999")
    assert response.status_code == 404
    assert "detail" in response.json()
