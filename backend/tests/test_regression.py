"""
Regression tests — guard against previously identified bugs.

Bug-1: POST /users with duplicate telegram_id must be idempotent.
Bug-2: Submitting an answer when no unanswered question is pending → 409, not 500.
Bug-3: GET /interview/{id}/result with zero answers → empty list, not crash.
Bug-4: Unknown interview → 404 on all endpoints.
"""
import pytest
from httpx import AsyncClient


# helpers

async def _auth_user(client: AsyncClient, tg: str = "reg_tg") -> tuple:
    r = await client.post("/auth/telegram", json={"telegram_id": tg, "name": "RegUser"})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"], data["access_token"]


async def _start(client: AsyncClient, user_id: int, token: str) -> int:
    r = await client.post(
        "/interview/start",
        json={"user_id": user_id, "level": "junior", "stack": "Python"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["interview_id"]

# Bug-1: idempotent user creation

@pytest.mark.asyncio
async def test_duplicate_telegram_id_returns_same_user(client: AsyncClient):
    """Two POST /users with the same telegram_id must return the same user record."""
    r1 = await client.post("/users", json={"telegram_id": "reg_dup"})
    r2 = await client.post("/users", json={"telegram_id": "reg_dup"})
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["telegram_id"] == r2.json()["telegram_id"]

# Bug-2: double-answer returns 409, not 500

@pytest.mark.asyncio
async def test_double_answer_returns_409_not_500(client: AsyncClient):
    user, token = await _auth_user(client, "reg_double")
    iid = await _start(client, user["id"], token)
    hdrs = {"Authorization": f"Bearer {token}"}

    r1 = await client.post(f"/interview/{iid}/answer", json={"text": "First answer"}, headers=hdrs)
    assert r1.status_code == 200

    r2 = await client.post(f"/interview/{iid}/answer", json={"text": "Second answer"}, headers=hdrs)
    assert r2.status_code == 409
    assert r2.status_code != 500

# Bug-3: result with zero answers returns empty list, not crash

@pytest.mark.asyncio
async def test_result_with_no_answers_is_empty_list(client: AsyncClient):
    user, token = await _auth_user(client, "reg_empty")
    iid = await _start(client, user["id"], token)
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/interview/{iid}/result", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert data["questions_results"] == []
    avg = data["average_score"]
    if isinstance(avg, dict):
        assert all(v == 0 for v in avg.values())
    else:
        assert avg == 0 or avg is None

# Bug-4: unknown interview always returns 404 (with valid auth)

@pytest.mark.asyncio
async def test_unknown_interview_is_404_on_all_endpoints(client: AsyncClient):
    _, token = await _auth_user(client, "reg_404")
    bad_id = 99999
    hdrs = {"Authorization": f"Bearer {token}"}

    r_q = await client.get(f"/interview/{bad_id}/question", headers=hdrs)
    r_a = await client.post(f"/interview/{bad_id}/answer", json={"text": "x"}, headers=hdrs)
    r_res = await client.get(f"/interview/{bad_id}/result", headers=hdrs)

    assert r_q.status_code == 404
    assert r_a.status_code == 404
    assert r_res.status_code == 404
