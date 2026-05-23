import os
from datetime import date
from authorised_capital_changes.schemas.document import FileMetadata, DocumentType, OfficialStatus
from authorised_capital_changes.pipeline.nodes.classifier import run_classifier
from authorised_capital_changes.schemas.pipeline_state import PipelineState

def test_classifier():
    # Make sure we have GOOGLE_API_KEY for genai testing
    os.environ["GOOGLE_API_KEY"] = "dummy"

    state: PipelineState = {
        "raw_files": [
            FileMetadata(
                filename="SH7_dummy.md",
                filepath="/tmp/SH7_dummy.md",
                raw_content="FORM NO. SH-7\nSome text... 15/05/2019 ...",
                file_size_bytes=100
            ),
            FileMetadata(
                filename="Random_file.md",
                filepath="/tmp/Random_file.md",
                raw_content="Just some random unknown text.",
                file_size_bytes=50
            ),
            FileMetadata(
                filename="MOA_dummy.md",
                filepath="/tmp/MOA_dummy.md",
                raw_content="Memorandum of Association... Clause V...",
                file_size_bytes=200
            )
        ],
        "pipeline_errors": [],
        "completed_stages": [],
        "human_review_queue": []
    }

    try:
        new_state = run_classifier(state)
        print("Classifier run successful!")
        print(f"SH-7 docs: {len(new_state.get('sh7_documents', []))}")
        print(f"Non SH-7 docs: {len(new_state.get('non_sh7_documents', []))}")
        print(f"Unclassified/Human Review docs: {len(new_state.get('unclassified_documents', []))}")
        
        # Expect 1 SH-7, 1 non_sh7 (MOA), 1 unclassified (Random_file)
    except Exception as e:
        print(f"Exception during run_classifier: {e}")

if __name__ == "__main__":
    test_classifier()
