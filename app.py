"""One-page, precomputed portfolio demo for nontechnical reviewers."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent


@st.cache_data
def load_json(relative_path: str):
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


demo_answers = load_json("data/demo_answers.json")
evaluation = load_json("results/evaluation_summary.json")
metrics = evaluation["metrics"]

st.set_page_config(
    page_title="PCAOB RAG Audit Assistant",
    page_icon="🔎",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {max-width: 1120px; padding-top: 2rem;}
      .hero-kicker {color:#138f7a; font-weight:700; letter-spacing:.08em;
                    text-transform:uppercase; font-size:.85rem;}
      .answer-card {background:#f7f9fc; border-left:5px solid #18a98f;
                    border-radius:8px; padding:1.25rem 1.4rem; margin:.75rem 0 1rem;}
      .status {display:inline-block; border-radius:999px; padding:.25rem .65rem;
               background:#e3f5f0; color:#0e6f60; font-size:.82rem; font-weight:700;}
      .small-note {color:#596579; font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Prototype scope")
    st.markdown(
        """
        - **Sources:** 6 public PCAOB reports
        - **Firms:** Deloitte and EY
        - **Inspection years:** 2022–2024
        - **Topic:** Revenue-related findings in Part I.A
        """
    )
    st.divider()
    st.caption(
        "This demo displays saved, human-reviewed outputs. It does not require an "
        "API key and does not send recruiter questions to an external model."
    )

st.markdown('<div class="hero-kicker">Audit analytics portfolio project</div>', unsafe_allow_html=True)
st.title("PCAOB RAG Audit Assistant")
st.write(
    "A source-grounded research prototype designed to help junior auditors explore "
    "selected PCAOB inspection findings and trace every substantive claim to a report page."
)
st.info(
    "Educational coaching only — not audit evidence, authoritative guidance, or a "
    "substitute for professional judgment and review."
)

labels = [item["label"] for item in demo_answers]
selected_label = st.selectbox("Choose a reviewed example", labels)
example = next(item for item in demo_answers if item["label"] == selected_label)

st.subheader("Question")
st.write(example["question"])
st.markdown(f'<span class="status">{example["status"]}</span>', unsafe_allow_html=True)
st.markdown(f'<div class="answer-card">{example["answer"]}</div>', unsafe_allow_html=True)

if example["sources"]:
    st.subheader("Source evidence")
    for source in example["sources"]:
        with st.expander(source["citation"], expanded=True):
            st.write(source["excerpt"])
            st.link_button("Open official PCAOB report", source["source_url"])
else:
    st.caption(
        "No source excerpt is presented because the correct behavior was to refuse "
        "an unsupported firm-quality ranking."
    )

st.markdown(f'**Human-review note:** {example["review_note"]}')

st.divider()
st.subheader("Evaluation snapshot")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Supported answers", f'{metrics["supported_answers"]}/{metrics["answerable_questions"]}')
c2.metric("Correct citations", f'{metrics["correct_citations_among_supported"]}/{metrics["supported_answers"]}')
c3.metric("Correct refusals", f'{metrics["correct_refusals"]}/{metrics["unsupported_questions"]}')
c4.metric(
    "Usefulness",
    f'{metrics["rag_usefulness_answerable"]:.1f}/5',
    f'+{metrics["rag_usefulness_answerable"] - metrics["plain_usefulness_answerable"]:.1f} vs. plain model',
)

st.caption(
    "Results apply only to a 12-question academic benchmark. The prototype covered "
    "two firms, three inspection years, and one audit topic; it has not been tested "
    "with practicing auditors or validated for production use."
)

