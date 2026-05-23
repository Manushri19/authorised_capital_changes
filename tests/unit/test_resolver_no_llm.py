import json
from datetime import date
from authorised_capital_changes.schemas.document import FileMetadata, ClassifiedDocument, DocumentType, OfficialStatus
from authorised_capital_changes.pipeline.nodes.relationship_resolver import run_relationship_resolver
from authorised_capital_changes.schemas.pipeline_state import PipelineState

def test_resolver_no_llm():
    sh7_content = """
## Attachments
<table>
  <tbody>
    <tr><td>List of attachments</td></tr>
    <tr><td>(5) Altered memorandum of association;</td><td>Attach</td><td>CTC_EGM_2021.pdf</td></tr>
    <tr><td>MOA_2021.pdf</td></tr>
    <tr><td>CTC_Board Meeting_2021.pdf</td></tr>
    <tr><td>Noise without extension</td></tr>
    <tr><td>Remove attachment</td></tr>
  </tbody>
</table>
"""
    sh7_doc = ClassifiedDocument(
        file_metadata=FileMetadata(
            filename="SH7_Event3_2021.md",
            filepath="/tmp/SH7_Event3_2021.md",
            raw_content=sh7_content,
            file_size_bytes=100
        ),
        document_type=DocumentType.SH7,
        official_status=OfficialStatus.OFFICIAL,
        classification_method="rule_based",
        classification_confidence=1.0,
        event_date_hint=date(2021, 9, 10),
        cin_hint="U85123DL2018PTC312456",
        requires_human_review=False,
        review_reason=None
    )

    non_sh7_docs = [
        ClassifiedDocument(
            file_metadata=FileMetadata(
                filename="CTC_EGM_2021.pdf",
                filepath="/tmp/CTC_EGM_2021.pdf",
                raw_content="dummy",
                file_size_bytes=100
            ),
            document_type=DocumentType.EGM_RESOLUTION,
            official_status=OfficialStatus.CERTIFIED_COPY,
            classification_method="rule_based",
            classification_confidence=1.0,
            event_date_hint=None,
            cin_hint=None,
            requires_human_review=False,
            review_reason=None
        ),
        ClassifiedDocument(
            file_metadata=FileMetadata(
                filename="MOA_2021.pdf",
                filepath="/tmp/MOA_2021.pdf",
                raw_content="dummy",
                file_size_bytes=100
            ),
            document_type=DocumentType.MOA,
            official_status=OfficialStatus.OFFICIAL,
            classification_method="rule_based",
            classification_confidence=1.0,
            event_date_hint=None,
            cin_hint=None,
            requires_human_review=False,
            review_reason=None
        ),
        ClassifiedDocument(
            file_metadata=FileMetadata(
                filename="CTC_Board Meeting_2021.pdf",
                filepath="/tmp/CTC_Board Meeting_2021.pdf",
                raw_content="dummy",
                file_size_bytes=100
            ),
            document_type=DocumentType.BOARD_MEETING_RESOLUTION,
            official_status=OfficialStatus.CERTIFIED_COPY,
            classification_method="rule_based",
            classification_confidence=1.0,
            event_date_hint=None,
            cin_hint=None,
            requires_human_review=False,
            review_reason=None
        )
    ]

    state: PipelineState = {
        "sh7_documents": [sh7_doc],
        "non_sh7_documents": non_sh7_docs,
        "document_groups": [],
        "unmatched_attachment_refs": {},
        "pipeline_errors": [],
        "completed_stages": []
    }

    new_state = run_relationship_resolver(state)
    print("Relationship Resolver (No LLM) run successful!")
    print(f"Groups created: {len(new_state['document_groups'])}")
    group = new_state['document_groups'][0]
    print(f"Event Index: {group.event_index}")
    print(f"EGM Resolution linked: {group.egm_resolution.file_metadata.filename if group.egm_resolution else None}")
    print(f"MOA linked: {group.moa.file_metadata.filename if group.moa else None}")
    print(f"Board Resolution linked: {group.board_resolution.file_metadata.filename if group.board_resolution else None}")
    print(f"Unmatched refs: {new_state['unmatched_attachment_refs']}")

if __name__ == "__main__":
    test_resolver_no_llm()
