"""
Regression tests — guard against previously identified bugs.

Bug-1: POST /users with duplicate telegram_id must be idempotent (return existing
       user, not raise 500/409 from a DB unique-constraint violation).

Bug-2: Submitting an answer when no unanswered question is pending must return 409,
       not 500 (previously an unhandled ConflictError propagated as a 500).

Bug-3: GET /interview/{id}/result on an interview with zero answers must return
       an empty list, not crash.
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def _make_user(client: AsyncClient, tg: str = "reg_tg") -> dict:
    r = await client.post("/users", json={"telegram_id": tg})
    assert r.status_code == 200, r.text
    return r.json()


async def _start(client: AsyncClient, user_id: int) -> int:
    r = await client.post("/interview/start", json={
        "user_id": user_id, "level": "junior", "stack": "Python",
    })
    assert r.status_code == 200, r.text
    return r.json()["interview_id"]


# ---------------------------------------------------------------------------
# Bug-1: idempotent user creation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_telegram_id_returns_same_user(client: AsyncClient):
    """Two POST /users with the same telegram_id must return the same user record."""
    first = await _make_user(client, "reg_dup")
    second_r = await client.post("/users", json={"telegram_id": "reg_dup"})

    assert second_r.status_code == 200
    second = second_r.json()
    assert second["id"] == first["id"]
    assert second["telegram_id"] == first["telegram_id"]


# ---------------------------------------------------------------------------
# Bug-2: double-answer returns 409, not 500
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_double_answer_returns_409_not_500(client: AsyncClient):
    """
    After answering the only pending question, a second answer attempt must
    return 409 Conflict — not 500 Internal Server Error.
    """
    user = await _make_user(client, "reg_double")
    iid = await _start(client, user["id"])

    r1 = await client.post(f"/interview/{iid}/answer", json={"text": "First answer"})
    assert r1.status_code == 200

    r2 = await client.post(f"/interview/{iid}/answer", json={"text": "Second answer"})
    assert r2.status_code == 409
    assert r2.status_code != 500


# ---------------------------------------------------------------------------
# Bug-3: result with zero answers returns empty list, not crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_result_with_no_answers_is_empty_list(client: AsyncClient):
    """
    GET /interview/{id}/result immediately after start (no answers yet) must
    return 200 with an empty questions_results list.
    """
    user = await _make_user(client, "reg_empty")
    iid = await _start(client, user["id"])

    r = await client.get(f"/interview/{iid}/result")
    assert r.status_code == 200
    data = r.json()
    assert data["questions_results"] == []
    avg = data["average_score"]
    # average_score may be scalar 0/None or a per-category dict of zeros
    if isinstance(avg, dict):
        assert all(v == 0 for v in avg.values())
    else:
        assert avg == 0 or avg is None


# ---------------------------------------------------------------------------
# Bug-4: unknown interview always returns 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_interview_is_404_on_all_endpoints(client: AsyncClient):
    bad_id = 99999

    r_q = await client.get(f"/interview/{bad_id}/question")
    r_a = await client.post(f"/interview/{bad_id}/answer", json={"text": "x"})
    r_res = await client.get(f"/interview/{bad_id}/result")

    assert r_q.status_code == 404
    assert r_a.status_code == 404
    assert r_res.status_code == 404
