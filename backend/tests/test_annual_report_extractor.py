"""Tests for AR section extraction (heading regex + offset slicing).

Synthetic full-text fixtures stand in for parsed PDFs — we exercise the
regex matches + section-boundary logic without round-tripping through pypdf.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.data.annual_report import _extract_sections


def _write_synthetic_pdf(tmp_path: Path) -> Path:
    """Build a minimal PDF whose extracted text contains our headings.

    We rely on a tiny inline PDF so pypdf has something to read; the test
    feeds a real (small) PDF through the actual extraction pipeline.
    """
    # The simplest portable approach: ship a hand-crafted PDF as a binary
    # constant. But we'd rather use reportlab... which we don't install.
    # Instead we test _extract_sections via the fpdf-free path: bypass it.
    raise NotImplementedError  # placeholder — see direct-path tests below


def test_extract_sections_directly_with_full_text(monkeypatch, tmp_path: Path) -> None:
    """We bypass real PDF reading by monkeypatching pypdf's PdfReader."""
    full_text_pages = [
        "Cover\n\nReliance Industries Limited\nIntegrated Annual Report 2024-25\n",
        "TABLE OF CONTENTS\nManagement Discussion and Analysis ........... 50\n",
        "MANAGEMENT DISCUSSION AND ANALYSIS\n\n"
        "FY25 was a year of consolidation. Retail crossed 18,000 stores. "
        "Digital services revenue grew 18% YoY. Gross refining margins normalised "
        "from elevated FY23 levels. Capex was rationalised to ₹1.23 lakh crore. "
        "We reiterate our medium-term goal of doubling Reliance Retail's revenue "
        "by FY28 from FY24 levels and growing digital services subscribers past "
        "550 million by FY27.\n",
        "CORPORATE GOVERNANCE REPORT\n\n"
        "The Board comprises 14 directors of whom 9 are Independent Non-Executive "
        "Directors. The Audit Committee, chaired by Mr. K.V. Chowdary, met four "
        "times during FY25. Related-party transactions amounting to ₹2,432 crore "
        "were approved, all on arm's-length basis. Total managerial remuneration "
        "as a percentage of net profit stood at 0.027%.\n",
        "RISK MANAGEMENT FRAMEWORK\n\n"
        "Principal risks identified: commodity price volatility (refining margins), "
        "regulatory shifts in telecommunications spectrum, supply-chain disruptions "
        "in retail, and currency translation risk on USD-denominated debt.\n",
    ]

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [FakePage(t) for t in full_text_pages]

    # Patch where _extract_sections imports from.
    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", FakePdfReader)

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

    page_count, sections = _extract_sections(pdf_path, ["mda", "governance", "risks"])

    assert page_count == 5
    assert "mda" in sections
    assert "governance" in sections
    assert "risks" in sections

    mda = sections["mda"]
    assert "MANAGEMENT DISCUSSION AND ANALYSIS" in mda.heading_found.upper()
    assert "Retail crossed 18,000 stores" in mda.text
    # MD&A must NOT bleed into governance.
    assert "Audit Committee" not in mda.text

    gov = sections["governance"]
    assert "Audit Committee" in gov.text
    # Governance must NOT bleed into risks.
    assert "Principal risks identified" not in gov.text

    risks = sections["risks"]
    assert "Principal risks identified" in risks.text


def test_no_match_returns_empty_dict(monkeypatch, tmp_path: Path) -> None:
    """If headings aren't present, the extractor returns an empty section map."""
    full_text_pages = [
        "Cover\n\nSome Company Limited\n\n",
        "We have nothing of interest in this PDF.\n\n"
        "No headings to find here.\n",
    ]

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [FakePage(t) for t in full_text_pages]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", FakePdfReader)

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

    page_count, sections = _extract_sections(pdf_path, ["mda", "governance"])
    assert page_count == 2
    assert sections == {}


def test_truncation_kicks_in_on_long_section(monkeypatch, tmp_path: Path) -> None:
    """A 6000-word MD&A should be truncated to 5000 words."""
    long_body = " ".join(["alpha"] * 6500)
    full_text_pages = [
        f"MANAGEMENT DISCUSSION AND ANALYSIS\n\n{long_body}\n",
        "CORPORATE GOVERNANCE REPORT\n\nshort\n",
    ]

    class FakePage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class FakePdfReader:
        def __init__(self, _path: str) -> None:
            self.pages = [FakePage(t) for t in full_text_pages]

    import pypdf

    monkeypatch.setattr(pypdf, "PdfReader", FakePdfReader)

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    _, sections = _extract_sections(pdf_path, ["mda", "governance"])
    mda = sections["mda"]
    assert mda.truncated is True
    assert mda.word_count == pytest.approx(5000, abs=2)
    assert mda.text.endswith("[…truncated]")
