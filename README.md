# Authorised Capital Changes Pipeline

Authorised Capital Changes Pipeline is an automated, AI-native data pipeline that extracts, corroborates, and validates corporate capital increases from filings like SH-7s, Board Resolutions, and EGMs/AGMs.

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
- `data/logs/`: The pipeline stores all the logs shown in terminal in yyyy-mm-dd hh-mm-ss format here.
- `tests/`: Contains the automated unit and integration tests.

## Output
<img width="1919" height="944" alt="image" src="https://github.com/user-attachments/assets/9bff338d-54cf-4a8e-b72e-8c43dd7b8567" />


## Logs
<img width="1824" height="902" alt="image" src="https://github.com/user-attachments/assets/0ef50995-cc97-4ef9-b729-6634d87f1001" />
<img width="1858" height="924" alt="image" src="https://github.com/user-attachments/assets/515814b8-7a28-43b3-b5aa-f12aea6ae9e2" />
<img width="1817" height="858" alt="image" src="https://github.com/user-attachments/assets/90027277-fdb2-4b69-a1bc-94783b59118a" />
<img width="1859" height="85" alt="image" src="https://github.com/user-attachments/assets/a0d24218-8653-462d-b400-92dfdfc15b5d" />
