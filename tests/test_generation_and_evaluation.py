from pcaob_rag.evaluation import extract_answer_citations, summarize_human_review
from pcaob_rag.generation import REFUSAL_TEXT, build_grounded_prompt


def test_grounded_prompt_contains_source_and_refusal_rule():
    results = [
        {
            "citation": "[EY, 2024 inspection, PDF p. 20]",
            "text": "Example source evidence.",
        }
    ]
    prompt = build_grounded_prompt("What happened?", results)
    assert "Example source evidence." in prompt
    assert "[EY, 2024 inspection, PDF p. 20]" in prompt
    assert REFUSAL_TEXT in prompt


def test_citation_extraction_rejects_malformed_label():
    answer = (
        "Claim [EY, 2024 inspection, PDF p. 20]. "
        "Malformed [EY, 2024 inspection, p. 21]."
    )
    assert extract_answer_citations(answer) == [
        "[EY, 2024 inspection, PDF p. 20]"
    ]


def test_human_review_summary_uses_answerable_denominator():
    rows = [
        {
            "answerable_from_reports": "True",
            "retrieval_hit_human": "True",
            "rag_answer_supported_human": "True",
            "rag_citation_correct_human": "True",
            "rag_usefulness_1_to_5": "5",
            "refusal_correct_human": "",
            "plain_answer_supported_human": "False",
            "plain_usefulness_1_to_5": "1",
            "rag_better_than_plain_human": "True",
        },
        {
            "answerable_from_reports": "False",
            "retrieval_hit_human": "True",
            "rag_answer_supported_human": "True",
            "rag_citation_correct_human": "True",
            "rag_usefulness_1_to_5": "3",
            "refusal_correct_human": "True",
            "plain_answer_supported_human": "True",
            "plain_usefulness_1_to_5": "3",
            "rag_better_than_plain_human": "False",
        },
    ]
    summary = summarize_human_review(rows)
    assert summary["supported_answers"] == 1
    assert summary["correct_refusals"] == 1
    assert summary["rag_usefulness_answerable"] == 5

