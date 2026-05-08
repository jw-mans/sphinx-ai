"""
Custom Prometheus metrics for Sphinx.

Import this module once (in main.py lifespan) to register the metrics.
Use the exported counters/histograms in routers and services.
"""
from prometheus_client import Counter, Histogram, Gauge

# ---------------------------------------------------------------------------
# Interview lifecycle
# ---------------------------------------------------------------------------

interviews_started = Counter(
    "sphinx_interviews_started_total",
    "Total number of interviews started",
    ["level", "stack"],
)

interviews_completed = Counter(
    "sphinx_interviews_completed_total",
    "Total number of interviews with at least one answer",
)

answers_submitted = Counter(
    "sphinx_answers_submitted_total",
    "Total answers submitted",
)

llm_request_duration = Histogram(
    "sphinx_llm_request_duration_seconds",
    "Time spent waiting for LLM responses",
    ["operation"],  # generate_question | evaluate_answer | generate_summary
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60],
)

average_score_gauge = Gauge(
    "sphinx_average_score",
    "Rolling average interview score (updated on result fetch)",
)

# ---------------------------------------------------------------------------
# User satisfaction (NPS / CSAT / CES)
# ---------------------------------------------------------------------------

nps_scores = Counter(
    "sphinx_nps_total",
    "NPS responses bucketed by score (0-10)",
    ["score"],
)

csat_scores = Counter(
    "sphinx_csat_total",
    "CSAT responses bucketed by score (1-5)",
    ["score"],
)

ces_scores = Counter(
    "sphinx_ces_total",
    "CES responses bucketed by score (1-7)",
    ["score"],
)

# ---------------------------------------------------------------------------
# HTTP / infrastructure (supplementary — main HTTP metrics come from
# prometheus-fastapi-instrumentator)
# ---------------------------------------------------------------------------

active_requests = Gauge(
    "sphinx_active_requests",
    "Number of requests currently being processed",
)
