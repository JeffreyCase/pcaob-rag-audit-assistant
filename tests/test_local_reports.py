import json
import socket
import urllib.request
from dataclasses import asdict

import fitz
import pytest

from pcaob_rag.documents import (
    PART_IA_HEADING,
    PART_IB_HEADING,
    ReportSpec,
    build_corpus,
    require_local_report,
)


@pytest.fixture(autouse=True)
def block_report_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Local report processing must not access the network")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def report_spec(firm="EY"):
    return ReportSpec(
        firm=firm,
        firm_short=firm,
        inspection_year=2024,
        filename=f"{firm.lower()}_2024.pdf",
        source_url=f"https://assets.pcaobus.org/{firm.lower()}_2024.pdf",
    )


def write_manifest(path, reports):
    path.write_text(json.dumps([asdict(spec) for spec in reports]), encoding="utf-8")


def write_synthetic_report(path):
    with fitz.open() as document:
        for number in range(1, 13):
            page = document.new_page()
            if number == 11:
                text = PART_IA_HEADING + "\n" + (
                    "Revenue controls did not address completeness of contracts. " * 15
                )
            elif number == 12:
                text = PART_IB_HEADING
            else:
                text = f"Synthetic report page {number}"
            assert page.insert_textbox(fitz.Rect(40, 40, 550, 780), text) >= 0
        document.save(path)


def test_missing_report_gives_manual_setup_without_downloading(tmp_path):
    spec = report_spec()
    manifest = tmp_path / "reports.json"
    write_manifest(manifest, [spec])
    raw_dir = tmp_path / "raw_pdfs"

    with pytest.raises(FileNotFoundError) as error:
        build_corpus(manifest, raw_dir)

    assert spec.filename in str(error.value)
    assert spec.source_url in str(error.value)
    assert "manually" in str(error.value)
    assert not raw_dir.exists()


@pytest.mark.parametrize("content", [b"", b"This is an HTML error, not a PDF."])
def test_invalid_report_is_preserved_and_never_replaced(tmp_path, content):
    spec = report_spec()
    path = tmp_path / spec.filename
    path.write_bytes(content)

    with pytest.raises(ValueError, match="readable, non-empty PDF"):
        require_local_report(spec, tmp_path)

    assert path.read_bytes() == content
    assert list(tmp_path.iterdir()) == [path]


def test_local_corpus_preserves_files_and_report_page_citations(tmp_path):
    reports = [report_spec("EY"), report_spec("Deloitte")]
    manifest = tmp_path / "reports.json"
    write_manifest(manifest, reports)
    before = {}
    for spec in reports:
        path = tmp_path / spec.filename
        write_synthetic_report(path)
        before[path] = path.read_bytes()

    chunks = build_corpus(manifest, tmp_path)

    assert set(chunks["firm_short"]) == {"EY", "Deloitte"}
    assert set(chunks["pdf_page"]) == {11}
    assert set(chunks["source_url"]) == {spec.source_url for spec in reports}
    assert set(chunks["citation"]) == {
        f"[{spec.firm_short}, 2024 inspection, PDF p. 11]" for spec in reports
    }
    assert chunks["text"].str.contains("completeness of contracts").all()
    for path, content in before.items():
        assert path.read_bytes() == content
