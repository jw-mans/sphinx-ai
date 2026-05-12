"""
Load test for Sphinx API — simulates concurrent users going through a full
interview session (start → answer → result).

Run:
    pip install locust
    locust -f locustfile.py --host http://localhost:8000

Then open http://localhost:8089 and set:
  - Number of users:  50
  - Spawn rate:       10 users/s
  - Host:             http://localhost:8000
"""
import random
import string

from locust import HttpUser, TaskSet, task, between, events


def _random_tg_id() -> str:
    return "load_" + "".join(random.choices(string.digits, k=10))


class InterviewSession(TaskSet):
    """Simulates one full interview round-trip per virtual user."""

    user_id: int | None = None
    interview_id: int | None = None

    def on_start(self):
        """Called once per simulated user — create or get the DB user."""
        tg_id = _random_tg_id()
        with self.client.post(
            "/users",
            json={"telegram_id": tg_id},
            name="/users [create]",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                self.user_id = r.json()["id"]
            else:
                r.failure(f"User creation failed: {r.status_code}")

    @task(1)
    def full_interview_flow(self):
        if self.user_id is None:
            return

        # 1. Start interview
        with self.client.post(
            "/interview/start",
            json={"user_id": self.user_id, "level": "junior", "stack": "Python"},
            name="/interview/start",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Start failed: {r.status_code}")
                return
            self.interview_id = r.json()["interview_id"]

        # 2. Submit an answer
        with self.client.post(
            f"/interview/{self.interview_id}/answer",
            json={"text": "A decorator wraps a function to modify its behaviour."},
            name="/interview/{id}/answer",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Answer failed: {r.status_code}")
                return

        # 3. Get result
        with self.client.get(
            f"/interview/{self.interview_id}/result",
            name="/interview/{id}/result",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Result failed: {r.status_code}")

    @task(2)
    def health_check(self):
        self.client.get("/health", name="/health")


class SphinxUser(HttpUser):
    tasks = [InterviewSession]
    wait_time = between(1, 3)
    host = "http://localhost:8000"

# Print summary stats on quit

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats
    total = stats.total
    print("\n=== Load Test Summary ===")
    print(f"  Requests  : {total.num_requests}")
    print(f"  Failures  : {total.num_failures}")
    print(f"  Median RT : {total.median_response_time} ms")
    print(f"  95th pct  : {total.get_response_time_percentile(0.95)} ms")
    print(f"  RPS       : {total.current_rps:.1f}")
