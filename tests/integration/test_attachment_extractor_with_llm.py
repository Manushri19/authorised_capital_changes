"""
test_attachment_extractor_with_llm.py
=======================================
Full pipeline E2E test: Ingestion → Classifier → Relationship Resolver →
Attachment Extractor using real raw files and a real Gemini API key.

Because the relationship resolver finds no .md-to-.pdf matches (the
non_sh7 documents are .md but the SH-7 attachment refs are .pdf), this test
manually injects the real file contents into DocumentGroups so the extractor
actually has content to send to the LLM.
"""

import os
from pathlib import Path
from decimal import Decimal

os.environ["GOOGLE_API_KEY"] = "dummy"

from datetime import date

from authorised_capital_changes.schemas.document import (
    ClassifiedDocument, DocumentGroup, DocumentType, FileMetadata, OfficialStatus
)
from authorised_capital_changes.schemas.pipeline_state import PipelineState
from authorised_capital_changes.pipeline.nodes.attachment_extractor import run_attachment_extractor

RAW = Path("c:/Users/manus/Project/authorised_capital_changes/data/raw")


def _load(filename: str) -> str:
    return (RAW / filename).read_text(encoding="utf-8")


def _make_doc(filename: str, doc_type: DocumentType) -> ClassifiedDocument:
    content = _load(filename)
    return ClassifiedDocument(
        file_metadata=FileMetadata(
            filename=filename,
            filepath=str(RAW / filename),
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


def test_attachment_extractor_with_llm():
    # Build four real DocumentGroups — one per event year
    events = [
        ("SH7_Event1_2018.md", "BoardMeeting_Event1_2018.md", "EGM_Event1_2018.md", "MOA_Event1_2018.md", 1),
        ("SH7_Event2_2019.md", "BoardMeeting_Event2_2019.md", "EGM_Event2_2019.md", "MOA_Event2_2019.md", 2),
        ("SH7_Event3_2021.md", "BoardMeeting_Event3_2021.md", "EGM_Event3_2021.md", "MOA_Event3_2021.md", 3),
        ("SH7_Event4_2024.md", "BoardMeeting_Event4_2024.md", "EGM_Event4_2024.md", "MOA_Event4_2024.md", 4),
    ]

    groups = []
    for sh7_f, board_f, egm_f, moa_f, idx in events:
        groups.append(DocumentGroup(
            event_index=idx,
            sh7=_make_doc(sh7_f, DocumentType.SH7),
            board_resolution=_make_doc(board_f, DocumentType.BOARD_MEETING_RESOLUTION),
            egm_resolution=_make_doc(egm_f, DocumentType.EGM_RESOLUTION),
            moa=_make_doc(moa_f, DocumentType.MOA),
            unmatched_attachment_refs=[],
        ))

    state: PipelineState = {
        "document_groups": groups,
        "pipeline_errors": [],
        "completed_stages": [],
    }

    print(f"Running Attachment Extractor on {len(groups)} groups...")
    result = run_attachment_extractor(state)

    bundles = result["attachment_bundles"]
    print(f"\nBundles created: {len(bundles)}")

    for b in bundles:
        print(f"\n{'='*60}")
        print(f"Event {b['event_index']}  |  SH-7: {b['sh7_filename']}")

        br = b["board_resolution"]
        if br:
            print(f"  Board Resolution:")
            print(f"    meeting_date            : {br.meeting_date}")
            print(f"    resolved_capital_amount : {br.resolved_capital_amount}")
            print(f"    resolution_type         : {br.resolution_type}")
            print(f"    cin                     : {br.cin}")
            print(f"    confidence              : {br.extraction_confidence:.2f}")
            print(f"    unconfirmed             : {br.unconfirmed_fields}")
            print(f"    errors                  : {br.extraction_errors}")

        egm = b["egm_resolution"]
        if egm:
            print(f"  EGM Resolution:")
            print(f"    meeting_date            : {egm.meeting_date}")
            print(f"    meeting_type            : {egm.meeting_type}")
            print(f"    resolved_capital_amount : {egm.resolved_capital_amount}")
            print(f"    cin                     : {egm.cin}")
            print(f"    confidence              : {egm.extraction_confidence:.2f}")
            print(f"    unconfirmed             : {egm.unconfirmed_fields}")
            print(f"    errors                  : {egm.extraction_errors}")

        moa = b["moa"]
        if moa:
            print(f"  MOA:")
            print(f"    incorporation_capital   : {moa.incorporation_capital}")
            print(f"    equity_shares_count     : {moa.equity_shares_count}")
            print(f"    nominal_per_share       : {moa.nominal_per_share}")
            print(f"    preference_shares_count : {moa.preference_shares_count}")
            print(f"    pref_nominal_per_share  : {moa.preference_nominal_per_share}")
            print(f"    cin                     : {moa.cin}")
            print(f"    confidence              : {moa.extraction_confidence:.2f}")
            print(f"    unconfirmed             : {moa.unconfirmed_fields}")
            print(f"    errors                  : {moa.extraction_errors}")

    if result["pipeline_errors"]:
        print(f"\nPipeline errors: {result['pipeline_errors']}")
    else:
        print("\nNo pipeline errors.")

    print(f"\nCompleted stages: {result['completed_stages']}")


if __name__ == "__main__":
    test_attachment_extractor_with_llm()
