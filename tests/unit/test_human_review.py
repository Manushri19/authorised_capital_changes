import logging
from authorised_capital_changes.pipeline.nodes.human_review import run_human_review
from authorised_capital_changes.schemas.document import ClassifiedDocument, FileMetadata, DocumentType, OfficialStatus
from authorised_capital_changes.schemas.pipeline_state import PipelineState

logging.basicConfig(level=logging.INFO)

def test_human_review():
    doc1 = ClassifiedDocument(
        file_metadata=FileMetadata(filename="unknown_file.md", filepath="...", raw_content="...", file_size_bytes=10),
        document_type=DocumentType.UNKNOWN,
        official_status=OfficialStatus.UNCONFIRMED,
        classification_method="rule_based",
        classification_confidence=0.1,
        requires_human_review=True,
        review_reason="LOW_CONFIDENCE",
        event_date_hint=None,
        cin_hint=None
    )

    doc2 = ClassifiedDocument(
        file_metadata=FileMetadata(filename="duplicate_sh7.md", filepath="...", raw_content="...", file_size_bytes=10),
        document_type=DocumentType.SH7,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=0.9,
        requires_human_review=True,
        review_reason="DUPLICATE_MEETING_DATE",
        event_date_hint=None,
        cin_hint=None
    )

    state: PipelineState = {
        "human_review_queue": [doc1, doc2],
        "human_review_resolved": [],
        "completed_stages": []
    }

    new_state = run_human_review(state)
    resolved = new_state["human_review_resolved"]
    
    assert len(resolved) == 2
    assert resolved[0]["filename"] == "unknown_file.md"
    assert resolved[0]["review_reason"] == "LOW_CONFIDENCE"
    assert resolved[0]["stage_flagged"] == "classifier"

    assert resolved[1]["filename"] == "duplicate_sh7.md"
    assert resolved[1]["review_reason"] == "DUPLICATE_MEETING_DATE"
    assert resolved[1]["stage_flagged"] == "classifier"
    
    print("All Human Review tests PASSED.")

if __name__ == "__main__":
    test_human_review()
