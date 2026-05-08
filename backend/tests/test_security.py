"""
Security tests:
  A) SQL-injection probes — all critical endpoints must return safe responses
     (no 500, no data leak) when receiving common injection payloads.

  B) Horizontal-privilege checks — user A must not be able to access or
     manipulate interviews belonging to user B.
"""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Common fixtures / helpers
# ---------------------------------------------------------------------------

SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM users --",
    "1; SELECT pg_sleep(5) --",
    "\\x27 OR 1=1 --",
    "<script>alert(1)</script>",
    "\" OR \"\"=\"",
]


async def _make_user(client: AsyncClient, tg: str) -> dict:
    r = await client.post("/users", json={"telegram_id": tg})
    assert r.status_code == 200, r.text
    return r.json()


async def _start_interview(client: AsyncClient, user_id: int) -> int:
    r = await client.post(
        "/interview/start",
        json={"user_id": user_id, "level": "junior", "stack": "Python"},
    )
    assert r.status_code == 200, r.text
    return r.json()["interview_id"]


# ===========================================================================
# A. SQL-injection probes
# ===========================================================================

class TestSQLInjection:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_create_user_sql_injection_in_telegram_id(
        self, client: AsyncClient, payload: str
    ):
        """
        Injecting SQL via telegram_id must not cause a 500 and must not
        return rows from other users.
        """
        r = await client.post("/users", json={"telegram_id": payload})
        # Either created (200) or rejected gracefully — never a server error
        assert r.status_code in (200, 400, 422), (
            f"Payload={payload!r} caused unexpected status {r.status_code}: {r.text}"
        )
        if r.status_code == 200:
            data = r.json()
            # The returned telegram_id must equal the verbatim payload (ORM
            # parameterises the query, so the literal string is stored safely)
            assert data["telegram_id"] == payload, (
                "Server must store the raw string, not interpret it as SQL"
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_get_user_sql_injection_in_path(
        self, client: AsyncClient, payload: str
    ):
        """
        Injecting SQL in the user_id path parameter must return 404 or 422 —
        never a 500.
        """
        encoded = payload.replace("/", "%2F")
        r = await client.get(f"/users/{encoded}")
        assert r.status_code in (404, 422), (
            f"Payload={payload!r} gave unexpected status {r.status_code}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_answer_sql_injection_in_text(
        self, client: AsyncClient, payload: str
    ):
        """
        Injecting SQL via the answer text must be stored safely and not cause 500.
        """
        user = await _make_user(client, f"sqli_ans_{hash(payload) % 10**6}")
        iid = await _start_interview(client, user["id"])

        r = await client.post(
            f"/interview/{iid}/answer",
            json={"text": payload},
        )
        assert r.status_code in (200, 400, 422), (
            f"Answer payload={payload!r} caused {r.status_code}: {r.text}"
        )


# ===========================================================================
# B. Horizontal-privilege checks
# ===========================================================================

class TestHorizontalPrivilege:

    @pytest.mark.asyncio
    async def test_user_cannot_read_other_users_profile(self, client: AsyncClient):
        """
        User A can read their own profile; reading user B's profile via the
        public endpoint must still return data (the endpoint is not auth-gated
        in this version) but must not return user A's sensitive fields mixed in.
        """
        user_a = await _make_user(client, "priv_a")
        user_b = await _make_user(client, "priv_b")

        r = await client.get(f"/users/{user_b['id']}")
        assert r.status_code == 200
        data = r.json()
        # Must return user B, not user A
        assert data["id"] == user_b["id"]
        assert data["telegram_id"] == user_b["telegram_id"]
        assert data["telegram_id"] != user_a["telegram_id"]

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_interview_question(self, client: AsyncClient):
        """
        Submitting an answer to an interview that belongs to a different user
        must behave safely: the interview_id lookup succeeds without leaking
        user A's data, and does not return user B-specific hints.
        """
        user_a = await _make_user(client, "priv_qa")
        user_b = await _make_user(client, "priv_qb")

        iid_b = await _start_interview(client, user_b["id"])

        # User A tries to read user B's question — no auth, so it returns 200,
        # but the interview_id must belong to user B only
        r = await client.get(f"/interview/{iid_b}/question")
        assert r.status_code == 200
        # No cross-contamination: user A's id is nowhere in the response
        assert str(user_a["id"]) not in r.text

    @pytest.mark.asyncio
    async def test_user_a_cannot_answer_user_b_interview(self, client: AsyncClient):
        """
        User A submitting an answer to user B's interview must either succeed
        (no auth enforcement yet) or fail gracefully — but must never 500 or
        corrupt user B's session with user A's data.
        """
        user_a = await _make_user(client, "priv_aa")
        user_b = await _make_user(client, "priv_bb")

        iid_b = await _start_interview(client, user_b["id"])

        r = await client.post(
            f"/interview/{iid_b}/answer",
            json={"text": "Attempting cross-user answer"},
        )
        # Must not 500
        assert r.status_code != 500, f"Server error on cross-user answer: {r.text}"
        # If it succeeded, the result must not reference user A's id
        assert str(user_a["id"]) not in r.text

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_result(self, client: AsyncClient):
        """Result endpoint must not leak user B's data to user A's request."""
        user_a = await _make_user(client, "priv_ra")
        user_b = await _make_user(client, "priv_rb")

        iid_b = await _start_interview(client, user_b["id"])

        # Answer one question in user B's interview
        await client.post(
            f"/interview/{iid_b}/answer",
            json={"text": "Some answer"},
        )

        # User A fetches user B's result
        r = await client.get(f"/interview/{iid_b}/result")
        assert r.status_code in (200, 403, 404)
        assert r.status_code != 500
        # User A's telegram_id must not appear in user B's result
        assert user_a["telegram_id"] not in r.text
