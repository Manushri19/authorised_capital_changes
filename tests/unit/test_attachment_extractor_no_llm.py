"""
test_attachment_extractor_no_llm.py
====================================
Tests _to_decimal, _to_date, _to_int converters and the no-attachment path
of run_attachment_extractor — no LLM calls made.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from datetime import date
from decimal import Decimal

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.pipeline.nodes.attachment_extractor import (
    _to_decimal, _to_date, _to_int, run_attachment_extractor
)


# ---------------------------------------------------------------------------
# Helper to build a minimal ClassifiedDocument
# ---------------------------------------------------------------------------

def _make_doc(filename: str, doc_type: DocumentType, content: str = "dummy") -> ClassifiedDocument:
    return ClassifiedDocument(
        file_metadata=FileMetadata(
            filename=filename,
            filepath=f"/tmp/{filename}",
            raw_content=content,
            file_size_bytes=len(content),
        ),
        document_type=doc_type,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=0.92,
        event_date_hint=None,
        cin_hint=None,
        requires_human_review=False,
        review_reason=None,
    )


# ---------------------------------------------------------------------------
# Unit tests: safe converters
# ---------------------------------------------------------------------------

def test_converters():
    errors = []

    # _to_decimal
    assert _to_decimal("5000000") == Decimal("5000000"), "_to_decimal basic"
    assert _to_decimal("5,00,000") == Decimal("500000"), "_to_decimal with commas"
    assert _to_decimal(None) is None, "_to_decimal None"
    assert _to_decimal("null") is None, "_to_decimal 'null' string"
    assert _to_decimal("abc") is None, "_to_decimal non-numeric"
    assert _to_decimal(100) == Decimal("100"), "_to_decimal int passthrough"

    # _to_date
    assert _to_date("15/05/2019") == date(2019, 5, 15), "_to_date DD/MM/YYYY"
    assert _to_date("2021-09-10") == date(2021, 9, 10), "_to_date YYYY-MM-DD"
    assert _to_date(None) is None, "_to_date None"
    assert _to_date("not-a-date") is None, "_to_date invalid"

    # _to_int
    assert _to_int("500000") == 500000, "_to_int string"
    assert _to_int(200000) == 200000, "_to_int int"
    assert _to_int(None) is None, "_to_int None"
    assert _to_int("abc") is None, "_to_int invalid"

    print("All converter tests PASSED")


# ---------------------------------------------------------------------------
# Integration: group with NO attachments → bundle with all-None extractions
# ---------------------------------------------------------------------------

def test_empty_group():
    sh7 = _make_doc("SH7_Event1_2018.md", DocumentType.SH7)
    group = DocumentGroup(
        event_index=1,
        sh7=sh7,
        board_resolution=None,
        egm_resolution=None,
        moa=None,
        unmatched_attachment_refs=[],
    )

    state: PipelineState = {
        "document_groups": [group],
        "pipeline_errors": [],
        "completed_stages": [],
    }

    result = run_attachment_extractor(state)

    bundles = result["attachment_bundles"]
    assert len(bundles) == 1, "Expected 1 bundle"
    b = bundles[0]
    assert b["event_index"] == 1
    assert b["sh7_filename"] == "SH7_Event1_2018.md"
    assert b["board_resolution"] is None
    assert b["egm_resolution"] is None
    assert b["moa"] is None
    assert "attachment_extractor" in result["completed_stages"]
    print(f"Empty group test PASSED | bundle sh7={b['sh7_filename']} event={b['event_index']}")


if __name__ == "__main__":
    test_converters()
    test_empty_group()
    print("\nAll no-LLM tests passed.")
