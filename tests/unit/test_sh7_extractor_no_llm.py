"""
test_sh7_extractor_no_llm.py
=============================
Tests the safe type-converters and the all-failures-raise path of
run_sh7_extractor — no LLM calls made.
"""

import sys, os
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from decimal import Decimal

from authorised_capital_changes.pipeline.nodes.sh7_extractor import (
    _dec, _dec_required, _int_or_none, _parse_date, _parse_date_required,
    _build_extraction, run_sh7_extractor,
)
from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus,
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sh7(filename: str, content: str = "dummy") -> ClassifiedDocument:
    return ClassifiedDocument(
        file_metadata=FileMetadata(
            filename=filename,
            filepath=f"/tmp/{filename}",
            raw_content=content,
            file_size_bytes=len(content),
        ),
        document_type=DocumentType.SH7,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=0.92,
        event_date_hint=None,
        cin_hint=None,
        requires_human_review=False,
        review_reason=None,
    )


def _make_group(filename: str, content: str = "dummy") -> DocumentGroup:
    return DocumentGroup(
        event_index=1,
        sh7=_make_sh7(filename, content),
        board_resolution=None,
        egm_resolution=None,
        moa=None,
        unmatched_attachment_refs=[],
    )


# ---------------------------------------------------------------------------
# Unit tests: converters
# ---------------------------------------------------------------------------

def test_converters():
    # _dec
    assert _dec("50,00,000.00") == Decimal("5000000.00")
    assert _dec("300000") == Decimal("300000")
    assert _dec(None) is None
    assert _dec("null") is None
    assert _dec("abc") is None
    assert _dec(10) == Decimal("10")

    # _dec_required — returns 0 and appends error on failure
    errs: list[str] = []
    assert _dec_required("5000000", "cap", errs) == Decimal("5000000")
    assert errs == []
    assert _dec_required(None, "cap", errs) == Decimal("0")
    assert len(errs) == 1

    # _int_or_none
    assert _int_or_none("500000") == 500000
    assert _int_or_none(None) is None
    assert _int_or_none("abc") is None

    # _parse_date
    assert _parse_date("15/05/2019") == date(2019, 5, 15)
    assert _parse_date("2021-09-10") == date(2021, 9, 10)
    assert _parse_date(None) is None
    assert _parse_date("bad") is None

    # _parse_date_required — fallback epoch on failure
    errs2: list[str] = []
    assert _parse_date_required("15/05/2019", "meeting_date", errs2) == date(2019, 5, 15)
    assert errs2 == []
    fallback = _parse_date_required(None, "meeting_date", errs2)
    assert fallback == date(1970, 1, 1)
    assert len(errs2) == 1

    print("All converter tests PASSED")


# ---------------------------------------------------------------------------
# Unit test: _build_extraction with well-formed args
# ---------------------------------------------------------------------------

def test_build_extraction():
    args = {
        "cin": "U85123DL2018PTC312456",
        "company_name": "NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED",
        "registered_address": "KRISHNA TOWER PLOT NO-45 SECTOR-12 DWARKA NEW DELHI",
        "email": "arunsethi@outlook.com",
        "purpose": "Increase in share capital independently by company",
        "meeting_date": "15/05/2019",
        "resolution_type": "Ordinary",
        "existing_authorised_capital": "300000",
        "revised_authorised_capital": "5000000",
        "section_9a_total_amount": "5000000",
        "section_9a_equity_shares_count": 500000,
        "section_9a_equity_nominal_per_share": "10",
        "section_9a_equity_total_amount": "5000000",
        "section_9a_preference_shares_count": 0,
        "section_9a_preference_nominal_per_share": None,
        "section_9a_preference_total_amount": None,
        "section_9a_unclassified_shares_count": None,
        "section_9a_unclassified_total_amount": None,
        "srn": "H45678902",
        "filing_date": "15/05/2019",
        "stamp_duty_state": "Delhi",
        "stamp_duty_amount": "4700",
        "attachment_filenames_raw": ["CTC_EGM_2019.pdf", "MOA_2019.pdf", "CTC_Board Meeting_2019.pdf"],
        "extraction_confidence": 0.97,
        "unconfirmed_fields": [],
        "extraction_errors": [],
    }

    ext = _build_extraction("SH7_Event2_2019.md", args)

    assert ext.cin == "U85123DL2018PTC312456"
    assert ext.meeting_date == date(2019, 5, 15)
    assert ext.existing_authorised_capital == Decimal("300000")
    assert ext.revised_authorised_capital == Decimal("5000000")
    assert ext.authorised_capital.total_amount == Decimal("5000000")
    assert ext.authorised_capital.breakdown.equity_shares_count == 500000
    assert ext.authorised_capital.breakdown.equity_nominal_per_share == Decimal("10")
    assert ext.authorised_capital.breakdown.preference_shares_count == 0
    assert ext.srn == "H45678902"
    assert ext.stamp_duty_state == "Delhi"
    assert ext.stamp_duty_amount == Decimal("4700")
    assert ext.attachment_filenames_raw == [
        "CTC_EGM_2019.pdf", "MOA_2019.pdf", "CTC_Board Meeting_2019.pdf"
    ]
    assert ext.extraction_confidence == 0.97
    # model_validator: 9(a) total matches revised — no mismatch error
    assert not any("does not match" in e for e in ext.extraction_errors)
    print(f"_build_extraction test PASSED | srn={ext.srn} confidence={ext.extraction_confidence}")


# ---------------------------------------------------------------------------
# Integration test: all-failures raises ValueError
# ---------------------------------------------------------------------------

def test_all_failures_raise():
    """When every LLM call returns None, ValueError must be raised."""

    # Patch _call_llm to always return None
    import authorised_capital_changes.pipeline.nodes.sh7_extractor as mod
    original = mod._call_llm
    mod._call_llm = lambda _: None

    state: PipelineState = {
        "document_groups": [_make_group("SH7_Event1.md"), _make_group("SH7_Event2.md")],
        "pipeline_errors": [],
        "completed_stages": [],
        "sh7_extraction_errors": [],
    }

    raised = False
    try:
        mod.run_sh7_extractor(state)
    except ValueError as e:
        raised = True
        assert "all 2 extractions failed" in str(e)
        print(f"all-failures ValueError PASSED: {e}")
    finally:
        mod._call_llm = original  # restore

    assert raised, "Expected ValueError was not raised"


if __name__ == "__main__":
    test_converters()
    test_build_extraction()
    test_all_failures_raise()
    print("\nAll no-LLM SH-7 extractor tests passed.")
