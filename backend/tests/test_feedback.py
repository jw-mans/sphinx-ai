"""
Tests for feedback collection endpoints:
  - POST /feedback/nps   (0-10 scale, detractor / passive / promoter)
  - POST /feedback/csat  (1-5 scale)
  - POST /feedback/ces   (1-7 scale, lower = easier)
"""
import pytest
from httpx import AsyncClient

# POST /feedback/nps

class TestNPS:
    async def test_nps_valid_score_returns_ok(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 8})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ok"

    async def test_nps_score_zero_is_detractor(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 0})
        assert r.status_code == 200
        assert r.json()["category"] == "detractor"

    async def test_nps_score_six_is_detractor(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 6})
        assert r.json()["category"] == "detractor"

    async def test_nps_score_seven_is_passive(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 7})
        assert r.json()["category"] == "passive"

    async def test_nps_score_eight_is_passive(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 8})
        assert r.json()["category"] == "passive"

    async def test_nps_score_nine_is_promoter(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 9})
        assert r.json()["category"] == "promoter"

    async def test_nps_score_ten_is_promoter(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 10})
        assert r.json()["category"] == "promoter"

    async def test_nps_score_too_high_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 11})
        assert r.status_code == 422

    async def test_nps_score_negative_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": -1})
        assert r.status_code == 422

    async def test_nps_with_interview_id(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 9, "interview_id": 42})
        assert r.status_code == 200

    async def test_nps_with_comment(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"score": 5, "comment": "Great tool!"})
        assert r.status_code == 200

    async def test_nps_with_all_fields(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={
            "score": 10,
            "interview_id": 1,
            "comment": "Loved it",
        })
        assert r.status_code == 200
        assert r.json()["category"] == "promoter"

    async def test_nps_missing_score_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/nps", json={"comment": "no score"})
        assert r.status_code == 422

    @pytest.mark.parametrize("score,expected_category", [
        (0, "detractor"),
        (3, "detractor"),
        (6, "detractor"),
        (7, "passive"),
        (8, "passive"),
        (9, "promoter"),
        (10, "promoter"),
    ])
    async def test_nps_all_boundary_categories(self, client: AsyncClient, score, expected_category):
        r = await client.post("/feedback/nps", json={"score": score})
        assert r.status_code == 200
        assert r.json()["category"] == expected_category

# POST /feedback/csat

class TestCSAT:
    async def test_csat_valid_score_returns_ok(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 4})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_csat_min_score_is_valid(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 1})
        assert r.status_code == 200

    async def test_csat_max_score_is_valid(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 5})
        assert r.status_code == 200

    async def test_csat_score_zero_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 0})
        assert r.status_code == 422

    async def test_csat_score_six_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 6})
        assert r.status_code == 422

    async def test_csat_negative_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": -1})
        assert r.status_code == 422

    async def test_csat_with_optional_fields(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={"score": 3, "interview_id": 99, "comment": "ok"})
        assert r.status_code == 200

    async def test_csat_missing_score_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/csat", json={})
        assert r.status_code == 422

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    async def test_csat_all_valid_scores(self, client: AsyncClient, score):
        r = await client.post("/feedback/csat", json={"score": score})
        assert r.status_code == 200

# POST /feedback/ces

class TestCES:
    async def test_ces_valid_score_returns_ok(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 3})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    async def test_ces_min_score_is_valid(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 1})
        assert r.status_code == 200

    async def test_ces_max_score_is_valid(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 7})
        assert r.status_code == 200

    async def test_ces_score_zero_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 0})
        assert r.status_code == 422

    async def test_ces_score_eight_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 8})
        assert r.status_code == 422

    async def test_ces_negative_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": -1})
        assert r.status_code == 422

    async def test_ces_with_optional_fields(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={"score": 2, "interview_id": 7, "comment": "easy"})
        assert r.status_code == 200

    async def test_ces_missing_score_returns_422(self, client: AsyncClient):
        r = await client.post("/feedback/ces", json={})
        assert r.status_code == 422

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5, 6, 7])
    async def test_ces_all_valid_scores(self, client: AsyncClient, score):
        r = await client.post("/feedback/ces", json={"score": score})
        assert r.status_code == 200
