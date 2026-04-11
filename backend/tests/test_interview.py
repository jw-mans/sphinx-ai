from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(client: AsyncClient, telegram_id: str = "tg_test") -> dict:
    r = await client.post("/users", json={"telegram_id": telegram_id})
    assert r.status_code == 200, r.text
    return r.json()


async def _start_interview(client: AsyncClient, user_id: int, level: str = "junior") -> dict:
    r = await client.post("/interview/start", json={
        "user_id": user_id,
        "level": level,
        "stack": "Python",
    })
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------------------
# /interview/start
# ---------------------------------------------------------------------------

async def test_start_interview_returns_first_question(client: AsyncClient):
    user = await _create_user(client)
    data = await _start_interview(client, user["id"])

    assert "interview_id" in data
    q = data["current_question"]
    assert "id" in q
    assert "text" in q
    assert "topic" in q
    assert "difficulty" in q


async def test_start_interview_unknown_user_is_404(client: AsyncClient):
    r = await client.post("/interview/start", json={
        "user_id": 99999,
        "level": "junior",
        "stack": "Python",
    })
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /interview/{id}/question
# ---------------------------------------------------------------------------

async def test_get_current_question(client: AsyncClient):
    user = await _create_user(client, "tg_q")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    r = await client.get(f"/interview/{interview_id}/question")
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert "topic" in data


async def test_get_question_unknown_interview_is_404(client: AsyncClient):
    r = await client.get("/interview/99999/question")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /interview/{id}/answer
# ---------------------------------------------------------------------------

async def test_submit_answer_returns_evaluation(client: AsyncClient):
    user = await _create_user(client, "tg_ans")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    r = await client.post(
        f"/interview/{interview_id}/answer",
        json={"text": "A decorator wraps a function to extend its behaviour."},
    )
    assert r.status_code == 200
    data = r.json()
    assert "evaluation" in data
    evaluation = data["evaluation"]
    assert "score" in evaluation
    assert "feedback" in evaluation
    assert "weak_topics" in evaluation


async def test_submit_answer_with_code(client: AsyncClient):
    user = await _create_user(client, "tg_code")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    r = await client.post(
        f"/interview/{interview_id}/answer",
        json={
            "text": "Here is an example decorator:",
            "code": "def my_decorator(func):\n    def wrapper(*args, **kwargs):\n        return func(*args, **kwargs)\n    return wrapper",
        },
    )
    assert r.status_code == 200
    assert "evaluation" in r.json()


async def test_submit_answer_no_unanswered_is_409(client: AsyncClient):
    """Submitting an answer when no question is pending must return 409."""
    user = await _create_user(client, "tg_409")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    # Answer the first question
    await client.post(
        f"/interview/{interview_id}/answer",
        json={"text": "First answer"},
    )
    # Answer again without a new question being fetched — no unanswered question exists
    r = await client.post(
        f"/interview/{interview_id}/answer",
        json={"text": "Second answer without a question"},
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# /interview/{id}/result
# ---------------------------------------------------------------------------

async def test_get_result_after_answering(client: AsyncClient):
    user = await _create_user(client, "tg_res")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    await client.post(
        f"/interview/{interview_id}/answer",
        json={"text": "A decorator adds behaviour to a function."},
    )

    r = await client.get(f"/interview/{interview_id}/result")
    assert r.status_code == 200
    data = r.json()
    assert "average_score" in data
    assert "questions_results" in data
    assert len(data["questions_results"]) == 1
    assert data["summary"] is not None


async def test_get_result_empty_interview(client: AsyncClient):
    """Result of an interview with no answers yet should return empty lists."""
    user = await _create_user(client, "tg_empty")
    interview = await _start_interview(client, user["id"])
    interview_id = interview["interview_id"]

    r = await client.get(f"/interview/{interview_id}/result")
    assert r.status_code == 200
    data = r.json()
    assert data["questions_results"] == []


async def test_get_result_unknown_interview_is_404(client: AsyncClient):
    r = await client.get("/interview/99999/result")
    assert r.status_code == 404
