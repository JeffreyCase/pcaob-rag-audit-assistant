"""One-page, precomputed portfolio demo for nontechnical reviewers."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
GITHUB_URL = "https://github.com/JeffreyCase/pcaob-rag-audit-assistant"


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
      .block-container {max-width:1120px; padding-top:4rem; padding-bottom:3rem;}
      .hero-kicker {color:#138f7a; font-weight:700; letter-spacing:.08em;
                    text-transform:uppercase; font-size:.85rem;}
      .answer-card {background:#f7f9fc; color:#1f2937;
                    border-left:5px solid #18a98f; border-radius:8px;
                    padding:1.25rem 1.4rem; margin:.75rem 0 1rem;
                    line-height:1.6;}
      .status {display:inline-block; border-radius:999px; padding:.28rem .7rem;
               font-size:.82rem; font-weight:700;}
      .status-supported {background:#e3f5f0; color:#0e6f60;}
      .status-refusal {background:#e8eef8; color:#31547c;}
      .status-limitation {background:#fff0dc; color:#8a4b08;}
      .process-card {min-height:142px; border:1px solid rgba(19,143,122,.22);
                     border-radius:10px; padding:1rem;
                     background:rgba(19,143,122,.06);}
      .process-number {color:#138f7a; font-size:.78rem; font-weight:800;
                       letter-spacing:.06em; text-transform:uppercase;}
      .process-title {font-size:1.02rem; font-weight:750; margin:.2rem 0 .35rem;}
      .process-copy {font-size:.9rem; line-height:1.45;}
      div[data-testid="stMetric"] {border:1px solid rgba(19,143,122,.18);
                                   border-radius:10px; padding:.75rem 1rem;
                                   background:rgba(19,143,122,.05);}
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
    st.link_button("View GitHub repository", GITHUB_URL, use_container_width=True)
    st.caption(
        "I originally developed this prototype with three classmates in the Rutgers "
        "MAcc program. I built the Python pipeline and independently converted the "
        "submitted prototype into this public portfolio demonstration."
    )

st.markdown(
    '<div class="hero-kicker">Audit analytics portfolio project</div>',
    unsafe_allow_html=True,
)
st.title("PCAOB RAG Audit Assistant")
st.write(
    "A source-grounded research prototype designed to help junior auditors explore "
    "selected PCAOB inspection findings and trace every substantive claim to a "
    "report page."
)
st.info(
    "Educational coaching only — not audit evidence, authoritative guidance, or a "
    "substitute for professional judgment and review."
)

st.markdown("### Human-reviewed benchmark")
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Retrieval checks",
    f'{metrics["retrieval_checks_passed"]}/{metrics["retrieval_checks_total"]}',
)
c2.metric(
    "Supported answers",
    f'{metrics["supported_answers"]}/{metrics["answerable_questions"]}',
)
c3.metric(
    "Correct refusals",
    f'{metrics["correct_refusals"]}/{metrics["unsupported_questions"]}',
)
usefulness_delta = (
    metrics["rag_usefulness_answerable"] - metrics["plain_usefulness_answerable"]
)
c4.metric(
    "Usefulness",
    f'{metrics["rag_usefulness_answerable"]:.1f}/5',
    f"+{usefulness_delta:.1f} vs. plain model",
)

st.caption(
    "Results apply only to the defined 12-question benchmark. Seven of eight supported "
    "answers had fully correct citations. These results do not establish general or "
    "production accuracy."
)

demo_tab, method_tab = st.tabs(
    ["Explore reviewed examples", "How it works & governance"]
)

with demo_tab:
    labels = [item["label"] for item in demo_answers]
    selected_label = st.selectbox("Choose a reviewed example", labels)
    example = next(item for item in demo_answers if item["label"] == selected_label)

    status_class = {
        "Supported answer": "status-supported",
        "Correct refusal": "status-refusal",
        "Generation failure": "status-limitation",
    }.get(example["status"], "status-refusal")

    st.subheader("Question")
    st.write(example["question"])
    st.markdown(
        f'<span class="status {status_class}">{escape(example["status"])}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="answer-card">{escape(example["answer"])}</div>',
        unsafe_allow_html=True,
    )

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

with method_tab:
    st.subheader("The pipeline in plain English")
    steps = [
        (
            "Step 1",
            "Extract",
            "Read six public PCAOB reports and preserve report and page metadata.",
        ),
        (
            "Step 2",
            "Retrieve",
            "Search focused text passages using TF-IDF and semantic embeddings.",
        ),
        (
            "Step 3",
            "Generate",
            "Ask Gemini to answer only from retrieved evidence and attach citations.",
        ),
        (
            "Step 4",
            "Review",
            "Check retrieval, support, citations, usefulness, and refusal behavior.",
        ),
    ]
    process_columns = st.columns(4)
    for column, (number, title, copy) in zip(process_columns, steps, strict=True):
        with column:
            st.markdown(
                '<div class="process-card">'
                f'<div class="process-number">{number}</div>'
                f'<div class="process-title">{title}</div>'
                f'<div class="process-copy">{copy}</div>'
                "</div>",
                unsafe_allow_html=True,
            )

    st.subheader("Controls and professional judgment")
    st.markdown(
        """
        - **Source grounding:** substantive claims should trace to a PCAOB
          report page.
        - **Refusal behavior:** unsupported questions should be declined rather
          than guessed.
        - **Human review:** an auditor must inspect the source and apply relevant
          standards and firm methodology before relying on any guidance.
        - **Public-data scope:** the prototype excludes confidential client information.
        """
    )

    st.subheader("Known limitations")
    st.markdown(
        """
        - Six reports, two firms, three inspection years, one audit topic, and
          12 questions.
        - One supported answer contained a malformed citation label.
        - One answer was incorrectly refused even though the correct evidence
          was retrieved.
        - No practicing-auditor pilot, production security review, or firm-methodology
          integration has been completed.
        """
    )

    with st.expander("Project origin, portfolio work, and AI assistance"):
        st.write(
            "I originally developed this prototype with three classmates in the "
            "Rutgers Master of Accountancy program. I built the Python pipeline and "
            "corresponding technical, testing, and results materials. My teammates "
            "and I shared the audit framing, written deliverables, and final "
            "presentation. After submission, I independently reorganized the "
            "codebase, built and deployed this no-key Streamlit demonstration, added "
            "tests and public governance documentation, and validated the portfolio "
            "edition. I used Gemini as the generation and comparison model, while "
            "other generative-AI tools assisted portions of brainstorming, code "
            "refinement, drafting, and review. I reviewed and tested the public "
            "portfolio changes before publication."
        )
