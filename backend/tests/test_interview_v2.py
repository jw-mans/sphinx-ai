"""
Tests for the v2 interview endpoints:
  - GET  /interview/{id}/question/v2
  - POST /interview/{id}/answer/v2
  - GET  /interview/{id}/result/v2
"""
from httpx import AsyncClient


async def _auth_user(client: AsyncClient, telegram_id: str = "tg_v2") -> tuple:
    r = await client.post("/auth/telegram", json={"telegram_id": telegram_id, "name": "V2User"})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"], data["access_token"]


async def _start_interview(client, user_id, token, level="junior", stack="Python", user_notes=None):
    body = {"user_id": user_id, "level": level, "stack": stack}
    if user_notes:
        body["user_notes"] = user_notes
    r = await client.post(
        "/interview/start", json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- question/v2 ---

async def test_v2_get_question_returns_question_fields(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_q")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "some answer"}, headers=hdrs)
    r = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
    assert r.status_code == 200, r.text
    for key in ("id", "text", "topic", "difficulty"):
        assert key in r.json()


async def test_v2_get_question_unknown_interview_returns_404(client: AsyncClient):
    _, token = await _auth_user(client, "tg_v2_q404")
    r = await client.get("/interview/99999/question/v2", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


async def test_v2_get_question_no_token_returns_401(client: AsyncClient):
    assert (await client.get("/interview/1/question/v2")).status_code == 401


async def test_v2_get_question_returns_unanswered_first(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_unans")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    r = await client.get(f"/interview/{iid}/question/v2", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["id"] == interview["current_question"]["id"]


async def test_v2_get_question_returns_completed_when_done(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_done")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        await client.post(f"/interview/{iid}/answer/v2", json={"text": f"a{i}"}, headers=hdrs)
        if i < 4:
            await client.get(f"/interview/{iid}/question/v2", headers=hdrs)

    r = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
    assert r.json().get("message") == "Interview completed"


# --- answer/v2 ---

async def test_v2_submit_answer_returns_evaluation(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_ans")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/interview/{iid}/answer/v2", json={"text": "decorator wraps function"}, headers=hdrs)
    assert r.status_code == 200
    ev = r.json()["evaluation"]
    assert "score" in ev and "feedback" in ev and "weak_topics" in ev


async def test_v2_submit_answer_with_code(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_code")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/interview/{iid}/answer/v2",
        json={"text": "decorator example:", "code": "def d(f):\n    def w(): return f()\n    return w"},
        headers=hdrs)
    assert r.status_code == 200
    assert "evaluation" in r.json()


async def test_v2_double_answer_returns_409(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_409")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "first"}, headers=hdrs)
    r = await client.post(f"/interview/{iid}/answer/v2", json={"text": "second"}, headers=hdrs)
    assert r.status_code == 409


async def test_v2_answer_unknown_interview_returns_404(client: AsyncClient):
    _, token = await _auth_user(client, "tg_v2_ans404")
    r = await client.post("/interview/99999/answer/v2", json={"text": "x"},
        headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


async def test_v2_answer_no_token_returns_401(client: AsyncClient):
    assert (await client.post("/interview/1/answer/v2", json={"text": "x"})).status_code == 401


async def test_v2_answer_score_structure(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_score")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/interview/{iid}/answer/v2", json={"text": "answer"}, headers=hdrs)
    score = r.json()["evaluation"]["score"]
    for key in ("correctness", "optimality", "complexity", "explanation", "gaps"):
        assert key in score


# --- result/v2 ---

async def test_v2_result_after_one_answer(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_res1")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "answer"}, headers=hdrs)
    r = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    assert r.status_code == 200
    data = r.json()
    assert len(data["questions_results"]) == 1
    assert data["summary"] is not None


async def test_v2_result_empty_interview(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_empty")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["questions_results"] == []


async def test_v2_result_unknown_interview_returns_404(client: AsyncClient):
    _, token = await _auth_user(client, "tg_v2_res404")
    r = await client.get("/interview/99999/result/v2", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


async def test_v2_result_no_token_returns_401(client: AsyncClient):
    assert (await client.get("/interview/1/result/v2")).status_code == 401


async def test_v2_result_has_average_score_keys(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_avgkeys")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "something"}, headers=hdrs)
    r = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    avg = r.json()["average_score"]
    for key in ("correctness", "optimality", "complexity", "explanation", "gaps"):
        assert key in avg


# --- full 5-question flow ---

async def test_v2_full_flow_five_questions(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_full")
    interview = await _start_interview(client, user["id"], token, level="middle", stack="FastAPI")
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        r_ans = await client.post(f"/interview/{iid}/answer/v2", json={"text": f"answer {i}"}, headers=hdrs)
        assert r_ans.status_code == 200, f"answer {i}: {r_ans.text}"
        if i < 4:
            r_q = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
            assert "id" in r_q.json(), f"round {i+1}: {r_q.json()}"

    r = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    assert len(r.json()["questions_results"]) == 5
    assert r.json()["summary"] is not None


async def test_v2_full_flow_prior_avg_propagated(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v2_prior")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "first"}, headers=hdrs)
    r_q2 = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
    assert "id" in r_q2.json()

    r2 = await client.post(f"/interview/{iid}/answer/v2", json={"text": "second"}, headers=hdrs)
    assert r2.status_code == 200
    assert r2.json()["evaluation"]["score"] is not None


async def test_v1_and_v2_endpoints_share_same_interview(client: AsyncClient):
    user, token = await _auth_user(client, "tg_v1v2_mix")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer/v2", json={"text": "mixed"}, headers=hdrs)
    r_q = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
    assert "id" in r_q.json()

    r_result = await client.get(f"/interview/{iid}/result", headers=hdrs)
    assert len(r_result.json()["questions_results"]) == 1
