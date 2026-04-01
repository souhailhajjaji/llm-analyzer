"""
Analyseur de Cahier des Charges
Utilise Ollama (local) ou Hugging Face pour l'analyse
"""

import json
import requests
from typing import Dict, List, Any, Optional

OLLAMA_URL = "http://localhost:11434/api/generate"
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-1B-Instruct"

SYSTEM_PROMPT = """Tu es un expert en analyse de cahier des charges logiciels.
Ton rôle est de détecter et classifier tous les problèmes dans un cahier des charges.

## Catégories de problèmes à détecter:

### 1. CONTRADICTIONS
- Deux exigences qui se contredisent mutuellement
- Exemple: "Le mot de passe doit contenir au moins 8 caractères" ET "Le mot de passe peut contenir moins de 8 caractères"

### 2. PROBLÈMES DE SÉCURITÉ
- Stockage de mots de passe en clair
- Absence de validation des entrées
- Sessions qui n'expirent jamais
- API sans authentification
- Permissions trop larges

### 3. PROBLÈMES RGPD/LÉGAUX
- Conservation de données après suppression (sans raison d'audit claire)
- Absence de mention de conformité légale

### 4. AMBIGUÏTÉS
- Exigences floues ou imprécises
- Utilisation de termes vagues ("rapidement", "sécurité", etc.)

### 5. EDGE CASES MANQUANTS
- Gestion des cas limites non traitée
- Valeurs vides, null, limites

## Format de réponse obligatoire (JSON):

```json
{
  "resume": {
    "total_problemes": 10,
    "critiques": 3,
    "eleves": 4,
    "moyens": 3,
    "faibles": 0
  },
  "problemes": [
    {
      "id": 1,
      "categorie": "SECURITE|CONTRADICTION|AMBIGUITE|LEGAL|EDGE_CASE",
      "severite": "CRITIQUE|ELEVEE|MOYENNE|FAIBLE",
      "titre": "Titre court du problème",
      "description": "Description détaillée",
      "localisation": "Section où se trouve le problème",
      "recommendation": "Solution recommandée"
    }
  ],
  "extraction": {
    "functionalites": ["liste des fonctionnalités identifiées"],
    "acteurs": ["liste des acteurs"],
    "contraintes": ["liste des contraintes"],
    "interfaces": ["liste des interfaces"],
    "donnees": ["liste des données manipulées"]
  }
}
```

Réponds STRICTEMENT en JSON valide. Pas de texte avant ou après.
"""

user_prompt_template = """Analyse ce cahier des charges et détecte tous les problèmes:

---

{cahier_des_charges}

---

Réponds en JSON strictement. """


class CahierDesChargesAnalyzer:
    def __init__(self, api_token: Optional[str] = None, use_ollama: bool = True):
        self.api_token = api_token
        self.use_ollama = use_ollama
        self.headers = {}
        if api_token:
            self.headers["Authorization"] = f"Bearer {api_token}"
        self.headers["Content-Type"] = "application/json"
    
    def analyze(self, texte: str) -> Dict[str, Any]:
        """Analyse le cahier des charges"""
        
        if self.use_ollama:
            result = self._analyze_ollama(texte)
            if result:
                return result
        
        return self._analyze_huggingface(texte)
    
    def _analyze_ollama(self, texte: str) -> Optional[Dict[str, Any]]:
        """Analyse avec Ollama (local)"""
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt_template.format(cahier_des_charges=texte)}"
        
        payload = {
            "model": "llama3.2",
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 2000
            }
        }
        
        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                texte_reponse = result.get("response", "")
                if texte_reponse:
                    return self._parser_reponse(texte_reponse)
        except Exception as e:
            pass
        
        return None
    
    def _analyze_huggingface(self, texte: str) -> Dict[str, Any]:
        """Fallback vers Hugging Face"""
        full_prompt = f"System: {SYSTEM_PROMPT}\n\nUser: {user_prompt_template.format(cahier_des_charges=texte)}"
        
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 2000,
                "temperature": 0.1,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                HF_API_URL,
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    texte_reponse = result[0].get("generated_text", "")
                    return self._parser_reponse(texte_reponse)
        except Exception as e:
            pass
        
        return self._analyse_regles(texte)
    
    def _parser_reponse(self, texte: str) -> Dict[str, Any]:
        """Parse la réponse JSON du modèle"""
        try:
            debut = texte.find("{")
            fin = texte.rfind("}") + 1
            if debut != -1 and fin != 0:
                json_str = texte[debut:fin]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return self._erreur("Impossible de parser la réponse")
    
    def _erreur(self, message: str) -> Dict[str, Any]:
        return {
            "erreur": message,
            "resume": {
                "total_problemes": 0,
                "critiques": 0,
                "eleves": 0,
                "moyens": 0,
                "faibles": 0
            },
            "problemes": [],
            "extraction": {
                "functionalites": [],
                "acteurs": [],
                "contraintes": [],
                "interfaces": [],
                "donnees": []
            }
        }
    
    def _analyse_regles(self, texte: str) -> Dict[str, Any]:
        """Analyse par règles locales (fallback sans LLM)"""
        probleme_id = 0
        problemes = []
        
        regles = [
            ("en clair|base64", "SECURITE", "CRITIQUE", "Mots de passe stockés de manière non sécurisée", "Hasher les mots de passe avec bcrypt/argon2"),
            ("stockées en clair", "SECURITE", "CRITIQUE", "Données sensibles stockées en clair", "Chiffrer les données sensibles"),
            ("sans authentification", "SECURITE", "CRITIQUE", "API sans authentification", "Implémenter une authentification JWT/OAuth"),
            ("pas de validation", "SECURITE", "CRITIQUE", "Aucune validation des entrées", "Valider toutes les entrées utilisateur"),
            ("sessions.*(jamais|infini)|n'expirent jamais|n'expire jamais", "SECURITE", "ELEVEE", "Sessions sans expiration", "Implémenter une expiration de session"),
            ("prix.*côté client", "SECURITE", "CRITIQUE", "Prix calculé côté client - fraude possible", "Calculer les prix côté serveur uniquement"),
            ("modifier le prix", "SECURITE", "CRITIQUE", "Prix modifiable par le client", "Le prix doit être validé côté serveur"),
            ("pas de vérification de rôle|vérification de rôle", "SECURITE", "ELEVEE", "Pas de vérification de rôle admin", "Vérifier les permissions à chaque requête admin"),
            ("comptes des autres|autrui", "SECURITE", "CRITIQUE", "Modification des comptes d'autrui", "Vérifier que l'utilisateur modifie son propre compte"),
            ("messages détaillés", "SECURITE", "MOYENNE", "Messages d'erreur détaillés (information leakage)", "Utiliser des messages génériques"),
            ("pas de limite.*tentatives|pas de limite de tentatives", "SECURITE", "ELEVEE", "Pas de limite de tentatives de connexion", "Implémenter un verrouillage après N tentatives"),
            ("SQL Injection|sql injection", "EDGE_CASE", "ELEVEE", "Risque d'injection SQL", "Utiliser des requêtes paramétrées"),
            ("XSS|xss", "EDGE_CASE", "ELEVEE", "Risque XSS", "Échapper les entrées/sorties"),
            ("prix négatif|prix.*négatif", "EDGE_CASE", "MOYENNE", "Prix négatif non géré", "Valider les valeurs positives"),
            ("IDOR", "EDGE_CASE", "ELEVEE", "Risque IDOR", "Vérifier les autorisations sur les ressources"),
            ("n'importe quelle longueur", "AMBIGUITE", "FAIBLE", "Mot de passe sans longueur minimale", "Exiger minimum 8 caractères"),
            ("pas besoin d'être validé|pas.*validé", "AMBIGUITE", "MOYENNE", "Email non validé", "Valider l'email par lien de confirmation"),
            ("logs de sécurité|logs.*sécurité", "SECURITE", "MOYENNE", "Pas de logs de sécurité", "Implémenter une journalisation"),
            ("tokens.*pas.*sécurisés", "SECURITE", "ELEVEE", "Tokens non sécurisés", "Utiliser des tokens JWT signés avec expiration"),
            ("plusieurs rôles", "CONTRADICTION", "MOYENNE", "Contradiction sur les rôles", "Clarifier: un utilisateur peut avoir plusieurs rôles ou un seul"),
            ("rgpd|revendues à des partenaires|indéfiniment", "LEGAL", "ELEVEE", "Problème de conformité RGPD", "Respecter le RGPD: droit à l'effacement, pas de revente de données"),
        ]
        
        texte_lower = texte.lower()
        
        for motif, categorie, severite, titre, recommendation in regles:
            import re
            if re.search(motif, texte_lower):
                probleme_id += 1
                problemes.append({
                    "id": probleme_id,
                    "categorie": categorie,
                    "severite": severite,
                    "titre": titre,
                    "description": f"Détecté: {titre}",
                    "localisation": "Analyse automatique",
                    "recommendation": recommendation
                })
        
        extraction = self._extraire_elements(texte)
        
        severites = {"CRITIQUE": 0, "ELEVEE": 0, "MOYENNE": 0, "FAIBLE": 0}
        for p in problemes:
            severites[p["severite"]] += 1
        
        return {
            "resume": {
                "total_problemes": len(problemes),
                "critiques": severites["CRITIQUE"],
                "eleves": severites["ELEVEE"],
                "moyens": severites["MOYENNE"],
                "faibles": severites["FAIBLE"]
            },
            "problemes": problemes,
            "extraction": extraction
        }
    
    def _extraire_elements(self, texte: str) -> Dict[str, List[str]]:
        """Extrait les éléments du cahier des charges"""
        import re
        
        functionalites = []
        acteurs = []
        
        if re.search(r"inscription|s'inscrire|créer.*compte", texte, re.I):
            functionalites.append("Inscription/Création de compte")
        if re.search(r"connexion|se connecter|authentification", texte, re.I):
            functionalites.append("Authentification")
        if re.search(r"produit|catalogue", texte, re.I):
            functionalites.append("Gestion des produits")
        if re.search(r"commande|panier", texte, re.I):
            functionalites.append("Gestion des commandes")
        if re.search(r"paiement|carte|bancaire", texte, re.I):
            functionalites.append("Paiement")
        if re.search(r"admin|gestion.*utilisateur", texte, re.I):
            functionalites.append("Administration")
        
        if re.search(r"utilisateur|client", texte, re.I):
            acteurs.append("Utilisateur/Client")
        if re.search(r'admin|administrateur', texte, re.I):
            acteurs.append("Administrateur")
        
        return {
            "functionalites": functionalites,
            "acteurs": acteurs,
            "contraintes": [],
            "interfaces": [],
            "donnees": []
        }


def analyser_cahier(texte: str, api_token: Optional[str] = None) -> Dict[str, Any]:
    """Fonction principale d'analyse"""
    analyzer = CahierDesChargesAnalyzer(api_token)
    return analyzer.analyze(texte)


if __name__ == "__main__":
    test_texte = """
    Cahier des charges - Système de gestion utilisateurs
    
    3.1 Inscription
    - Email unique
    - Mot de passe min 8 caractères
    
    3.2 Authentification
    - Pas de limite de tentatives
    - Verrouillage après 3 tentatives
    
    5.1 Sécurité
    - Mots de passe stockés en clair
    - Sessions n'expirent jamais
    """
    
    result = analyser_cahier(test_texte)
    print(json.dumps(result, indent=2, ensure_ascii=False))
