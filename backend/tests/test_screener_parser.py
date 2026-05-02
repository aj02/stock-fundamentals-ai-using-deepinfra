"""Test the Screener HTML parser against synthetic page fragments.

Network is mocked — we feed canned HTML matching the structure observed on
real Screener company pages (h1 company name, div.pros/li, div.cons/li,
anchors with class containing 'plausible-event-name=Annual+Report').
"""

from __future__ import annotations

from app.data.screener_scraper import _parse_company_page


SYNTH_HTML = """\
<!doctype html>
<html><body>
  <h1>Reliance Industries Ltd</h1>

  <div class="pros">
    <p>Pros</p>
    <ul><li>Healthy free cash generation in last 2 years.</li></ul>
  </div>
  <div class="cons">
    <p>Cons</p>
    <ul>
      <li>Company has a low return on equity of 8.91% over last 3 years.</li>
      <li>Dividend payout has been low at 10.2% of profits over last 3 years</li>
    </ul>
  </div>

  <h3>Annual reports</h3>
  <ul>
    <li><a class="plausible-event-name=Annual+Report plausible-event-user=unregistered"
       href="https://www.bseindia.com/xml-data/corpfiling/AttachHis/abc.pdf">Financial Year 2025from bse</a></li>
    <li><a class="plausible-event-name=Annual+Report"
       href="https://www.bseindia.com/xml-data/corpfiling/AttachHis/def.pdf">Financial Year 2024from bse</a></li>
    <li><a class="plausible-event-name=Annual+Report"
       href="https://www.bseindia.com/xml-data/corpfiling/AttachHis/ghi.pdf">Financial Year 2023from bse</a></li>
    <li><a class="plausible-event-name=Annual+Report"
       href="https://archives.nseindia.com/annual_reports/AR_19_RELIANCE_2012_2013.zip">Financial Year 2013from nse</a></li>
  </ul>
</body></html>
"""


def test_parser_extracts_company_name_and_bullets() -> None:
    snap = _parse_company_page(SYNTH_HTML, "RELIANCE", "https://example/test")
    assert snap.company_name == "Reliance Industries Ltd"
    assert "Healthy free cash generation in last 2 years." in snap.pros
    assert "Company has a low return on equity of 8.91% over last 3 years." in snap.cons
    assert len(snap.cons) == 2


def test_parser_extracts_annual_reports_newest_first_and_drops_zip() -> None:
    snap = _parse_company_page(SYNTH_HTML, "RELIANCE", "https://example/test")

    # ZIP (FY2013 NSE) should be dropped — we only keep PDFs.
    assert all(ar.url.endswith(".pdf") for ar in snap.annual_reports)
    assert len(snap.annual_reports) == 3

    # Sorted newest-first.
    assert [ar.fiscal_year for ar in snap.annual_reports] == [2025, 2024, 2023]
    assert snap.annual_reports[0].url == (
        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/abc.pdf"
    )
    assert snap.annual_reports[0].source == "bse"


def test_parser_marks_available_true_on_clean_input() -> None:
    snap = _parse_company_page(SYNTH_HTML, "RELIANCE", "https://example/test")
    assert snap.available is True
    assert snap.note is None
