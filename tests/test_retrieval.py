import pandas as pd

from pcaob_rag.retrieval import Retriever, infer_question_scope


def fake_chunks():
    return pd.DataFrame(
        [
            {
                "text": "Revenue data were not tested for completeness.",
                "firm_short": "Deloitte",
                "inspection_year": 2023,
                "citation": "[Deloitte, 2023 inspection, PDF p. 20]",
            },
            {
                "text": "Revenue reports lacked accuracy and completeness controls.",
                "firm_short": "EY",
                "inspection_year": 2023,
                "citation": "[EY, 2023 inspection, PDF p. 20]",
            },
            {
                "text": "A contract review population was incomplete.",
                "firm_short": "EY",
                "inspection_year": 2024,
                "citation": "[EY, 2024 inspection, PDF p. 20]",
            },
        ]
    )


def test_scope_inference_for_single_firm_and_year():
    firms, years = infer_question_scope("What did EY identify in 2024?")
    assert firms == ["EY"]
    assert years == [2024]


def test_scope_inference_for_selected_reports():
    firms, years = infer_question_scope(
        "Across the selected reports from 2022-2024, what recurred?"
    )
    assert firms == ["Deloitte", "EY"]
    assert years == [2022, 2023, 2024]


def test_cross_firm_retrieval_returns_both_firms():
    results = Retriever(fake_chunks()).retrieve(
        "Across the selected reports, what revenue deficiencies recur?",
        k=2,
        method="tfidf",
    )
    assert set(results["firm_short"]) == {"Deloitte", "EY"}
    assert results["citation"].is_unique

