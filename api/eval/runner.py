import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from rag.service import RAGService
from rules.engine import evaluate_profile
from reconcile.matcher import DocumentReconciler
from .dataset import BENCHMARK_CASES


class BenchmarkRunner:
    """Evaluates CivicPilot accuracy across Eligibility, Citations, Escalation, and Reconciliation."""

    def __init__(self, rag_service: Optional[RAGService] = None, reconciler: Optional[DocumentReconciler] = None):
        self.rag = rag_service or RAGService()
        self.reconciler = reconciler or DocumentReconciler()

    def run_all(self) -> Dict[str, Any]:
        start_time = time.time()
        results: List[Dict[str, Any]] = []

        elig_correct = 0
        elig_total = 0

        cite_correct = 0
        cite_total = 0

        esc_correct = 0
        esc_total = 0

        recon_correct = 0
        recon_total = 0

        for case in BENCHMARK_CASES:
            cid = case["id"]
            cat = case["category"]
            cname = case["name"]
            t0 = time.time()
            passed = False
            details: Dict[str, Any] = {}

            # 1. Eligibility Evaluation
            if cat == "eligibility":
                elig_total += 1
                try:
                    eval_res = evaluate_profile(case["input"])
                    verdict = eval_res.get("verdict") if isinstance(eval_res, dict) else eval_res.verdict
                    passed = verdict == case["expected_verdict"]
                    if passed:
                        elig_correct += 1
                    failed_list = eval_res.get("failed_rules", []) if isinstance(eval_res, dict) else eval_res.failed_rules
                    details = {
                        "actual_verdict": verdict,
                        "expected_verdict": case["expected_verdict"],
                        "failed_rules_count": len(failed_list),
                    }
                except Exception as e:
                    passed = False
                    details = {"error": str(e)}

            # 2. Citation Coverage
            elif cat == "citation":
                cite_total += 1
                try:
                    rag_res = self.rag.ask(case["question"])
                    actual_citations = [c.id for c in rag_res.citations]
                    expected_list = case["expected_clause_ids"]
                    # Passed if at least one expected clause is cited
                    overlap = [c for c in actual_citations if any(exp in c for exp in expected_list)]
                    passed = len(overlap) > 0
                    if passed:
                        cite_correct += 1
                    details = {
                        "actual_citations": actual_citations,
                        "expected_clause_ids": expected_list,
                        "matching_citations": overlap,
                    }
                except Exception as e:
                    passed = False
                    details = {"error": str(e)}

            # 3. Escalation Correctness
            elif cat == "escalation":
                esc_total += 1
                try:
                    rag_res = self.rag.ask(case["question"])
                    actual_esc = rag_res.needs_escalation
                    expected_esc = case["expected_needs_escalation"]
                    passed = actual_esc == expected_esc
                    if passed:
                        esc_correct += 1
                    details = {
                        "actual_needs_escalation": actual_esc,
                        "expected_needs_escalation": expected_esc,
                        "confidence": rag_res.confidence,
                    }
                except Exception as e:
                    passed = False
                    details = {"error": str(e)}

            # 4. Reconciliation Recall
            elif cat == "reconciliation":
                recon_total += 1
                try:
                    recon_res = self.reconciler.reconcile(case["docs"])
                    expected_field = case.get("expected_discrepant_field")

                    if expected_field is None:
                        # Expecting all matched
                        passed = (recon_res.overall_status == "MATCHED") or (len(recon_res.discrepancies) == 0)
                    else:
                        disc_fields = [d.field for d in recon_res.discrepancies]
                        passed = expected_field in disc_fields

                    if passed:
                        recon_correct += 1

                    details = {
                        "discrepancies_detected": [d.field for d in recon_res.discrepancies],
                        "expected_discrepant_field": expected_field,
                        "overall_status": recon_res.overall_status,
                    }
                except Exception as e:
                    passed = False
                    details = {"error": str(e)}

            elapsed_ms = round((time.time() - t0) * 1000, 1)
            results.append(
                {
                    "id": cid,
                    "category": cat,
                    "name": cname,
                    "passed": passed,
                    "latency_ms": elapsed_ms,
                    "details": details,
                }
            )

        total_elapsed = round(time.time() - start_time, 2)
        total_cases = len(BENCHMARK_CASES)
        passed_cases = sum(1 for r in results if r["passed"])

        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "overall_accuracy_pct": round((passed_cases / total_cases) * 100, 1),
            "execution_duration_sec": total_elapsed,
            "dimensions": {
                "eligibility_accuracy_pct": round((elig_correct / elig_total) * 100, 1) if elig_total else 0,
                "eligibility_cases": f"{elig_correct}/{elig_total}",
                "citation_coverage_pct": round((cite_correct / cite_total) * 100, 1) if cite_total else 0,
                "citation_cases": f"{cite_correct}/{cite_total}",
                "escalation_correctness_pct": round((esc_correct / esc_total) * 100, 1) if esc_total else 0,
                "escalation_cases": f"{esc_correct}/{esc_total}",
                "reconciliation_recall_pct": round((recon_correct / recon_total) * 100, 1) if recon_total else 0,
                "reconciliation_cases": f"{recon_correct}/{recon_total}",
            },
            "cases": results,
        }

        return metrics


# Singleton
_benchmark_runner: Optional[BenchmarkRunner] = None


def get_benchmark_runner() -> BenchmarkRunner:
    global _benchmark_runner
    if _benchmark_runner is None:
        _benchmark_runner = BenchmarkRunner()
    return _benchmark_runner
