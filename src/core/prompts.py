SYSTEM_PROMPT = "Tu es un assistant qui analyse des textes."

EXTRACTION_PROMPT = """Résumé le texte en 2-3 phrases:
{content}

JSON:"""

ANALYSIS_PROMPT = """Trouve les problèmes dans ce texte:
{content}

JSON avec "issues":"""

RECOMMENDATION_PROMPT = """Problèmes: {issues}
Texte: {content}

Recommandations JSON:"""

def build_extraction_prompt(content: str) -> str:
    return EXTRACTION_PROMPT.format(content=content)

def build_analysis_prompt(content: str) -> str:
    return ANALYSIS_PROMPT.format(content=content)

def build_recommendation_prompt(content: str, issues: str) -> str:
    return RECOMMENDATION_PROMPT.format(content=content, issues=issues)
