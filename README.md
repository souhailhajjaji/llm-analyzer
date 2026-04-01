# Cahier Charges Analyzer

Analyseur intelligent de cahier des charges utilisant LLM (Hugging Face).

## Fonctionnalités

- Analyse automatique avec Qwen2.5-14B
- Détection de :
  - Bugs et anti-patterns
  - Problèmes de sécurité (OWASP)
  - Incohérences et contradictions
- Interface Streamlit
- API REST avec FastAPI
- Génération de rapports JSON

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Interface Web (Streamlit)

```bash
streamlit run app.py
```

L'interface sera accessible sur http://localhost:8501

## Déploiement gratuit sur Hugging Face Spaces

1. Créer un compte sur [huggingface.co](https://huggingface.co)
2. Créer un nouveau Space (Streamlit)
3. Uploader: `app.py`, `analyzer.py`, `requirements.txt`

## API

```bash
uvicorn src.api.main:app --reload
```

## License

MIT
