"""
test_validator_no_llm.py
=========================
Full test-suite for Node 6 — Validator.
No LLM calls are made.  All data is hand-crafted to match the real SH-7
documents in authorised_capital_changes/data/raw/.

Tests:
  1. _extract_field6_total_addition — HTML and plain-text formats
  2. Arithmetic check — pass / fail paths
  3. Continuity check — pass / fail / MOA corroboration
  4. Cross-document check — date and capital, non-blocking and blocking paths
  5. Duplicate SH-7 detection → blocking
  6. run_validator() integration — happy path (4 events, all pass)
  7. run_validator() integration — Event 3 continuity gap (blocking)
  8. run_validator() integration — Event 2 cross-doc date conflict (blocking)
  9. run_validator() integration — duplicate meeting_date → both blocked
"""

import sys, os
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from decimal import Decimal

from authorised_capital_changes.pipeline.nodes.validator import (
    _extract_field6_total_addition,
    _run_arithmetic_check,
    _run_continuity_checks,
    _run_cross_document_checks,
    _run_duplicate_check,
    run_validator,
)
from authorised_capital_changes.schemas.attachment import (
    BoardResolutionExtraction,
    EGMResolutionExtraction,
    MOAExtraction,
)
from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus,
)
from authorised_capital_changes.schemas.pipeline_state import (
    AttachmentExtractionBundle, PipelineState,
)
from authorised_capital_changes.schemas.sh7 import (
    AuthorisedCapitalBlock, ShareBreakdown, SH7Extraction,
)
from authorised_capital_changes.schemas.validation import ValidationReport

# ============================================================
# Fixtures
# ============================================================

def _make_sh7(
    srn: str,
    existing: str,
    revised: str,
    meeting_date: date,
    total_9a: str | None = None,
) -> SH7Extraction:
    """Build a minimal SH7Extraction; 9(a) total defaults to revised."""
    total = Decimal(total_9a or revised)
    return SH7Extraction(
        cin="U85123DL2018PTC312456",
        company_name="NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED",
        registered_address="KRISHNA TOWER DWARKA NEW DELHI",
        email="arunsethi@outlook.com",
        purpose="Increase in share capital independently by company",
        meeting_date=meeting_date,
        resolution_type="Ordinary",
        existing_authorised_capital=Decimal(existing),
        revised_authorised_capital=Decimal(revised),
        authorised_capital=AuthorisedCapitalBlock(
            total_amount=total,
            breakdown=ShareBreakdown(
                equity_shares_count=None,
                equity_nominal_per_share=None,
                equity_total_amount=None,
                preference_shares_count=None,
                preference_nominal_per_share=None,
                preference_total_amount=None,
                unclassified_shares_count=None,
                unclassified_total_amount=None,
            ),
        ),
        srn=srn,
        filing_date=meeting_date,
        stamp_duty_state="Delhi",
        stamp_duty_amount=Decimal("4700"),
        attachment_filenames_raw=[],
        extraction_confidence=0.95,
        unconfirmed_fields=[],
        extraction_errors=[],
    )


def _make_board(
    source: str,
    meeting_date: date | None,
    capital: str | None,
) -> BoardResolutionExtraction:
    return BoardResolutionExtraction(
        source_filename=source,
        cin="U85123DL2018PTC312456",
        meeting_date=meeting_date,
        resolved_capital_amount=Decimal(capital) if capital else None,
        resolution_type="Ordinary",
        extraction_confidence=0.9,
        unconfirmed_fields=[],
        extraction_errors=[],
    )


def _make_egm(
    source: str,
    meeting_date: date | None,
    capital: str | None,
    meeting_type: str = "EGM",
) -> EGMResolutionExtraction:
    return EGMResolutionExtraction(
        source_filename=source,
        cin="U85123DL2018PTC312456",
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        resolved_capital_amount=Decimal(capital) if capital else None,
        extraction_confidence=0.9,
        unconfirmed_fields=[],
        extraction_errors=[],
    )


def _make_moa(incorporation_capital: str | None) -> MOAExtraction:
    return MOAExtraction(
        source_filename="MOA_2018.pdf",
        cin="U85123DL2018PTC312456",
        incorporation_capital=Decimal(incorporation_capital) if incorporation_capital else None,
        equity_shares_count=30000,
        nominal_per_share=Decimal("10"),
        preference_shares_count=None,
        preference_nominal_per_share=None,
        extraction_confidence=0.95,
        unconfirmed_fields=[],
        extraction_errors=[],
    )


def _make_bundle(
    sh7_srn: str,
    event_index: int,
    board: BoardResolutionExtraction | None = None,
    egm: EGMResolutionExtraction | None = None,
    moa: MOAExtraction | None = None,
) -> AttachmentExtractionBundle:
    return AttachmentExtractionBundle(
        event_index=event_index,
        sh7_filename=sh7_srn,
        board_resolution=board,
        egm_resolution=egm,
        moa=moa,
    )


def _make_classified_doc(filename: str, raw_content: str) -> ClassifiedDocument:
    return ClassifiedDocument(
        file_metadata=FileMetadata(
            filename=filename,
            filepath=f"/tmp/{filename}",
            raw_content=raw_content,
            file_size_bytes=len(raw_content),
        ),
        document_type=DocumentType.SH7,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=0.95,
        event_date_hint=None,
        cin_hint=None,
        requires_human_review=False,
        review_reason=None,
    )


def _make_group(sh7_filename: str, raw_content: str) -> DocumentGroup:
    return DocumentGroup(
        event_index=1,
        sh7=_make_classified_doc(sh7_filename, raw_content),
        board_resolution=None,
        egm_resolution=None,
        moa=None,
        unmatched_attachment_refs=[],
    )


# Raw content for Field-6 extraction tests
_FIELD6_HTML = """\
6. The additional capital is divided as follows
<table>
  <tr><td>Number of equity shares</td><td>13,00,000</td></tr>
  <tr><td>Total addition</td><td>(in Rs.)</td><td>1,50,00,000.00</td></tr>
</table>
"""

_FIELD6_PLAIN = """\
6. Field 6 breakdown
Total addition | (in Rs.) | 47,00,000.00
"""

_FIELD6_MISSING = """\
9. Revised capital structure after changes.
(a) Authorised capital of the company (in Rs.) 5000000.00
"""

# ============================================================
# 1. Test _extract_field6_total_addition
# ============================================================

def test_field6_extraction():
    # HTML table cell format
    result = _extract_field6_total_addition(_FIELD6_HTML)
    assert result == Decimal("15000000.00"), f"Expected 15000000.00 got {result}"

    # Plain text / markdown format
    result2 = _extract_field6_total_addition(_FIELD6_PLAIN)
    assert result2 == Decimal("4700000.00"), f"Expected 4700000.00 got {result2}"

    # Absent — should return None
    result3 = _extract_field6_total_addition(_FIELD6_MISSING)
    assert result3 is None, f"Expected None got {result3}"

    print("PASS  test_field6_extraction")


# ============================================================
# 2. Arithmetic check
# ============================================================

def test_arithmetic_check_pass():
    sh7 = _make_sh7("H001", "300000", "5000000", date(2019, 5, 15))
    flags, non_blocking = [], []
    result, counter = _run_arithmetic_check(
        sh7=sh7,
        raw_content=_FIELD6_PLAIN,    # addition = 4700000
        flag_counter=1,
        report_flags=flags,
        report_non_blocking=non_blocking,
    )
    # 300000 + 4700000 = 5000000 ✓
    assert result.passed, f"Expected pass: {result}"
    assert counter == 1          # no flag consumed
    assert flags == []
    print("PASS  test_arithmetic_check_pass")


def test_arithmetic_check_fail():
    # existing=300000, revised=6000000, but addition=4700000 → mismatch
    sh7 = _make_sh7("H002", "300000", "6000000", date(2019, 5, 15))
    flags, non_blocking = [], []
    result, counter = _run_arithmetic_check(
        sh7=sh7,
        raw_content=_FIELD6_PLAIN,   # addition = 4700000
        flag_counter=1,
        report_flags=flags,
        report_non_blocking=non_blocking,
    )
    assert not result.passed
    assert result.discrepancy_amount == Decimal("1000000")
    assert counter == 2          # one flag consumed
    assert len(flags) == 1
    assert "FLAG_001" in flags[0]
    print("PASS  test_arithmetic_check_fail  discrepancy=%s", result.discrepancy_amount)


def test_arithmetic_check_missing_field6():
    sh7 = _make_sh7("H003", "300000", "5000000", date(2019, 5, 15))
    flags, non_blocking = [], []
    result, counter = _run_arithmetic_check(
        sh7=sh7,
        raw_content=_FIELD6_MISSING,
        flag_counter=1,
        report_flags=flags,
        report_non_blocking=non_blocking,
    )
    # Indeterminate — should NOT flag
    assert result.passed is True   # indeterminate treated as pass
    assert counter == 1
    assert flags == []
    print("PASS  test_arithmetic_check_missing_field6")


# ============================================================
# 3. Continuity check
# ============================================================

def test_continuity_pass():
    sh7s = [
        _make_sh7("H001", "300000",  "5000000",   date(2018, 12, 10)),
        _make_sh7("H002", "5000000", "20000000",  date(2019, 5, 15)),
        _make_sh7("H003", "20000000","50000000",  date(2021, 9, 10)),
    ]
    blocked, corroborations = set(), []
    results = _run_continuity_checks(
        sorted_sh7s=sh7s,
        moa_bundle=None,
        blocking_errors={},
        blocked_set=blocked,
        discrepancy_corroborations=corroborations,
    )
    assert blocked == set()
    assert all(r.passed for r in results)
    assert len(results) == 2      # events 2 and 3
    print("PASS  test_continuity_pass")


def test_continuity_fail():
    sh7s = [
        _make_sh7("H001", "300000",  "5000000",   date(2018, 12, 10)),
        _make_sh7("H002", "9999999", "20000000",  date(2019, 5, 15)),  # gap!
    ]
    blocked, block_errs, corroborations = set(), {}, []
    results = _run_continuity_checks(
        sorted_sh7s=sh7s,
        moa_bundle=None,
        blocking_errors=block_errs,
        blocked_set=blocked,
        discrepancy_corroborations=corroborations,
    )
    assert "H002" in blocked
    assert not results[0].passed
    assert results[0].expected_from == Decimal("5000000")
    assert results[0].actual_from == Decimal("9999999")
    print("PASS  test_continuity_fail")


def test_moa_corroboration_agreed():
    sh7s = [_make_sh7("H001", "300000", "5000000", date(2018, 12, 10))]
    moa_bundle = _make_bundle(
        sh7_srn="H001",
        event_index=1,
        moa=_make_moa("300000"),   # matches existing capital of Event 1
    )
    corroborations = []
    _run_continuity_checks(
        sorted_sh7s=sh7s,
        moa_bundle=moa_bundle,
        blocking_errors={},
        blocked_set=set(),
        discrepancy_corroborations=corroborations,
    )
    assert len(corroborations) == 1
    assert corroborations[0]["result"] == "AGREED"
    assert "note" not in corroborations[0]   # no note on AGREED
    print("PASS  test_moa_corroboration_agreed")


def test_moa_corroboration_disagreed():
    sh7s = [_make_sh7("H001", "300000", "5000000", date(2018, 12, 10))]
    moa_bundle = _make_bundle(
        sh7_srn="H001",
        event_index=1,
        moa=_make_moa("100000"),   # does NOT match
    )
    corroborations = []
    blocked = set()
    _run_continuity_checks(
        sorted_sh7s=sh7s,
        moa_bundle=moa_bundle,
        blocking_errors={},
        blocked_set=blocked,
        discrepancy_corroborations=corroborations,
    )
    assert corroborations[0]["result"] == "DISAGREED"
    assert "Non-blocking" in corroborations[0]["note"]
    assert blocked == set()    # non-blocking — SH-7 not blocked
    print("PASS  test_moa_corroboration_disagreed")


# ============================================================
# 4. Cross-document check
# ============================================================

def test_cross_doc_all_agree():
    sh7 = _make_sh7("H002", "300000", "5000000", date(2019, 5, 15))
    bundle = _make_bundle(
        sh7_srn="H002",
        event_index=2,
        board=_make_board("BoardMeeting_2019.md", date(2019, 5, 15), "5000000"),
        egm=_make_egm("EGM_2019.md", date(2019, 5, 15), "5000000"),
    )
    flags, non_blocking, blocking = [], [], []
    blocked, cross = set(), []
    _run_cross_document_checks(
        sh7=sh7, bundle=bundle, flag_counter=1,
        report_flags=flags, report_non_blocking=non_blocking,
        report_blocking=blocking, blocked_set=blocked,
        cross_results=cross, event_index=2,
    )
    assert blocked == set()
    assert cross == []
    print("PASS  test_cross_doc_all_agree")


def test_cross_doc_one_conflict_nonblocking():
    sh7 = _make_sh7("H002", "300000", "5000000", date(2019, 5, 15))
    bundle = _make_bundle(
        sh7_srn="H002",
        event_index=2,
        board=_make_board("BoardMeeting_2019.md", date(2019, 5, 15), "5000000"),  # agrees
        egm=_make_egm("EGM_2019.md", date(2019, 5, 16), "5000000"),               # date disagrees
    )
    flags, non_blocking, blocking = [], [], []
    blocked, cross = set(), []
    _run_cross_document_checks(
        sh7=sh7, bundle=bundle, flag_counter=1,
        report_flags=flags, report_non_blocking=non_blocking,
        report_blocking=blocking, blocked_set=blocked,
        cross_results=cross, event_index=2,
    )
    assert "H002" not in blocked          # non-blocking — not blocked
    assert len(cross) == 1
    assert cross[0].check_type == "DATE"
    assert "BoardMeeting_2019.md" in cross[0].agreeing_documents
    assert len(non_blocking) == 1
    assert "FLAG_001" in non_blocking[0]
    print("PASS  test_cross_doc_one_conflict_nonblocking")


def test_cross_doc_all_conflict_blocking():
    sh7 = _make_sh7("H002", "300000", "5000000", date(2019, 5, 15))
    bundle = _make_bundle(
        sh7_srn="H002",
        event_index=2,
        board=_make_board("BoardMeeting_2019.md", date(2019, 5, 20), "5000000"),  # date differs
        egm=_make_egm("EGM_2019.md", date(2019, 5, 21), "5000000"),               # date differs
    )
    flags, non_blocking, blocking = [], [], []
    blocked, cross = set(), []
    _run_cross_document_checks(
        sh7=sh7, bundle=bundle, flag_counter=1,
        report_flags=flags, report_non_blocking=non_blocking,
        report_blocking=blocking, blocked_set=blocked,
        cross_results=cross, event_index=2,
    )
    assert "H002" in blocked
    assert len(blocking) >= 1
    assert all(not r.passed for r in cross)
    print("PASS  test_cross_doc_all_conflict_blocking")


def test_cross_doc_meeting_type_not_compared():
    """
    A file named EGM_EventN whose body says meeting_type='AGM' must NOT raise a flag.
    ClassifiedDocument.document_type vs EGMResolutionExtraction.meeting_type are never compared.
    """
    sh7 = _make_sh7("H002", "300000", "5000000", date(2019, 5, 15))
    # meeting_type = "AGM" even though filename says EGM — this is valid per spec
    bundle = _make_bundle(
        sh7_srn="H002",
        event_index=2,
        egm=_make_egm("EGM_Event2_2019.md", date(2019, 5, 15), "5000000", meeting_type="AGM"),
    )
    flags, non_blocking, blocking = [], [], []
    blocked, cross = set(), []
    _run_cross_document_checks(
        sh7=sh7, bundle=bundle, flag_counter=1,
        report_flags=flags, report_non_blocking=non_blocking,
        report_blocking=blocking, blocked_set=blocked,
        cross_results=cross, event_index=2,
    )
    assert blocked == set()
    assert cross == []            # no meeting_type comparison flag
    print("PASS  test_cross_doc_meeting_type_not_compared")


# ============================================================
# 5. Duplicate check
# ============================================================

def test_duplicate_check_no_duplicates():
    sh7s = [
        _make_sh7("H001", "300000",  "5000000",  date(2018, 12, 10)),
        _make_sh7("H002", "5000000", "20000000", date(2019, 5, 15)),
    ]
    blocked, hr = set(), set()
    results = _run_duplicate_check(sh7s, blocked, hr)
    assert results == []
    assert blocked == set()
    print("PASS  test_duplicate_check_no_duplicates")


def test_duplicate_check_blocks_both():
    sh7s = [
        _make_sh7("H001", "300000", "5000000", date(2019, 5, 15)),
        _make_sh7("H002", "300000", "5000000", date(2019, 5, 15)),  # same date!
    ]
    blocked, hr = set(), set()
    results = _run_duplicate_check(sh7s, blocked, hr)
    assert len(results) == 1
    assert results[0].routed_to_human_review
    assert "H001" in blocked and "H002" in blocked
    assert "H001" in hr and "H002" in hr
    print("PASS  test_duplicate_check_blocks_both")


# ============================================================
# 6. Integration — happy path (4 events, all pass)
# ============================================================

_RAW = {
    "H12345678": (
        "6. Field 6\nTotal addition | (in Rs.) | 4,70,000.00\n"
    ),
    "H45678902": _FIELD6_PLAIN,         # addition=4700000, existing=300000 → revised=5000000
    "H56789013": (
        "6. Field 6\nTotal addition | (in Rs.) | 1,50,00,000.00\n"
    ),
    "H67890124": (
        "6. Field 6\nTotal addition | (in Rs.) | 1,00,00,000.00\n"
    ),
}

def _integration_state(sh7s, bundles, groups) -> PipelineState:
    return PipelineState(
        run_id="test-run",
        input_folder="/tmp",
        started_at="2026-01-01T00:00:00Z",
        raw_files=[],
        classified_docs=[],
        sh7_documents=[],
        non_sh7_documents=[],
        unclassified_documents=[],
        document_groups=groups,
        unmatched_attachment_refs={},
        attachment_bundles=bundles,
        extracted_sh7s=sh7s,
        sh7_extraction_errors=[],
        validation_reports=[],
        sh7s_blocked_by_validation=[],
        sh7s_passed_validation=[],
        capital_table_rows=[],
        final_table_rows=[],
        discrepancy_report=None,
        human_review_queue=[],
        human_review_resolved=[],
        human_review_required=False,
        pipeline_errors=[],
        completed_stages=[],
    )


def test_integration_happy_path():
    """4 chronological events, all arithmetic and continuity correct, no cross-doc conflicts."""
    sh7_e1 = _make_sh7("H12345678", "300000",   "5000000",   date(2018, 12, 10))
    sh7_e2 = _make_sh7("H45678902", "5000000",  "5000000",   date(2019, 5, 15))   # revised=existing+4700000
    sh7_e3 = _make_sh7("H56789013", "5000000",  "20000000",  date(2021, 9, 10))
    sh7_e4 = _make_sh7("H67890124", "20000000", "30000000",  date(2024, 3, 20))

    # All bundles empty (no attachment extractions) — no cross-doc check needed
    bundles = [
        _make_bundle("H12345678", 1),
        _make_bundle("H45678902", 2),
        _make_bundle("H56789013", 3),
        _make_bundle("H67890124", 4),
    ]
    groups = [
        _make_group("H12345678", _RAW["H12345678"]),
        _make_group("H45678902", _RAW["H45678902"]),
        _make_group("H56789013", _RAW["H56789013"]),
        _make_group("H67890124", _RAW["H67890124"]),
    ]

    state = _integration_state([sh7_e1, sh7_e2, sh7_e3, sh7_e4], bundles, groups)
    result = run_validator(state)

    assert result["sh7s_blocked_by_validation"] == [], result["sh7s_blocked_by_validation"]
    assert len(result["sh7s_passed_validation"]) == 4
    assert "validator" in result["completed_stages"]
    for report in result["validation_reports"]:
        assert report.validation_passed, f"Expected pass for {report.sh7_filename}"
    print("PASS  test_integration_happy_path  passed=%d", len(result["sh7s_passed_validation"]))


# ============================================================
# 7. Integration — continuity gap at Event 3 → blocked
# ============================================================

def test_integration_continuity_blocking():
    sh7_e1 = _make_sh7("H001", "300000",  "5000000",  date(2018, 12, 10))
    sh7_e2 = _make_sh7("H002", "5000000", "20000000", date(2019, 5, 15))
    # Gap! Event 3 existing should be 20000000 but says 99999999
    sh7_e3 = _make_sh7("H003", "99999999","50000000", date(2021, 9, 10))

    bundles = [_make_bundle(srn, i + 1) for i, srn in enumerate(["H001","H002","H003"])]
    groups = [_make_group(srn, "") for srn in ["H001", "H002", "H003"]]

    state = _integration_state([sh7_e1, sh7_e2, sh7_e3], bundles, groups)
    result = run_validator(state)

    assert "H003" in result["sh7s_blocked_by_validation"]
    assert "H003" not in result["sh7s_passed_validation"]
    blocked_report = next(r for r in result["validation_reports"] if r.sh7_filename == "H003")
    assert not blocked_report.validation_passed
    assert len(blocked_report.blocking_errors) >= 1
    print("PASS  test_integration_continuity_blocking  blocked=%s",
          result["sh7s_blocked_by_validation"])


# ============================================================
# 8. Integration — cross-doc all-conflict (blocking)
# ============================================================

def test_integration_cross_doc_all_conflict():
    sh7_e1 = _make_sh7("H001", "300000", "5000000", date(2018, 12, 10))
    # Both board and EGM say meeting_date is totally different
    bundles = [
        _make_bundle(
            "H001", 1,
            board=_make_board("Board.md", date(2025, 1, 1), "5000000"),
            egm=_make_egm("EGM.md",   date(2025, 2, 2), "5000000"),
        )
    ]
    groups = [_make_group("H001", "")]

    state = _integration_state([sh7_e1], bundles, groups)
    result = run_validator(state)

    assert "H001" in result["sh7s_blocked_by_validation"]
    rpt = result["validation_reports"][0]
    assert not rpt.validation_passed
    assert len(rpt.blocking_errors) >= 1
    print("PASS  test_integration_cross_doc_all_conflict")


# ============================================================
# 9. Integration — duplicate meeting_date → both blocked
# ============================================================

def test_integration_duplicate_date():
    sh7_a = _make_sh7("H001", "300000", "5000000", date(2019, 5, 15))
    sh7_b = _make_sh7("H002", "300000", "5000000", date(2019, 5, 15))  # same date!

    bundles = [_make_bundle("H001", 1), _make_bundle("H002", 2)]
    groups = [_make_group("H001", ""), _make_group("H002", "")]

    state = _integration_state([sh7_a, sh7_b], bundles, groups)
    result = run_validator(state)

    blocked = result["sh7s_blocked_by_validation"]
    assert "H001" in blocked and "H002" in blocked
    assert result["sh7s_passed_validation"] == []
    print("PASS  test_integration_duplicate_date  blocked=%s", blocked)


# ============================================================
# Runner
# ============================================================

if __name__ == "__main__":
    test_field6_extraction()
    test_arithmetic_check_pass()
    test_arithmetic_check_fail()
    test_arithmetic_check_missing_field6()
    test_continuity_pass()
    test_continuity_fail()
    test_moa_corroboration_agreed()
    test_moa_corroboration_disagreed()
    test_cross_doc_all_agree()
    test_cross_doc_one_conflict_nonblocking()
    test_cross_doc_all_conflict_blocking()
    test_cross_doc_meeting_type_not_compared()
    test_duplicate_check_no_duplicates()
    test_duplicate_check_blocks_both()
    test_integration_happy_path()
    test_integration_continuity_blocking()
    test_integration_cross_doc_all_conflict()
    test_integration_duplicate_date()
    print("\nAll Validator tests PASSED.")
