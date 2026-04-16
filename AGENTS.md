# AGENTS.md - Agentic Coding Guidelines

**Project**: Cahier des Charges Analyzer - analyzes specifications to detect security issues, contradictions, legal/RGPD problems, ambiguities, and edge cases.

## Commands

```bash
# Python backend (activate venv first: source venv/bin/activate)
pip install -r requirements.txt
pytest                    # run all tests
pytest tests/test_analyzer.py -v        # specific test file
pytest tests/test_analyzer.py::TestOllamaAnalyzer::test_health_check_connected -v  # single test

streamlit run app.py        # web interface on http://localhost:8501
uvicorn src.api.main:app --reload --port 8000   # REST API

# Frontend
cd frontend && npm install && npm run dev
```

## Architecture

- **Backend**: Python (FastAPI + Streamlit + Pydantic)
- **Frontend**: React + TypeScript + Tailwind CSS + Vite
- **Config**: `.env` + Pydantic `BaseSettings` in `src/core/config.py`
- **LLM Providers**: Groq (default), Ollama, HuggingFace - toggle via `USE_GROQ`, `USE_OLLAMA`, `USE_HUGGINGFACE` in `.env`

## Key Facts

- **Entry points**: `app.py` (Streamlit), `src/api/main.py` (FastAPI), `analyzer.py` (main logic)
- **API Responses**: Structured JSON with `resume`, `problemes`, `extraction`
- **Problem Categories**: `SECURITE`, `CONTRADICTION`, `LEGAL`, `AMBIGUITE`, `EDGE_CASE`
- **Severity Levels**: `CRITIQUE`, `ELEVEE`, `MOYENNE`, `FAIBLE`
- **Extraction Schema**: Nested dict with `metadonnees`, `contraintes_projet`, `dossier_reponse`, `references`, `exigences`, `modalites_paiement`

## YAML Rules

Rules auto-loaded from `rules/` directory (`security_patterns.yaml`, `inconsistencies.yaml`, `bugs_patterns.yaml`).