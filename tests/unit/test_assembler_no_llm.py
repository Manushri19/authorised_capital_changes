"""
test_assembler_no_llm.py
=========================
Comprehensive test suite for Node 7 — Assembler.
No LLM calls are made. Tests Indian number formatting,
pre-change breakdown computation, capital narrative formatting,
and the integration test that builds rows 0 to N.
"""

import sys, os
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from decimal import Decimal

from authorised_capital_changes.pipeline.nodes.assembler import (
    format_capital_narrative,
    compute_prechange_breakdown,
    run_assembler,
)
from authorised_capital_changes.services.document_parser import format_inr
from authorised_capital_changes.schemas.attachment import EGMResolutionExtraction
from authorised_capital_changes.schemas.capital_event import CapitalTableRow
from authorised_capital_changes.schemas.document import ClassifiedDocument, DocumentGroup, FileMetadata, DocumentType, OfficialStatus
from authorised_capital_changes.schemas.pipeline_state import AttachmentExtractionBundle, PipelineState
from authorised_capital_changes.schemas.sh7 import AuthorisedCapitalBlock, ShareBreakdown, SH7Extraction
from authorised_capital_changes.schemas.validation import CrossDocumentCheckResult, ValidationReport


def test_format_inr():
    assert format_inr(Decimal("150000")) == "₹1,50,000"
    assert format_inr(Decimal("5000000")) == "₹50,00,000"
    assert format_inr(Decimal("20000000")) == "₹2,00,00,000"
    assert format_inr(Decimal("1000")) == "₹1,000"
    assert format_inr(Decimal("10")) == "₹10"
    # with decimal component (though not common in share counts, testing robustly)
    assert format_inr(Decimal("1500000.50")) == "₹15,00,000.50"
    print("PASS  test_format_inr")


def test_format_capital_narrative():
    # Case 1: Equity only
    narrative1 = format_capital_narrative(
        total_amount=Decimal("150000"),
        equity_count=15000,
        equity_nominal=Decimal("10")
    )
    assert narrative1 == "₹1,50,000 divided into 15,000 Equity Shares of ₹10 each"

    # Case 2: Equity + Preference
    narrative2 = format_capital_narrative(
        total_amount=Decimal("20000000"),
        equity_count=1800000,
        equity_nominal=Decimal("10"),
        preference_count=200000,
        preference_nominal=Decimal("10")
    )
    assert narrative2 == "₹2,00,00,000 divided into 18,00,000 Equity Shares of ₹10 each and 2,00,000 Preference Shares of ₹10 each"

    # Case 3: Breakdown unavailable
    narrative3 = format_capital_narrative(
        total_amount=Decimal("5000000"),
        equity_count=None,
        equity_nominal=Decimal("10")
    )
    assert narrative3 == "₹50,00,000 (share breakdown not determinable — see footnote)"
    print("PASS  test_format_capital_narrative")


def test_compute_prechange_breakdown():
    # 1. Happy path: total=300000, nominal=10 -> count=30000
    cnt, note = compute_prechange_breakdown(
        existing_total=Decimal("300000"),
        nominal_per_share=Decimal("10"),
        post_change_preference_count=None,
        source_sh7_filename="SH7_Event1.md"
    )
    assert cnt == 30000
    assert "arithmetically" in note

    # 2. Multi-class guard
    cnt2, note2 = compute_prechange_breakdown(
        existing_total=Decimal("300000"),
        nominal_per_share=Decimal("10"),
        post_change_preference_count=500,  # Preference exists post-change
        source_sh7_filename="SH7_Event1.md"
    )
    assert cnt2 is None
    assert "preference shares present" in note2

    # 3. Nominal is 0
    cnt3, note3 = compute_prechange_breakdown(
        existing_total=Decimal("300000"),
        nominal_per_share=Decimal("0"),
        post_change_preference_count=None,
        source_sh7_filename="SH7_Event1.md"
    )
    assert cnt3 is None
    assert "nominal value per share is zero" in note3

    # 4. Indivisible
    cnt4, note4 = compute_prechange_breakdown(
        existing_total=Decimal("100"),
        nominal_per_share=Decimal("3"),
        post_change_preference_count=None,
        source_sh7_filename="SH7_Event1.md"
    )
    assert cnt4 is None
    assert "not exactly divisible" in note4

    print("PASS  test_compute_prechange_breakdown")


# ============================================================
# Integration Test
# ============================================================

def _make_sh7(srn: str, existing: str, revised: str, meeting_date: date) -> SH7Extraction:
    return SH7Extraction(
        cin="U12345DL2018PTC123456",
        company_name="NEXUS INC",
        registered_address="DELHI",
        email="nexus@example.com",
        purpose="Increase",
        meeting_date=meeting_date,
        resolution_type="Ordinary",
        existing_authorised_capital=Decimal(existing),
        revised_authorised_capital=Decimal(revised),
        authorised_capital=AuthorisedCapitalBlock(
            total_amount=Decimal(revised),
            breakdown=ShareBreakdown(
                equity_shares_count=int(Decimal(revised) / 10),
                equity_nominal_per_share=Decimal("10"),
                equity_total_amount=Decimal(revised),
                preference_shares_count=None,
                preference_nominal_per_share=None,
                preference_total_amount=None,
                unclassified_shares_count=None,
                unclassified_total_amount=None,
            )
        ),
        srn=srn,
        filing_date=meeting_date,
        stamp_duty_state="Delhi",
        stamp_duty_amount=Decimal("100"),
        attachment_filenames_raw=[],
        extraction_confidence=0.9,
        unconfirmed_fields=[],
        extraction_errors=[],
    )

def _make_egm(source: str, meeting_type: str) -> EGMResolutionExtraction:
    return EGMResolutionExtraction(
        source_filename=source,
        cin="U123",
        meeting_date=date(2019,1,1),
        meeting_type=meeting_type,
        resolved_capital_amount=Decimal("1000"),
        extraction_confidence=0.9,
        unconfirmed_fields=[],
        extraction_errors=[]
    )

def test_run_assembler():
    sh7_e1 = _make_sh7("H001", "300000", "5000000", date(2018, 12, 10))
    sh7_e2 = _make_sh7("H002", "5000000", "20000000", date(2019, 5, 15))
    
    # EGM provides meeting type
    bundle_e2 = AttachmentExtractionBundle(
        event_index=2,
        sh7_filename="H002",
        board_resolution=None,
        egm_resolution=_make_egm("EGM_2.md", "EGM"),
        moa=None
    )

    # Cross-document check failure for E2
    cross_res = CrossDocumentCheckResult(
        event_index=2,
        sh7_filename="H002",
        check_type="DATE",
        sh7_value="2019-05-15",
        conflicting_document="EGM_2.md",
        conflicting_value="2019-05-16",
        agreeing_documents=[],
        passed=False,
        flag_code="FLAG_001"
    )

    val_e1 = ValidationReport(
        sh7_filename="H001",
        arithmetic_checks=[], continuity_checks=[], cross_document_checks=[], duplicate_checks=[],
        validation_passed=True, blocking_errors=[], non_blocking_flags=[]
    )
    val_e2 = ValidationReport(
        sh7_filename="H002",
        arithmetic_checks=[], continuity_checks=[], cross_document_checks=[cross_res], duplicate_checks=[],
        validation_passed=True, blocking_errors=[], 
        non_blocking_flags=["FLAG_001 | DATE mismatch on H002"]
    )

    # Empty document groups for filename mappings
    state = PipelineState(
        run_id="test",
        input_folder="/tmp",
        started_at="now",
        raw_files=[], classified_docs=[], sh7_documents=[], non_sh7_documents=[],
        unclassified_documents=[], document_groups=[], unmatched_attachment_refs={},
        attachment_bundles=[bundle_e2],
        extracted_sh7s=[sh7_e1, sh7_e2],
        sh7_extraction_errors=[],
        validation_reports=[val_e1, val_e2],
        sh7s_blocked_by_validation=[],  # all passed
        sh7s_passed_validation=["H001", "H002"],
        capital_table_rows=[],
        final_table_rows=[],
        discrepancy_report=None,
        human_review_queue=[], human_review_resolved=[], human_review_required=False,
        pipeline_errors=[], completed_stages=[]
    )

    result = run_assembler(state)
    rows = result["capital_table_rows"]
    
    assert len(rows) == 3  # Row 0, Row 1, Row 2

    # Verify Row 0
    assert rows[0].row_number == 0
    assert rows[0].meeting_date.value == "On incorporation"
    assert rows[0].authorised_from.value is None
    assert rows[0].authorised_to.value == "₹3,00,000 divided into 30,000 Equity Shares of ₹10 each"
    assert rows[0].meeting_type.value is None

    # Verify Row 1
    assert rows[1].row_number == 1
    assert rows[1].meeting_date.value == "2018-12-10"
    assert rows[1].authorised_from.value == rows[0].authorised_to.value  # MUST MATCH EXACTLY
    assert rows[1].authorised_to.value == "₹50,00,000 divided into 5,00,000 Equity Shares of ₹10 each"
    assert rows[1].meeting_type.value is None
    assert rows[1].meeting_type.flag_code == "FLAG_MEETING_TYPE_UNCONFIRMED"

    # Verify Row 2
    assert rows[2].row_number == 2
    assert rows[2].authorised_from.value == rows[1].authorised_to.value
    assert rows[2].authorised_to.value == "₹2,00,00,000 divided into 20,00,000 Equity Shares of ₹10 each"
    assert rows[2].meeting_type.value == "EGM"  # Extracted from EGM bundle
    assert rows[2].meeting_date.flag_code == "FLAG_001"  # Derived from cross-doc check

    print("PASS  test_run_assembler")


if __name__ == "__main__":
    test_format_inr()
    test_format_capital_narrative()
    test_compute_prechange_breakdown()
    test_run_assembler()
    print("\nAll Assembler tests PASSED.")
