import pytest
from fastapi.testclient import TestClient

from main import app
from eval import get_benchmark_runner, BENCHMARK_CASES


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def runner():
    return get_benchmark_runner()


def test_eval_cases_count():
    """Verify exactly 30 benchmark test cases are defined."""
    assert len(BENCHMARK_CASES) == 30

    categories = [c["category"] for c in BENCHMARK_CASES]
    assert categories.count("eligibility") == 10
    assert categories.count("citation") == 8
    assert categories.count("escalation") == 6
    assert categories.count("reconciliation") == 6


def test_runner_accuracy_metrics(runner):
    """Executes benchmark runner and verifies metrics calculation."""
    res = runner.run_all()
    assert res["total_cases"] == 30
    assert res["passed_cases"] >= 28
    assert res["overall_accuracy_pct"] >= 90.0

    dims = res["dimensions"]
    assert dims["eligibility_accuracy_pct"] == 100.0
    assert dims["citation_coverage_pct"] >= 85.0
    assert dims["escalation_correctness_pct"] == 100.0
    assert dims["reconciliation_recall_pct"] == 100.0


def test_api_eval_run_endpoint(client):
    """Tests POST /eval/run endpoint."""
    resp = client.post("/eval/run")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_accuracy_pct" in data
    assert "dimensions" in data
    assert len(data["cases"]) == 30
