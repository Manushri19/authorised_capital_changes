"""
test_narrative_generator_no_llm.py
===================================
Test for Node 8.
"""
import sys, os
sys.path.insert(0, os.path.abspath("."))

import json
from datetime import date
from decimal import Decimal

from authorised_capital_changes.pipeline.nodes.narrative_generator import _format_display_date, run_narrative_generator
from authorised_capital_changes.schemas.capital_event import CapitalTableRow, FieldValue
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.schemas.validation import ValidationReport, ArithmeticCheckResult

def test_format_display_date():
    assert _format_display_date("On incorporation") == "On incorporation"
    assert _format_display_date(date(2018, 3, 22)) == "March 22, 2018"
    assert _format_display_date("2021-09-10") == "September 10, 2021"
    print("PASS  test_format_display_date")

def test_run_narrative_generator():
    row_0 = CapitalTableRow(
        row_number=0,
        meeting_date=FieldValue(value="On incorporation", confirmed=True, source_document="doc1", source_field_machine=None, source_field_human=None, flag_code=None, flag_message=None),
        authorised_from=FieldValue(value=None, confirmed=True, source_document="doc1", source_field_machine=None, source_field_human=None, flag_code=None, flag_message=None),
        authorised_to=FieldValue(value="Narrative 1", confirmed=True, source_document="doc1", source_field_machine=None, source_field_human=None, flag_code="FLAG_001", flag_message="Underivable"),
        meeting_type=FieldValue(value=None, confirmed=True, source_document="doc1", source_field_machine=None, source_field_human=None, flag_code=None, flag_message=None),
        source_srn="H1", source_sh7_filename="doc1.md", source_filing_date=None, has_flags=True, flag_count=1, flags=["FLAG_001"]
    )
    
    row_1 = CapitalTableRow(
        row_number=1,
        meeting_date=FieldValue(value="2018-03-22", confirmed=True, source_document="doc2", source_field_machine=None, source_field_human=None, flag_code="FLAG_002", flag_message="Date mismatch. Conflicting: bd.md=2018-03-23"),
        authorised_from=FieldValue(value="Narrative 1", confirmed=True, source_document="doc2", source_field_machine=None, source_field_human=None, flag_code=None, flag_message=None),
        authorised_to=FieldValue(value="Narrative 2", confirmed=True, source_document="doc2", source_field_machine=None, source_field_human=None, flag_code=None, flag_message=None),
        meeting_type=FieldValue(value=None, confirmed=True, source_document="doc2", source_field_machine=None, source_field_human=None, flag_code="FLAG_003", flag_message="No EGM"),
        source_srn="H2", source_sh7_filename="doc2.md", source_filing_date=None, has_flags=True, flag_count=2, flags=["FLAG_002", "FLAG_003"]
    )

    arith_fail = ArithmeticCheckResult(
        sh7_filename="H2", existing=Decimal("100"), difference=Decimal("50"), revised=Decimal("200"),
        computed_revised=Decimal("150"), passed=False, discrepancy_amount=Decimal("50")
    )
    
    val_report = ValidationReport(
        sh7_filename="H2",
        arithmetic_checks=[arith_fail],
        continuity_checks=[], cross_document_checks=[], duplicate_checks=[],
        validation_passed=True, blocking_errors=[], non_blocking_flags=[]
    )

    state = PipelineState(
        run_id="run-123",
        input_folder="/tmp",
        started_at="now",
        raw_files=[], classified_docs=[], sh7_documents=["H1", "H2"], non_sh7_documents=[],
        unclassified_documents=[], document_groups=[], unmatched_attachment_refs={},
        attachment_bundles=[], extracted_sh7s=[], sh7_extraction_errors=[],
        validation_reports=[val_report], sh7s_blocked_by_validation=[], sh7s_passed_validation=["H1", "H2"],
        capital_table_rows=[row_0, row_1], final_table_rows=[],
        discrepancy_report=None, human_review_queue=[], human_review_resolved=[], human_review_required=False,
        pipeline_errors=[], completed_stages=[]
    )

    new_state = run_narrative_generator(state)
    
    disc_rep = new_state["discrepancy_report"]
    assert disc_rep.sh7_documents_assembled == 1 # length of rows (2) - 1
    assert len(disc_rep.flags) == 3
    assert disc_rep.flags[0].flag_code == "FLAG_001"
    assert disc_rep.flags[1].flag_code == "FLAG_002"
    assert disc_rep.flags[1].conflicting_document == "bd.md"
    assert disc_rep.flags[2].flag_code == "FLAG_003"
    
    assert len(disc_rep.arithmetic_failures) == 1
    assert disc_rep.arithmetic_failures[0]["discrepancy_amount"] == Decimal("50")

    # verify HTML output
    html_file = os.path.join("data", "outputs", "capital_table.html")
    assert os.path.exists(html_file)
    with open(html_file, "r", encoding="utf-8") as f:
        html_txt = f.read()
        assert "March 22, 2018" in html_txt
        assert "[1] FLAG_001" in html_txt
        assert "[2] FLAG_002" in html_txt
        assert "[3] FLAG_003" in html_txt

    # Save a copy to the root directory for easy user review
    review_file = "test_narrative_output.html"
    with open(review_file, "w", encoding="utf-8") as f:
        f.write(html_txt)

    print("PASS  test_run_narrative_generator")
    print(f"\nSaved test HTML output to: {os.path.abspath(review_file)}")


if __name__ == "__main__":
    test_format_display_date()
    test_run_narrative_generator()
    print("All Narrative Generator tests PASSED.")
