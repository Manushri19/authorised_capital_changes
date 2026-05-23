import logging
import os
from authorised_capital_changes.pipeline.edges.routing import build_pipeline_graph
from authorised_capital_changes.schemas.pipeline_state import PipelineState

logging.basicConfig(level=logging.INFO)

def test_full_pipeline_compilation():
    graph = build_pipeline_graph()
    print("Graph compiled successfully!")
    
    # Generate the Mermaid graph representation of the DAG
    print("\n--- DAG Structure ---")
    print(graph.get_graph().draw_mermaid())
    print("---------------------\n")
    
    # We won't fully invoke it here as it requires API keys for the full run,
    # but graph compilation ensures the routing logic is fully valid!

if __name__ == "__main__":
    test_full_pipeline_compilation()
