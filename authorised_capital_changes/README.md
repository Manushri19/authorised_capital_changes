# Authorised Capital Changes

Authorised Capital Changes is an automated, AI-native data pipeline that extracts, corroborates, and validates corporate capital increases from filings like SH-7s, Board Resolutions, and EGMs/AGMs.

## Prerequisites

1. **Python 3.10+**
2. **Ollama**: You must have [Ollama](https://ollama.com/) running locally. The pipeline defaults to using `http://localhost:11434` for LLM extraction tasks.

## Setup Instructions

1. Clone the repository and navigate into the project root.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r authorised_capital_changes/requirements.txt
   ```

## Running the Pipeline

You can run the pipeline locally using the CLI orchestrator:

```bash
python run_pipeline.py
```

The CLI will read all documents from the `data/raw/` directory, process them via LangGraph, and output the final validated Capital Table and Discrepancy Reports into `data/outputs/`.

## Running the API

If you prefer to run the system as a REST API:

```bash
uvicorn authorised_capital_changes.api.main:app --reload
```

Then navigate to `http://localhost:8000/docs` to interact with the API endpoints.

## Project Structure

- `authorised_capital_changes/pipeline/`: Contains the LangGraph nodes and edges.
- `authorised_capital_changes/schemas/`: Contains the strict Pydantic V2 schemas used for validation and data handling.
- `authorised_capital_changes/api/`: FastAPI application and routes to interact with the pipeline via a REST interface.
- `authorised_capital_changes/services/`: Auxiliary services such as LLM clients, document parsing, and template engines.
- `authorised_capital_changes/templates/`: Jinja2 HTML templates used to render the final visual outputs.
- `authorised_capital_changes/data/raw/`: Drop your raw markdown documents here before running the CLI script.
- `data/outputs/`: The pipeline stores the final generated Capital Table (JSON/HTML) and discrepancy reports here.
- `tests/`: Contains the automated unit and integration tests.
