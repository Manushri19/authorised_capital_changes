"""
test_narrative_scenarios.py
============================
Mocks four end-to-end scenarios generating the full Capital Table:
1. On Incorporation (Equity only)
2. Equity to Equity
3. Equity to Equity + Preference
4. Both to Both

Outputs an HTML file for visual review.
"""
import sys, os, shutil
sys.path.insert(0, os.path.abspath("."))

from datetime import date
from decimal import Decimal

from authorised_capital_changes.schemas.sh7 import SH7Extraction, AuthorisedCapitalBlock, ShareBreakdown
from authorised_capital_changes.schemas.attachment import EGMResolutionExtraction
from authorised_capital_changes.schemas.pipeline_state import AttachmentExtractionBundle, PipelineState
from authorised_capital_changes.schemas.validation import ValidationReport
from authorised_capital_changes.schemas.document import DocumentGroup, ClassifiedDocument, FileMetadata, DocumentType, OfficialStatus

from authorised_capital_changes.pipeline.nodes.assembler import run_assembler
from authorised_capital_changes.pipeline.nodes.narrative_generator import run_narrative_generator

def _make_sh7(srn, existing, revised, meeting_date, eq_cnt, eq_nom, pref_cnt=None, pref_nom=None):
    return SH7Extraction(
        srn=srn,
        cin="U12345",
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
                equity_shares_count=eq_cnt,
                equity_nominal_per_share=Decimal(eq_nom) if eq_nom else None,
                equity_total_amount=Decimal(eq_cnt * int(eq_nom)) if eq_cnt and eq_nom else None,
                preference_shares_count=pref_cnt,
                preference_nominal_per_share=Decimal(pref_nom) if pref_nom else None,
                preference_total_amount=Decimal(pref_cnt * int(pref_nom)) if pref_cnt and pref_nom else None,
                unclassified_shares_count=None,
                unclassified_total_amount=None,
            )
        ),
        filing_date=meeting_date,
        stamp_duty_state="Delhi",
        stamp_duty_amount=Decimal("100"),
        attachment_filenames_raw=[],
        extraction_confidence=0.9,
        unconfirmed_fields=[],
        extraction_errors=[],
    )

def _make_egm(srn, meeting_type):
    return AttachmentExtractionBundle(
        event_index=1,
        sh7_filename=srn,
        board_resolution=None,
        egm_resolution=EGMResolutionExtraction(
            source_filename=f"{srn}_EGM.md",
            cin="U123",
            meeting_date=date(2019,1,1),
            meeting_type=meeting_type,
            resolved_capital_amount=Decimal("1000"),
            extraction_confidence=0.9,
            unconfirmed_fields=[],
            extraction_errors=[]
        ),
        moa=None
    )

def _make_doc_group(srn, index):
    return DocumentGroup(
        sh7=ClassifiedDocument(
            file_metadata=FileMetadata(
                filename=srn,
                filepath=f"/tmp/{srn}",
                raw_content="",
                file_size_bytes=100
            ),
            document_type=DocumentType.SH7,
            official_status=OfficialStatus.OFFICIAL,
            classification_method="rule_based",
            classification_confidence=1.0,
            event_date_hint=None,
            cin_hint=None,
            requires_human_review=False,
            review_reason=None
        ),
        attachments=[],
        board_resolution=None,
        egm_resolution=None,
        moa=None,
        unmatched_attachment_refs=[],
        event_index=index
    )

def run_scenarios():
    # Event 1: Incorporation (1 Lakh, Equity only) - Date ignored by assembler for row 0
    e1 = _make_sh7("Event_1", "100000", "100000", date(2015, 1, 1), 10000, "10")
    
    # Event 2: Equity -> Equity (2 Lakh)
    e2 = _make_sh7("Event_2", "100000", "200000", date(2016, 11, 17), 20000, "10")
    
    # Event 3: Equity -> Equity + Pref (3 Lakh)
    e3 = _make_sh7("Event_3", "200000", "300000", date(2021, 7, 22), 20000, "10", 10000, "10")
    
    # Event 4: Both -> Both (11 Crore)
    e4 = _make_sh7("Event_4", "300000", "110000000", date(2025, 9, 29), 19990000, "10", 10000, "10")

    sh7s = [e1, e2, e3, e4]
    
    # We map meeting types for Events 2, 3, 4: EGM, EGM, AGM
    meeting_types = ["EGM", "EGM", "AGM"]
    bundles = [_make_egm(e.srn, meeting_types[i]) for i, e in enumerate(sh7s[1:])]
    
    val_reports = [
        ValidationReport(
            sh7_filename=e.srn, arithmetic_checks=[], continuity_checks=[], 
            cross_document_checks=[], duplicate_checks=[], validation_passed=True, 
            blocking_errors=[], non_blocking_flags=[]
        ) for e in sh7s
    ]
    doc_groups = [_make_doc_group(e.srn, i) for i, e in enumerate(sh7s)]

    state = PipelineState(
        run_id="test-scenarios", 
        input_folder="/tmp", 
        started_at="now", 
        raw_files=[], 
        classified_docs=[], 
        sh7_documents=[e.srn for e in sh7s], 
        non_sh7_documents=[], 
        unclassified_documents=[], 
        document_groups=doc_groups, 
        unmatched_attachment_refs={}, 
        attachment_bundles=bundles, 
        extracted_sh7s=sh7s, 
        sh7_extraction_errors=[], 
        validation_reports=val_reports, 
        sh7s_blocked_by_validation=[], 
        sh7s_passed_validation=[e.srn for e in sh7s], 
        capital_table_rows=[], 
        final_table_rows=[], 
        discrepancy_report=None, 
        human_review_queue=[], 
        human_review_resolved=[], 
        human_review_required=False, 
        pipeline_errors=[], 
        completed_stages=[]
    )

    print("Running Assembler...")
    state = run_assembler(state)
    
    print("Running Narrative Generator...")
    state = run_narrative_generator(state)
    
    html_path = "test_narrative_scenarios_output.html"
    shutil.copy(os.path.join("data", "outputs", "capital_table.html"), html_path)
    
    print(f"\nSUCCESS! Scenarios HTML successfully saved to: {os.path.abspath(html_path)}")

if __name__ == "__main__":
    run_scenarios()
