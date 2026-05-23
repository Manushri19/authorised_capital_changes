import os
from datetime import date
from decimal import Decimal

os.environ["GOOGLE_API_KEY"] = "dummy"

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.pipeline.nodes.attachment_extractor import run_attachment_extractor

BOARD_RESOLUTION = """
NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED
CERTIFIED TRUE COPY OF THE RESOLUTION PASSED AT THE MEETING OF THE BOARD OF DIRECTORS 
HELD ON 10th SEPTEMBER 2021 AT 11:00 AM

INCREASE IN AUTHORISED SHARE CAPITAL
"RESOLVED THAT pursuant to the provisions of Section 61 and 64 of the Companies Act, 2013, 
the consent of the Board of Directors of the Company be and is hereby accorded, subject to the 
approval of shareholders, to increase the Authorized Share Capital of the Company from 
Rs. 50,00,000 (Rupees Fifty Lakh) to Rs. 1,50,00,000 (Rupees One Crore Fifty Lakh) divided 
into 15,00,000 Equity Shares of Rs. 10/- each."

FURTHER RESOLVED THAT this Ordinary resolution shall take effect immediately.
CIN: U85123DL2018PTC312456
"""

EGM_RESOLUTION = """
NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED
EXTRA ORDINARY GENERAL MEETING
HELD ON 15th OCTOBER 2021 AT 10:00 AM

TO AMEND THE MEMORANDUM OF ASSOCIATION & INCREASE IN AUTHORISED SHARE CAPITAL
"RESOLVED THAT pursuant to Section 61 and 64 of the Companies Act, 2013, the consent of the 
members of the Company be and is hereby accorded to increase the Authorized Share Capital 
of the Company to Rs. 1,50,00,000 (Rupees One Crore Fifty Lakh) divided into 15,00,000 
Equity Shares of Rs. 10/- each."

Registered Office: DWARKA NEW DELHI, DL 110075 IN
CIN: U85123DL2018PTC312456
"""

MOA_CONTENT = """
MEMORANDUM OF ASSOCIATION
NEXUS BRIGHTLEARN SOLUTIONS PRIVATE LIMITED

V. The Authorised Share Capital of the Company is Rs. 1,50,00,000/- (Rupees One Crore Fifty Lakh) 
divided into 15,00,000 (Fifteen Lakh) Equity Shares of Rs. 10/- (Rupees Ten) each.

CIN: U85123DL2018PTC312456
"""

def _make_doc(filename: str, doc_type: DocumentType, content: str) -> ClassifiedDocument:
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
        classification_confidence=0.99,
        event_date_hint=None,
        cin_hint=None,
        requires_human_review=False,
        review_reason=None,
    )

def test_mini_llm():
    sh7 = _make_doc("SH7_Event3_2021.md", DocumentType.SH7, "dummy sh7")
    board = _make_doc("Board_2021.md", DocumentType.BOARD_MEETING_RESOLUTION, BOARD_RESOLUTION)
    egm = _make_doc("EGM_2021.md", DocumentType.EGM_RESOLUTION, EGM_RESOLUTION)
    moa = _make_doc("MOA_2021.md", DocumentType.MOA, MOA_CONTENT)

    group = DocumentGroup(
        event_index=3,
        sh7=sh7,
        board_resolution=board,
        egm_resolution=egm,
        moa=moa,
        unmatched_attachment_refs=[],
    )

    state: PipelineState = {
        "document_groups": [group],
        "pipeline_errors": [],
        "completed_stages": [],
    }

    print("Running Mini LLM Test for Attachment Extractor...")
    result = run_attachment_extractor(state)

    b = result["attachment_bundles"][0]
    print("\nExtraction Results:")
    print("=" * 40)
    
    br = b["board_resolution"]
    print("BOARD RESOLUTION:")
    print(f"  Meeting Date: {br.meeting_date}")
    print(f"  Resolved Capital: {br.resolved_capital_amount}")
    print(f"  Resolution Type: {br.resolution_type}")
    print(f"  CIN: {br.cin}")
    
    egm = b["egm_resolution"]
    print("\nEGM RESOLUTION:")
    print(f"  Meeting Date: {egm.meeting_date}")
    print(f"  Meeting Type: {egm.meeting_type}")
    print(f"  Resolved Capital: {egm.resolved_capital_amount}")
    print(f"  CIN: {egm.cin}")
    
    moa = b["moa"]
    print("\nMOA:")
    print(f"  Auth Capital: {moa.incorporation_capital}")
    print(f"  Equity Shares: {moa.equity_shares_count}")
    print(f"  Nominal/Share: {moa.nominal_per_share}")
    print(f"  Preference Shares: {moa.preference_shares_count}")
    print(f"  CIN: {moa.cin}")

    print("\nDone.")

if __name__ == "__main__":
    test_mini_llm()
