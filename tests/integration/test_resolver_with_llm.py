import os
from pprint import pprint
from authorised_capital_changes.pipeline.nodes.ingestion import run_ingestion
from authorised_capital_changes.pipeline.nodes.classifier import run_classifier
from authorised_capital_changes.pipeline.nodes.relationship_resolver import run_relationship_resolver
from authorised_capital_changes.schemas.pipeline_state import PipelineState

def test_resolver_with_llm():
    # Make sure we have GOOGLE_API_KEY for genai testing
    os.environ["GOOGLE_API_KEY"] = "dummy"

    # Initial state
    state: PipelineState = {
        "input_folder": "c:/Users/manus/Project/authorised_capital_changes/data/raw",
        "pipeline_errors": [],
        "completed_stages": [],
        "human_review_queue": []
    }

    try:
        # Node 1
        print("Running Ingestion...")
        state = run_ingestion(state)
        print(f"Files ingested: {len(state.get('raw_files', []))}")

        # Node 2
        print("Running Classifier...")
        state = run_classifier(state)
        print(f"Classified SH-7s: {len(state.get('sh7_documents', []))}")
        print(f"Classified Non-SH-7s: {len(state.get('non_sh7_documents', []))}")
        print(f"Unclassified: {len(state.get('unclassified_documents', []))}")

        # Node 3
        print("Running Relationship Resolver...")
        state = run_relationship_resolver(state)
        
        groups = state.get('document_groups', [])
        print(f"\nDocument Groups created: {len(groups)}")
        for g in groups:
            print(f"\nGroup Event Index: {g.event_index}")
            print(f"  SH-7: {g.sh7.file_metadata.filename}")
            print(f"  EGM Resolution: {g.egm_resolution.file_metadata.filename if g.egm_resolution else None}")
            print(f"  MOA: {g.moa.file_metadata.filename if g.moa else None}")
            print(f"  Board Resolution: {g.board_resolution.file_metadata.filename if g.board_resolution else None}")
            unmatched = state.get('unmatched_attachment_refs', {}).get(g.sh7.file_metadata.filename, [])
            print(f"  Unmatched Refs: {unmatched}")

        if state.get("pipeline_errors"):
            print(f"\nErrors encountered in pipeline: {state['pipeline_errors']}")
    except Exception as e:
        print(f"Pipeline crashed: {e}")

if __name__ == "__main__":
    test_resolver_with_llm()
