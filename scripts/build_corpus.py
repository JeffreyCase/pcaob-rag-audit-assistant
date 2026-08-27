"""Download the scoped public reports and build the local chunk corpus."""

from pathlib import Path

from pcaob_rag.pipeline import build_and_save_corpus

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    chunks = build_and_save_corpus(
        manifest_path=ROOT / "config" / "reports.json",
        raw_pdf_dir=ROOT / "data" / "raw_pdfs",
        output_path=ROOT / "data" / "processed" / "pcaob_revenue_chunks.csv",
    )
    print(
        f"Built {len(chunks)} chunks across "
        f"{chunks['pdf_page'].nunique()} report pages."
    )

