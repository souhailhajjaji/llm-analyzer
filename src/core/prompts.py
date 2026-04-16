import json

EXAMPLES = """
EXEMPLE de structure CPS française:
- "Maître d'Ouvrage: Commune de Paris"
- "Objet: Création d'un site web institutionnel"
- "Budget: 150 000 € HT"
- "Date limite: 31/12/2024"
- "Caution provisoire: 3% du montant"
- "Délai d'exécution: 6 mois"
"""

SYSTEM_PROMPT = """Tu es un expert en analyse de marchés publics français (Cahier des Prescriptions Spéciales).
Tu EXTRAIS les métadonnées et détectes les problèmes de sécurité, contradictions, légales et ambiguïtés.
RETOURNE TOUJOURS du JSON valide sans texte avant/après, sans markdown."""

EXTRACTION_PROMPT = """EXTRAIS les informations structurées de ce cahier des charges (CPS).

{cahier_des_charges}

{EXAMPLES}

RESPONDS EXACTEMENT en JSON avec cette structure:

{{
  "extraction": {{
    "metadonnees": {{
      "nom_client": "string ou null",
      "objet": "string ou null",
      "objectifs": ["liste ou []"],
      "orientations_technologiques": ["liste ou []"]
    }},
    "contraintes_projet": {{
      "date_limite_soumission": "string ou null",
      "budget": "string ou null",
      "caution_provisoire": "string ou null",
      "delai_execution": "string ou null"
    }},
    "dossier_reponse": {{
      "administratif": ["liste ou []"],
      "technique": ["liste ou []"],
      "financier": ["liste ou []"]
    }},
    "references": ["liste ou []"],
    "exigences": ["liste ou []"],
    "modalites_paiement": ["liste ou []"]
  }}
}}

INSTRUCTIONS:
1. Extrais UNIQUEMENT les infos EXPLICITEMENT présentes
2. Si absent, utilise null ou []
3. Cherche: Maître d'Ouvrage, Objet, Objectifs, Tech, Budget, Date, Caution, Délai

JSON:"""


def build_extraction_prompt(content: str) -> str:
    return EXTRACTION_PROMPT.format(cahier_des_charges=content, EXAMPLES=EXAMPLES)


PROBLEM_CATEGORIES = """
CATEGORIES de problèmes à détecter:

1. SECURITE: mots de passe en clair, données sensibles, clefs API, tokens, secrets
2. CONTRADICTION: dates incohérentes, budgets contradictoires, exigences incompatibles
3. LEGAL: manquements RGPD, clauses illégales, conditions abusives
4. AMBIGUITE: termes imprécis, délais flous, exigences non mesurables
5. EDGE_CASE: cas limites non définis, exceptions non gérées

SEVERITES:
- CRITIQUE: bloque le marché, risque juridique majeur
- ELEVEE: problème important à résoudre
- MOYENNE: amélioration recommandée
- FAIBLE: suggestion mineure
"""

ANALYSIS_PROMPT = """ANALYSE ce cahier des charges et détecte TOUS les problèmes.

{cahier_des_charges}

{PROBLEM_CATEGORIES}

Réponds en JSON:
{{
  "resume": {{
    "total_problemes": 0,
    "critiques": 0,
    "eleves": 0,
    "moyens": 0,
    "faibles": 0
  }},
  "problemes": [
    {{
      "id": 1,
      "categorie": "SECURITE|CONTRADICTION|LEGAL|AMBIGUITE|EDGE_CASE",
      "severite": "CRITIQUE|ELEVEE|MOYENNE|FAIBLE",
      "titre": "Titre du problème",
      "description": "Description concise",
      "localisation": "Section ou paragraphe",
      "recommendation": "Recommandation pour résoudre"
    }}
  ]
}}

JSON:"""


def build_analysis_prompt(content: str) -> str:
    return ANALYSIS_PROMPT.format(cahier_des_charges=content, PROBLEM_CATEGORIES=PROBLEM_CATEGORIES)


RECOMMENDATION_PROMPT = """Basé sur l'analyse suivante du cahier des charges, génère des recommandations précises:

{analysis_result}

Pour chaque problème, fournis:
1. Une recommandation actionnable
2. Un indice d'implémentation
3. Une priorité (1-5)

Réponds en JSON:
{{
  "recommendations": [
    {{
      "issue_id": "1",
      "priority": 1,
      "recommendation": "Description",
      "implementation_hint": "Comment implémenter"
    }}
  ]
}}

JSON:"""


def build_recommendation_prompt(analysis_result: str) -> str:
    return RECOMMENDATION_PROMPT.format(analysis_result=analysis_result)


NOM_CLIENT_PROMPT = """Extrait le nom du client/maître d'ouvrage de ce marché.

{cahier_des_charges}

Réponds en JSON:
{{"nom_client": "string ou null"}}

JSON:"""


def build_nom_client_prompt(content: str) -> str:
    return NOM_CLIENT_PROMPT.format(cahier_des_charges=content)


OBJET_PROMPT = """Extrait l'objet du marché.

{cahier_des_charges}

Réponds en JSON:
{{"objet": "string ou null"}}

JSON:"""


def build_objet_prompt(content: str) -> str:
    return OBJET_PROMPT.format(cahier_des_charges=content)


OBJECTIFS_PROMPT = """Extrait les objectifs du projet.

{cahier_des_charges}

INSTRUCTIONS:
- Extrais UNIQUEMENT les objectifs EXPRESSEMENT mentionnés
- Si aucun objectif explicite, retourne []

Réponds en JSON:
{{"objectifs": ["liste ou []"]}}

JSON:"""


def build_objectifs_prompt(content: str) -> str:
    return OBJECTIFS_PROMPT.format(cahier_des_charges=content)


ORIENTATIONS_TECH_PROMPT = """Extrait les orientations technologiques.

{cahier_des_charges}

INSTRUCTIONS:
- Extrais UNIQUEMENT les technologies EXPLICITEMENT mentionnées
- Si aucune technologie explicite, retourne []

Réponds en JSON:
{{"orientations_technologiques": ["liste ou []"]}}

JSON:"""


def build_orientations_tech_prompt(content: str) -> str:
    return ORIENTATIONS_TECH_PROMPT.format(cahier_des_charges=content)


DATE_LIMITE_PROMPT = """Extrait la date limite de soumission.

{cahier_des_charges}

Réponds en JSON:
{{"date_limite_soumission": "string ou null"}}

JSON:"""


def build_date_limite_prompt(content: str) -> str:
    return DATE_LIMITE_PROMPT.format(cahier_des_charges=content)


BUDGET_PROMPT = """Extrait le budget.

{cahier_des_charges}

Réponds en JSON:
{{"budget": "string ou null"}}

JSON:"""


def build_budget_prompt(content: str) -> str:
    return BUDGET_PROMPT.format(cahier_des_charges=content)


CAUTION_PROVISOIRE_PROMPT = """Extrait la caution provisoire.

{cahier_des_charges}

Réponds en JSON:
{{"caution_provisoire": "string ou null"}}

JSON:"""


def build_caution_provisoire_prompt(content: str) -> str:
    return CAUTION_PROVISOIRE_PROMPT.format(cahier_des_charges=content)


DELAI_EXECUTION_PROMPT = """Extrait le délai d'exécution.

{cahier_des_charges}

Réponds en JSON:
{{"delai_execution": "string ou null"}}

JSON:"""


def build_delai_execution_prompt(content: str) -> str:
    return DELAI_EXECUTION_PROMPT.format(cahier_des_charges=content)


REFERENCES_PROMPT = """Extrait les références juridiques.

{cahier_des_charges}

Réponds en JSON:
{{"references": ["liste ou []"]}}

JSON:"""


def build_references_prompt(content: str) -> str:
    return REFERENCES_PROMPT.format(cahier_des_charges=content)


EXIGENCES_PROMPT = """Extrait les exigences du marché.

{cahier_des_charges}

Réponds en JSON:
{{"exigences": ["liste ou []"]}}

JSON:"""


def build_exigences_prompt(content: str) -> str:
    return EXIGENCES_PROMPT.format(cahier_des_charges=content)


MODALITES_PAIEMENT_PROMPT = """Extrait les modalités de paiement.

{cahier_des_charges}

Réponds en JSON:
{{"modalites_paiement": ["liste ou []"]}}

JSON:"""


def build_modalites_paiement_prompt(content: str) -> str:
    return MODALITES_PAIEMENT_PROMPT.format(cahier_des_charges=content)


DOSSIER_REPONSE_PROMPT = """Extrait les pièces du dossier de réponse.

{cahier_des_charges}

Réponds en JSON:
{{"dossier_reponse": {{
  "administratif": ["liste ou []"],
  "technique": ["liste ou []"],
  "financier": ["liste ou []"]
}}}}

JSON:"""


def build_dossier_reponse_prompt(content: str) -> str:
    return DOSSIER_REPONSE_PROMPT.format(cahier_des_charges=content)