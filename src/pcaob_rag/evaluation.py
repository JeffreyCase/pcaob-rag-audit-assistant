"""Small, auditable evaluation helpers used by the portfolio prototype."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from statistics import fmean

CITATION_PATTERN = re.compile(
    r"\[(?:Deloitte|EY), 20(?:22|23|24) inspection, PDF p\. \d+\]"
)


def extract_answer_citations(answer: str) -> list[str]:
    """Return citation labels that follow the prototype's exact format."""

    return CITATION_PATTERN.findall(answer)


def automatic_retrieval_hit(test_case: Mapping, retrieved) -> bool:
    """Apply the original benchmark's transparent retrieval checks."""

    retrieved_citations = set(retrieved["citation"])
    expected_citations = set(test_case.get("expected_citations", []))
    minimum_matches = int(test_case.get("expected_min_citation_matches", 0))
    if expected_citations:
        return len(retrieved_citations & expected_citations) >= minimum_matches

    retrieved_firms = set(retrieved["firm_short"])
    if test_case["expected_firm"] == "Both":
        return retrieved_firms == {"Deloitte", "EY"}
    return (
        test_case["expected_firm"] in retrieved_firms
        and int(test_case["expected_year"]) in set(retrieved["inspection_year"])
    )


def _as_bool(value) -> bool:
    return str(value).strip().casefold() == "true"


def summarize_human_review(rows: Iterable[Mapping]) -> dict:
    """Calculate the project's public, human-reviewed headline metrics."""

    records = list(rows)
    answerable = [r for r in records if _as_bool(r["answerable_from_reports"])]
    unsupported = [r for r in records if not _as_bool(r["answerable_from_reports"])]
    supported = [r for r in answerable if _as_bool(r["rag_answer_supported_human"])]

    return {
        "benchmark_questions": len(records),
        "retrieval_checks_passed": sum(
            _as_bool(r["retrieval_hit_human"]) for r in records
        ),
        "answerable_questions": len(answerable),
        "supported_answers": len(supported),
        "correct_citations_among_supported": sum(
            _as_bool(r["rag_citation_correct_human"]) for r in supported
        ),
        "unsupported_questions": len(unsupported),
        "correct_refusals": sum(
            _as_bool(r["refusal_correct_human"]) for r in unsupported
        ),
        "rag_usefulness_answerable": round(
            fmean(float(r["rag_usefulness_1_to_5"]) for r in answerable), 2
        ),
        "plain_usefulness_answerable": round(
            fmean(float(r["plain_usefulness_1_to_5"]) for r in answerable), 2
        ),
        "plain_supported_answerable": sum(
            _as_bool(r["plain_answer_supported_human"]) for r in answerable
        ),
        "rag_better_answerable": sum(
            _as_bool(r["rag_better_than_plain_human"]) for r in answerable
        ),
    }
