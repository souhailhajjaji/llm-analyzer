# AGENTS.md - Agentic Coding Guidelines

This file provides guidelines for agents working on this codebase.

## Project Overview

This is a **Cahier des Charges Analyzer** - a tool that analyzes specifications/requirements documents to detect security issues, contradictions, legal problems (RGPD), ambiguities, and edge cases. It consists of:

- **Backend**: Python with FastAPI, Streamlit, Pydantic
- **Frontend**: React + TypeScript + Tailwind CSS + Vite

---

## Build / Lint / Test Commands

### Python Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a specific test file
pytest tests/test_analyzer.py -v

# Run a single test
pytest tests/test_analyzer.py::TestAnalyseRegles::test_mots_passe_en_clair -v

# Run Streamlit web interface
streamlit run app.py

# Run FastAPI server
uvicorn src.api.main:app --reload
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build
```

---

## Code Style Guidelines

### Python

#### Imports
- Standard library imports first, then third-party, then local
- Use absolute imports from `src` (e.g., `from src.core.config import settings`)
- Group: `import X` → `from X import Y`

#### Type Hints
- Use Python 3.10+ union syntax: `X | None` instead of `Optional[X]`
- Use generics: `list[str]`, `dict[str, Any]`
- All function arguments and return types should be typed

#### Naming Conventions
- Classes: `CamelCase` (e.g., `CahierDesChargesAnalyzer`)
- Functions/methods: `snake_case` (e.g., `analyser_cahier`)
- Constants: `UPPER_SNAKE_CASE`
- Private methods: prefix with `_`

#### Error Handling
- Use specific exceptions: `FileNotFoundError`, `ValueError`
- Never catch bare `Exception` without re-raising or logging
- Validate inputs with Pydantic models

#### Dataclasses & Pydantic
- Use `@dataclass` for simple data containers
- Use Pydantic `BaseModel` for API request/response validation
- Use Pydantic `BaseSettings` for configuration (loads from `.env`)

#### Example Structure

```python
from typing import Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    text: str
    use_huggingface: bool = False

@dataclass
class Problem:
    categorie: str
    severite: str
    titre: str
    description: str
    recommendation: str

def analyse_cahier(text: str) -> Dict[str, Any]:
    """Analyze cahier des charges and return problems."""
    if not text:
        raise ValueError("Text cannot be empty")
    # ... implementation
```

### TypeScript / React

#### Naming
- Components: `PascalCase` (e.g., `AnalysisResults.tsx`)
- Hooks: `camelCase` starting with `use` (e.g., `useAnalysis`)
- Files: `kebab-case.tsx`

#### Type Safety
- Use explicit types for props, state, and API responses
- Avoid `any` - use `unknown` if type is uncertain

#### Example

```typescript
interface Problem {
  categorie: string;
  severite: 'CRITIQUE' | 'ELEVEE' | 'MOYENNE' | 'FAIBLE';
  titre: string;
  description: string;
  recommendation: string;
}

interface AnalysisResult {
  resume: { total_problemes: number };
  problemes: Problem[];
}
```

---

## Project Structure

```
.
├── app.py                 # Streamlit entry point
├── analyzer.py            # Main analysis logic
├── requirements.txt       # Python dependencies
├── src/
│   ├── api/
│   │   ├── main.py       # FastAPI app
│   │   └── routes/       # API endpoints
│   ├── core/
│   │   ├── config.py     # Pydantic settings
│   │   ├── prompts.py    # LLM prompts
│   │   └── rules_loader.py
│   └── services/
│       ├── llm_analyzer.py     # LLM integration
│       ├── rule_analyzer.py    # Rule-based analysis
│       ├── document_extractor.py
│       └── report_generator.py
├── tests/
│   ├── test_analyzer.py
│   ├── test_api.py
│   └── test_extractor.py
├── rules/                 # YAML rule definitions
│   ├── bugs_patterns.yaml
│   ├── security_patterns.yaml
│   └── inconsistencies.yaml
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── hooks/
    │   ├── services/
    │   └── types/
    └── package.json
```

---

## Key Conventions

1. **Configuration**: All config via `.env` + Pydantic `BaseSettings`
2. **API Responses**: Always return structured JSON with `resume`, `problemes`, `extraction`
3. **Problem Categories**: `SECURITE`, `CONTRADICTION`, `LEGAL`, `AMBIGUITE`, `EDGE_CASE`
4. **Severity Levels**: `CRITIQUE`, `ELEVEE`, `MOYENNE`, `FAIBLE`
5. **Testing**: Place tests in `tests/` directory, use pytest with class-based test groups

---

## Common Tasks

### Running a Single Test

```bash
# By test function name
pytest tests/test_analyzer.py::TestAnalyseRegles::test_api_sans_auth -v

# By test class
pytest tests/test_analyzer.py::TestCahierDesChargesAnalyzer -v
```

### Adding a New Rule

1. Add pattern to appropriate YAML in `rules/` (e.g., `security_patterns.yaml`)
2. The rule analyzer auto-loads rules from YAML files
3. Format: `pattern`, `categorie`, `severite`, `titre`, `description`, `recommendation`

### Adding a New LLM Model

1. Add model config to `src/core/config.py` (Settings class)
2. Implement new analyzer class in `src/services/llm_analyzer.py`
3. Update `analyzer.py` to support the new model option
