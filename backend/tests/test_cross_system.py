"""
Cross-system integration tests: auth, interview (v1 & v2), feedback, DB layer.
LLM calls are mocked via MockLLMClient (conftest.py).
"""
from httpx import AsyncClient

# Shared helpers

async def _register(client, email="user@example.com", password="secret123", name="User"):
    r = await client.post("/auth/register", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    return r.json()


async def _login(client, email, password):
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


async def _auth_tg(client, telegram_id, name="TgUser"):
    r = await client.post("/auth/telegram", json={"telegram_id": telegram_id, "name": name})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"], data["access_token"]


async def _start_interview(client, user_id, token, level="junior", stack="Python"):
    r = await client.post(
        "/interview/start",
        json={"user_id": user_id, "level": level, "stack": stack},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()

# 1. Full web-auth flow: register → login → /auth/me

async def test_register_login_me_full_cycle(client: AsyncClient):
    email, password, name = "cycle@example.com", "pass1234", "CycleUser"
    reg = await _register(client, email, password, name)
    log = await _login(client, email, password)

    assert reg["user"]["id"] == log["user"]["id"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {log['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == reg["user"]["id"]

# 2. Telegram auth → 5-question v1 interview

async def test_telegram_user_completes_full_v1_interview(client: AsyncClient):
    user, token = await _auth_tg(client, "tg_cross_v1")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        r_ans = await client.post(f"/interview/{iid}/answer", json={"text": f"answer {i}"}, headers=hdrs)
        assert r_ans.status_code == 200, f"Answer {i} failed: {r_ans.text}"
        if i < 4:
            r_q = await client.get(f"/interview/{iid}/question", headers=hdrs)
            assert r_q.status_code == 200

    r_result = await client.get(f"/interview/{iid}/result", headers=hdrs)
    assert r_result.status_code == 200
    result = r_result.json()
    assert len(result["questions_results"]) == 5
    assert result["summary"] is not None
    for key in ("correctness", "optimality", "complexity", "explanation", "gaps"):
        assert key in result["average_score"]

# 3. Web user → 5-question v2 interview

async def test_web_user_completes_full_v2_interview(client: AsyncClient):
    reg = await _register(client, "webv2@example.com")
    uid = reg["user"]["id"]
    token = reg["access_token"]
    hdrs = {"Authorization": f"Bearer {token}"}

    interview = await _start_interview(client, uid, token, level="senior", stack="FastAPI")
    iid = interview["interview_id"]

    for i in range(5):
        r_ans = await client.post(f"/interview/{iid}/answer/v2", json={"text": f"v2 answer {i}"}, headers=hdrs)
        assert r_ans.status_code == 200, f"V2 answer {i} failed: {r_ans.text}"
        if i < 4:
            r_q = await client.get(f"/interview/{iid}/question/v2", headers=hdrs)
            assert r_q.status_code == 200
            assert "id" in r_q.json()

    r_result = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    assert r_result.status_code == 200
    assert len(r_result.json()["questions_results"]) == 5

# 4. Interview → NPS/CSAT/CES feedback after completing

async def test_feedback_submitted_after_interview(client: AsyncClient):
    user, token = await _auth_tg(client, "tg_feedback_cs")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer", json={"text": "decorator answer"}, headers=hdrs)

    assert (await client.post("/feedback/nps", json={"score": 9, "interview_id": iid})).status_code == 200
    assert (await client.post("/feedback/csat", json={"score": 5, "interview_id": iid})).status_code == 200
    assert (await client.post("/feedback/ces", json={"score": 2, "interview_id": iid})).status_code == 200

# 5. Two users' interviews are isolated from each other

async def test_two_users_interviews_are_independent(client: AsyncClient):
    user_a, token_a = await _auth_tg(client, "tg_cross_a")
    user_b, token_b = await _auth_tg(client, "tg_cross_b")

    iv_a = await _start_interview(client, user_a["id"], token_a, stack="Go")
    iv_b = await _start_interview(client, user_b["id"], token_b, stack="Rust")
    iid_a, iid_b = iv_a["interview_id"], iv_b["interview_id"]

    await client.post(f"/interview/{iid_a}/answer", json={"text": "Go answer"},
                      headers={"Authorization": f"Bearer {token_a}"})

    res_b = (await client.get(f"/interview/{iid_b}/result",
                              headers={"Authorization": f"Bearer {token_b}"})).json()
    assert res_b["questions_results"] == []

    res_a = (await client.get(f"/interview/{iid_a}/result",
                              headers={"Authorization": f"Bearer {token_a}"})).json()
    assert len(res_a["questions_results"]) == 1

# 6. Security: user A cannot access user B's interview

async def test_cross_user_access_is_forbidden(client: AsyncClient):
    user_a, token_a = await _auth_tg(client, "tg_sec_a")
    user_b, token_b = await _auth_tg(client, "tg_sec_b")

    iv_b = await _start_interview(client, user_b["id"], token_b)
    iid_b = iv_b["interview_id"]

    for method, path, body in [
        ("GET", f"/interview/{iid_b}/question", None),
        ("POST", f"/interview/{iid_b}/answer", {"text": "attack"}),
        ("GET", f"/interview/{iid_b}/result", None),
        ("GET", f"/interview/{iid_b}/question/v2", None),
        ("POST", f"/interview/{iid_b}/answer/v2", {"text": "attack"}),
        ("GET", f"/interview/{iid_b}/result/v2", None),
    ]:
        hdrs = {"Authorization": f"Bearer {token_a}"}
        if method == "GET":
            r = await client.get(path, headers=hdrs)
        else:
            r = await client.post(path, json=body, headers=hdrs)
        assert r.status_code == 403, f"{method} {path} returned {r.status_code}, expected 403"

# 7. user_notes propagate into interview start

async def test_interview_with_user_notes(client: AsyncClient):
    user, token = await _auth_tg(client, "tg_notes_cs")
    r = await client.post(
        "/interview/start",
        json={"user_id": user["id"], "level": "middle", "stack": "Django",
              "user_notes": "Focus on ORM and migrations"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "interview_id" in r.json()

# 8. Token from register valid throughout session

async def test_register_token_valid_throughout_session(client: AsyncClient):
    reg = await _register(client, "persist@example.com")
    token = reg["access_token"]

    for _ in range(3):
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "persist@example.com"

# 9. Telegram auth → v2 interview

async def test_telegram_auth_then_v2_interview(client: AsyncClient):
    user, token = await _auth_tg(client, "tg_cross_v2")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    r_ans = await client.post(f"/interview/{iid}/answer/v2", json={"text": "cross system"}, headers=hdrs)
    assert r_ans.status_code == 200

    r_result = await client.get(f"/interview/{iid}/result/v2", headers=hdrs)
    assert r_result.status_code == 200
    assert len(r_result.json()["questions_results"]) == 1

# 10. Health check is always reachable

async def test_health_endpoint_reachable(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

# 11. Sequential answers accumulate in result

async def test_sequential_answers_accumulate_in_result(client: AsyncClient):
    user, token = await _auth_tg(client, "tg_seq_accum_cs")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    for n in range(3):
        r_ans = await client.post(f"/interview/{iid}/answer", json={"text": f"answer {n}"}, headers=hdrs)
        assert r_ans.status_code == 200
        if n < 2:
            r_q = await client.get(f"/interview/{iid}/question", headers=hdrs)
            assert r_q.status_code == 200

    result = (await client.get(f"/interview/{iid}/result", headers=hdrs)).json()
    assert len(result["questions_results"]) == 3

# 12. Average score computed correctly from mock values

async def test_average_score_computed_correctly(client: AsyncClient):
    """MockLLMClient always returns fixed scores (8,7,7,8,8)."""
    user, token = await _auth_tg(client, "tg_avg_check_cs")
    interview = await _start_interview(client, user["id"], token)
    iid = interview["interview_id"]
    hdrs = {"Authorization": f"Bearer {token}"}

    await client.post(f"/interview/{iid}/answer", json={"text": "answer"}, headers=hdrs)

    result = (await client.get(f"/interview/{iid}/result", headers=hdrs)).json()
    avg = result["average_score"]
    assert avg["correctness"] == 8
    assert avg["optimality"] == 7
    assert avg["complexity"] == 7
    assert avg["explanation"] == 8
    assert avg["gaps"] == 8
