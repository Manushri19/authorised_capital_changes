from typing import Dict
from authorised_capital_changes.schemas.pipeline_state import PipelineState

# In-memory dictionary to hold state across asynchronous API requests
runs_store: Dict[str, PipelineState] = {}
