"""Download, extract, and chunk selected public PCAOB inspection reports."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

import fitz
import pandas as pd

PART_IA_HEADING = "PART I.A: AUDITS WITH UNSUPPORTED OPINIONS"
PART_IB_HEADING = "PART I.B: OTHER INSTANCES OF NON-COMPLIANCE"

TOPIC_PATTERN = re.compile(
    r"\b(revenue|deferred revenue|accounts receivable|contract|"
    r"performance obligation|standalone selling price|sales incentive)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class ReportSpec:
    """Metadata for one public inspection report."""

    firm: str
    firm_short: str
    inspection_year: int
    filename: str
    source_url: str


def load_report_manifest(path: str | Path) -> list[ReportSpec]:
    """Load the six-report project scope from JSON."""

    with Path(path).open(encoding="utf-8") as handle:
        records = json.load(handle)
    return [ReportSpec(**record) for record in records]


def pdf_is_readable(path: str | Path) -> bool:
    """Return True when a path looks like a valid, non-empty PDF."""

    pdf_path = Path(path)
    if not pdf_path.exists() or pdf_path.stat().st_size <= 50_000:
        return False
    try:
        with fitz.open(pdf_path) as document:
            return document.page_count > 0
    except Exception:
        return False


def download_report(spec: ReportSpec, destination_dir: str | Path) -> Path:
    """Download one report from its official PCAOB URL when not cached."""

    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / spec.filename

    if pdf_is_readable(destination):
        return destination

    temporary_path = destination.with_suffix(".download")
    request = Request(
        spec.source_url,
        headers={"User-Agent": "PCAOB RAG academic portfolio prototype"},
    )
    with (
        urlopen(request, timeout=60) as response,
        temporary_path.open("wb") as output_file,
    ):
        shutil.copyfileobj(response, output_file)

    if not pdf_is_readable(temporary_path):
        temporary_path.unlink(missing_ok=True)
        raise ValueError(f"Downloaded file is not a readable PDF: {spec.filename}")

    temporary_path.replace(destination)
    return destination


def clean_page_text(text: str) -> str:
    """Normalize extracted PDF text without changing substantive wording."""

    text = text.replace("\u00ad", "")
    text = re.sub(r"-\s*\n\s*(?=[a-z])", "", text)
    text = re.sub(
        r"(Deloitte & Touche LLP|Ernst & Young LLP),\s*"
        r"PCAOB Release No\.[^|\n]+\|\s*[A-Z0-9\-]+",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip()


def extract_pages(spec: ReportSpec, pdf_path: str | Path) -> list[dict]:
    """Extract text and citation metadata page by page."""

    page_rows: list[dict] = []
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_rows.append(
                {
                    **asdict(spec),
                    "pdf_page": page_index + 1,
                    "text": clean_page_text(page.get_text("text")),
                }
            )
    return page_rows


def find_part_ia_bounds(report_pages: Iterable[dict]) -> tuple[int, int]:
    """Locate the detailed Part I.A section and the start of Part I.B."""

    pages = list(report_pages)
    start_pages = [
        row["pdf_page"]
        for row in pages
        if row["pdf_page"] > 10 and PART_IA_HEADING in row["text"].upper()
    ]
    if not start_pages:
        raise ValueError("Could not locate the detailed Part I.A heading.")

    start_page = min(start_pages)
    end_pages = [
        row["pdf_page"]
        for row in pages
        if row["pdf_page"] > start_page
        and PART_IB_HEADING in row["text"].upper()
    ]
    if not end_pages:
        raise ValueError("Could not locate the detailed Part I.B heading.")
    return start_page, min(end_pages)


def select_part_ia_pages(report_pages: Iterable[dict]) -> list[dict]:
    """Keep only the detailed Part I.A pages used by this prototype."""

    pages = list(report_pages)
    start_page, end_page = find_part_ia_bounds(pages)
    return [
        row for row in pages if start_page <= row["pdf_page"] < end_page
    ]


def split_into_word_chunks(
    text: str,
    target_words: int = 350,
    overlap_words: int = 75,
    minimum_words: int = 80,
) -> list[str]:
    """Split text into overlapping word windows."""

    if overlap_words >= target_words:
        raise ValueError("overlap_words must be smaller than target_words")

    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        chunk_text = " ".join(words[start:end])
        if len(chunk_text.split()) >= minimum_words:
            chunks.append(chunk_text)
        if end == len(words):
            break
        start = end - overlap_words
    return chunks


def build_revenue_chunks(part_ia_pages: Iterable[dict]) -> pd.DataFrame:
    """Build revenue-focused chunks plus adjacent same-page context."""

    raw_chunks: list[dict] = []
    for page in part_ia_pages:
        for chunk_number, text in enumerate(
            split_into_word_chunks(page["text"]), start=1
        ):
            raw_chunks.append(
                {
                    **{key: value for key, value in page.items() if key != "text"},
                    "chunk_number": chunk_number,
                    "chunk_id": (
                        f'{page["firm_short"].lower()}_'
                        f'{page["inspection_year"]}_'
                        f'p{page["pdf_page"]}_c{chunk_number}'
                    ),
                    "text": text,
                    "word_count": len(text.split()),
                    "direct_topic_match": bool(TOPIC_PATTERN.search(text)),
                }
            )

    raw_df = pd.DataFrame(raw_chunks)
    if raw_df.empty:
        raise ValueError("No chunks were created from the selected pages.")

    keep_indices: set[int] = set()
    group_keys = ["firm_short", "inspection_year", "pdf_page"]
    for _, page_group in raw_df.groupby(group_keys):
        ordered = list(page_group.sort_values("chunk_number").index)
        for position, row_index in enumerate(ordered):
            if not raw_df.loc[row_index, "direct_topic_match"]:
                continue
            keep_indices.add(row_index)
            if position > 0:
                keep_indices.add(ordered[position - 1])
            if position + 1 < len(ordered):
                keep_indices.add(ordered[position + 1])

    chunks = raw_df.loc[sorted(keep_indices)].reset_index(drop=True).copy()
    chunks["citation"] = chunks.apply(
        lambda row: (
            f'[{row["firm_short"]}, {row["inspection_year"]} inspection, '
            f'PDF p. {row["pdf_page"]}]'
        ),
        axis=1,
    )
    return chunks


def build_corpus(
    manifest_path: str | Path,
    raw_pdf_dir: str | Path,
) -> pd.DataFrame:
    """Download all scoped reports and build the revenue-focused corpus."""

    selected_pages: list[dict] = []
    for spec in load_report_manifest(manifest_path):
        pdf_path = download_report(spec, raw_pdf_dir)
        selected_pages.extend(select_part_ia_pages(extract_pages(spec, pdf_path)))
    return build_revenue_chunks(selected_pages)

