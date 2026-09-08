"""Build a portable static demo directly from the project's saved results."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
STATUS = {
    "Supported answer": "supported",
    "Correct refusal": "refusal",
    "Generation failure": "failure",
}
TITLES = {
    "Q05": "Contract completeness",
    "Q02": "Substantive analytics",
    "Q12": "An unsupported ranking",
    "Q08": "When the model over-refused",
}


def page_link(source: dict) -> tuple[str, int]:
    """Use physical PDF page numbers, preserving the official URL's query."""
    page = re.search(r"PDF p\. (\d+)", source["citation"])
    if page is None:
        raise ValueError(f"Missing PDF page: {source['citation']}")
    url = urlsplit(source["source_url"])
    if url.scheme != "https" or url.hostname != "assets.pcaobus.org":
        raise ValueError("Expected an official PCAOB HTTPS source")
    number = int(page.group(1))
    return urlunsplit(url._replace(fragment=f"page={number}")), number


def answer_html(example: dict) -> str:
    answer = escape(example["answer"])
    for source in example["sources"]:
        citation = escape(source["citation"])
        url, _ = page_link(source)
        answer = answer.replace(
            citation,
            f'<a class="inline-citation" href="{escape(url, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{citation}</a>',
        )
    return answer


def render_example(example: dict) -> str:
    kind = STATUS[example["status"]]
    sources = []
    for source in example["sources"]:
        url, page = page_link(source)
        citation = escape(source["citation"].strip("[]"))
        sources.append(
            f'<div class="source"><div class="source-title">{citation}</div>'
            f'<p>{escape(source["excerpt"])}</p>'
            f'<a href="{escape(url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">Open official PDF · page {page} ↗</a></div>'
        )
    if sources:
        evidence = (
            '<p class="label">Source notes · selected report passages</p>'
            f'<div class="sources">{"".join(sources)}</div>'
            '<p class="page-note">Source notes may be abridged. Links use PDF page '
            'numbers, which can differ from printed page numbers. If your PDF viewer '
            'opens at the start, go to the indicated PDF page.</p>'
        )
    else:
        evidence = (
            '<p class="empty-source">No source excerpt is presented: these six '
            'reports do not support an overall firm-quality ranking.</p>'
        )
    return (
        f'<article class="example" id="{escape(example["question_id"])}" '
        f'data-status="{kind}" aria-labelledby="question-{example["question_id"]}">'
        '<div class="example-meta"><span>Saved benchmark example · '
        f'{escape(example["question_id"])}</span><span class="status {kind}">'
        f'{escape(example["status"])}</span></div>'
        f'<h3 id="question-{example["question_id"]}">{escape(example["question"])}</h3>'
        '<p class="label">Saved model response</p>'
        f'<div class="answer"><p>{answer_html(example)}</p></div>{evidence}'
        '<p class="review"><strong>Human-review note</strong>'
        f'{escape(example["review_note"])}</p></article>'
    )


def build(output: str = "dist") -> Path:
    if output not in {"dist", "docs"}:
        raise ValueError("Output must be dist or docs")
    examples = json.loads((ROOT / "data/demo_answers.json").read_text(encoding="utf-8"))
    evaluation = json.loads(
        (ROOT / "results/evaluation_summary.json").read_text(encoding="utf-8")
    )
    metrics = evaluation["metrics"]
    ids = [item["question_id"] for item in examples]
    if len(ids) != len(set(ids)) or set(ids) != set(TITLES):
        raise ValueError("Expected the four distinct reviewed demonstration examples")
    metric_rows = [
        ("Predefined retrieval checks", "retrieval_checks_passed", "retrieval_checks_total", "All benchmark questions"),
        ("Supported answers", "supported_answers", "answerable_questions", "Among answerable questions"),
        ("Correct citations", "correct_citations_among_supported", "supported_answers", "Among supported answers"),
        ("Correct refusals", "correct_refusals", "unsupported_questions", "Among unsupported questions"),
    ]
    metric_html = "".join(
        f'<div class="metric"><strong>{metrics[n]}/{metrics[d]}</strong>'
        f'<span class="metric-label">{label}</span><small>{detail}</small></div>'
        for label, n, d, detail in metric_rows
    )
    result_rows = [(label, f"{metrics[n]}/{metrics[d]}") for label, n, d, _ in metric_rows]
    result_rows.extend([
        ("Correct overall RAG behavior", f'{metrics["correct_rag_behavior"]}/{metrics["retrieval_checks_total"]}'),
        ("Average usefulness · grounded RAG", f'{metrics["rag_usefulness_answerable"]:.2f}/5'),
        ("Average usefulness · plain model", f'{metrics["plain_usefulness_answerable"]:.2f}/5'),
        ("Plain-model answers supported by selected reports", f'{metrics["plain_supported_answerable"]}/{metrics["answerable_questions"]}'),
    ])
    nav = "".join(
        f'<a class="example-link" href="#{item["question_id"]}">'
        f'<span class="example-number">{item["question_id"]}</span>'
        f'<strong>{TITLES[item["question_id"]]}</strong>'
        f'<span class="mini-status {STATUS[item["status"]]}">{escape(item["status"])}</span></a>'
        for item in examples
    )
    html = (ROOT / "portfolio/index.html").read_text(encoding="utf-8")
    for marker, value in {
        "METRICS": metric_html,
        "BASELINE": str(metrics["first_prototype_retrieval_hits"]),
        "NAV": nav,
        "EXAMPLES": "".join(render_example(item) for item in examples),
        "RESULTS": "".join(f'<tr><th scope="row">{label}</th><td>{value}</td></tr>' for label, value in result_rows),
    }.items():
        html = html.replace("{{" + marker + "}}", value)
    if re.search(r"\{\{\w+\}\}", html):
        raise ValueError("Unresolved template marker")
    destination = ROOT / output
    destination.mkdir(exist_ok=True)
    (destination / "index.html").write_text(html, encoding="utf-8")
    for asset in ("styles.css", "app.js", "favicon.svg"):
        shutil.copyfile(ROOT / "portfolio" / asset, destination / asset)
    if output == "docs":
        (destination / ".nojekyll").write_text("", encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", choices=("dist", "docs"), default="dist",
        help="Build into dist (default), or docs for GitHub Pages.",
    )
    args = parser.parse_args()
    print(f"Built static portfolio: {build(args.output)}")
