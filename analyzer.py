"""
Analyseur de Cahier des Charges
Utilise Ollama (local) ou Hugging Face pour l'analyse
"""

import json
import requests
from typing import Dict, List, Any, Optional

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """Tu es un expert en analyse de cahier des charges de sécurité informatique.

DÉTECTE UNIQUEMENT LES PROBLÈMES, PAS LES FONCTIONNALITÉS!

Catégories de PROBLÈMES (pas de fonctionnalités):
- SECURITY: mots de passe en clair, API sans auth, sessions infinies, pas de validation
- CONTRADICTION: exigences qui se contredisent
- LEGAL: RGPD non respecté, données vendues, pas de droit effacement
- AMBIGUITE: exigences floues
- EDGE_CASE: cas limites non gérés

Pour chaque problème, indique:
- categorie: SECURITY, CONTRADICTION, LEGAL, AMBIGUITE ou EDGE_CASE
- severite: CRITIQUE (pour sécurité), ELEVEE, MOYENNE ou FAIBLE
- titre: description courte du problème
- description: explication détaillée
- recommendation: solution recommandée

NE mets PAS les fonctionnalités dans "problemes"! Elles vont dans "extraction".

Réponds en JSON:
{
  "resume": {"total_problemes": N, "critiques": N, "eleves": N, "moyens": N, "faibles": N},
  "problemes": [{"categorie": "...", "severite": "...", "titre": "...", "description": "...", "recommendation": "..."}],
  "extraction": {"functionalites": [], "acteurs": [], "contraintes": [], "interfaces": [], "donnees": []}
}"""

user_prompt_template = """Analyse ce cahier des charges et détecte les PROBLÈMES (sécurité, contradictions, RGPD, ambiguïtés):

---

{cahier_des_charges}

---

列出 JSON. NE PAS inclure les fonctionnalités comme des problèmes!"""


class CahierDesChargesAnalyzer:
    def __init__(self, api_token: Optional[str] = None, use_ollama: bool = False, use_huggingface: bool = False):
        self.api_token = api_token  # Token sera configuré par l'utilisateur
        self.use_ollama = use_ollama
        self.use_huggingface = use_huggingface
        self.headers = {}
        if self.api_token:
            self.headers["Authorization"] = f"Bearer {self.api_token}"
        self.headers["Content-Type"] = "application/json"
    
    def analyze(self, texte: str) -> Dict[str, Any]:
        """Analyse le cahier des charges"""
        
        if self.use_ollama:
            result = self._analyze_ollama(texte)
            if result:
                return result
        
        if self.use_huggingface:
            result = self._analyze_huggingface(texte)
            if result and result.get("problemes"):
                return result
        
        return self._analyse_regles(texte)
    
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
        """Fallback vers Hugging Face avec huggingface_hub"""
        
        if not HF_AVAILABLE:
            return self._analyse_regles(texte)
        
        full_prompt = f"""{SYSTEM_PROMPT}

Analyse ce cahier des charges et détecte tous les problèmes:

---

{texte}

---

Réponds en JSON strictement."""
        
        try:
            client = InferenceClient(
                "meta-llama/Llama-3.2-1B-Instruct",
                token=self.api_token
            )
            
            response = client.chat_completion(
                messages=[{"role": "user", "content": full_prompt}],
                max_tokens=2000,
                temperature=0.0
            )
            
            texte_reponse = response.choices[0].message.content
            return self._parser_reponse(texte_reponse)
            
        except Exception as e:
            print(f"HF Error: {e}")
        
        return self._analyse_regles(texte)
    
    def _parser_reponse(self, texte: str) -> Dict[str, Any]:
        """Parse la réponse JSON du modèle"""
        if not texte:
            return self._erreur("Réponse vide")
        
        try:
            debut = texte.find("{")
            fin = texte.rfind("}") + 1
            if debut != -1 and fin != 0:
                json_str = texte[debut:fin]
                result = json.loads(json_str)
                
                # Valider la structure
                if "resume" in result and "problemes" in result:
                    # Compter les sévérités si pas fait
                    if result["resume"].get("total_problemes", 0) == 0:
                        severites = {"CRITIQUE": 0, "ELEVEE": 0, "MOYENNE": 0, "FAIBLE": 0}
                        for p in result.get("problemes", []):
                            sev = p.get("severite", "MOYENNE")
                            if sev in severites:
                                severites[sev] += 1
                        result["resume"]["total_problemes"] = len(result.get("problemes", []))
                        result["resume"]["critiques"] = severites["CRITIQUE"]
                        result["resume"]["eleves"] = severites["ELEVEE"]
                        result["resume"]["moyens"] = severites["MOYENNE"]
                        result["resume"]["faibles"] = severites["FAIBLE"]
                    return result
        except (json.JSONDecodeError, Exception) as e:
            print(f"Parser error: {e}")
        
        return self._analyse_regles(texte)
    
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
            ("sans chiffrement|sans chiffrement", "SECURITE", "CRITIQUE", "Données non chiffrées", "Chiffrer les données sensibles"),
            ("accessible à tous|tous les utilisateurs ont accès|accès complet", "SECURITE", "CRITIQUE", "Accès données sans autorisation", "Implémenter un contrôle d'accès"),
            ("api ouverte|api.*sans authentification|partenaires externes", "SECURITE", "ELEVEE", "API ouverte", "Implémenter une authentification"),
            ("sans authentification", "SECURITE", "CRITIQUE", "API sans authentification", "Implémenter une authentification JWT/OAuth"),
            ("pas de validation", "SECURITE", "CRITIQUE", "Aucune validation des entrées", "Valider toutes les entrées utilisateur"),
            ("sessions.*(jamais|infini)|n'expirent jamais|n'expire jamais", "SECURITE", "ELEVEE", "Sessions sans expiration", "Implémenter une expiration de session"),
            ("prix.*côté client", "SECURITE", "CRITIQUE", "Prix calculé côté client - fraude possible", "Calculer les prix côté serveur uniquement"),
            ("modifier le prix", "SECURITE", "CRITIQUE", "Prix modifiable par le client", "Le prix doit être validé côté serveur"),
            ("pas de vérification de rôle|vérification de rôle", "SECURITE", "ELEVEE", "Pas de vérification de rôle admin", "Vérifier les permissions à chaque requête admin"),
            ("comptes des autres|autrui", "SECURITE", "CRITIQUE", "Modification des comptes d'autrui", "Vérifier que l'utilisateur modifie son propre compte"),
            ("messages détaillés", "SECURITE", "MOYENNE", "Messages d'erreur détaillés (information leakage)", "Utiliser des messages génériques"),
            ("pas de limite.*tentatives|pas de limite de tentatives", "SECURITE", "ELEVEE", "Pas de limite de tentatives de connexion", "Implémenter un verrouillage après N tentatives"),
            ("sauvegardes non chiffrées|backup.*non chiffré", "SECURITE", "CRITIQUE", "Sauvegardes non chiffrées", "Chiffrer les sauvegardes"),
            ("SQL Injection|sql injection", "EDGE_CASE", "ELEVEE", "Risque d'injection SQL", "Utiliser des requêtes paramétrées"),
            ("XSS|xss", "EDGE_CASE", "ELEVEE", "Risque XSS", "Échapper les entrées/sorties"),
            ("prix négatif|prix.*négatif", "EDGE_CASE", "MOYENNE", "Prix négatif non géré", "Valider les valeurs positives"),
            ("IDOR", "EDGE_CASE", "ELEVEE", "Risque IDOR", "Vérifier les autorisations sur les ressources"),
            ("numéro.*相同|double.*numéro|même numéro", "EDGE_CASE", "MOYENNE", "Doublon de données non géré", "Implémenter des contraintes d'unicité"),
            ("n'importe quelle longueur|minimum.*[0-9].*caractères", "AMBIGUITE", "FAIBLE", "Mot de passe sans longueur minimale", "Exiger minimum 8 caractères"),
            ("pas besoin d'être validé|pas.*validé", "AMBIGUITE", "MOYENNE", "Email non validé", "Valider l'email par lien de confirmation"),
            ("logs de sécurité|logs.*sécurité", "SECURITE", "MOYENNE", "Pas de logs de sécurité", "Implémenter une journalisation"),
            ("tokens.*pas.*sécurisés", "SECURITE", "ELEVEE", "Tokens non sécurisés", "Utiliser des tokens JWT signés avec expiration"),
            ("plusieurs rôles", "CONTRADICTION", "MOYENNE", "Contradiction sur les rôles", "Clarifier: un utilisateur peut avoir plusieurs rôles ou un seul"),
            ("tout le monde peut|tous peuvent", "CONTRADICTION", "MOYENNE", "Rôles non définis", "Définir des rôles claire"),
            ("secret médical|secret professionnel", "LEGAL", "ELEVEE", "Secret médical non respecté", "Respecter le secret médical"),
            ("pas de droit|effacement|droit à l'effacement", "LEGAL", "ELEVEE", "Droit à l'effacement non respecté", "Implémenter le droit à l'effacement RGPD"),
            ("rgpd|revendues à des partenaires|indéfiniment", "LEGAL", "ELEVEE", "Problème de conformité RGPD", "Respecter le RGPD: droit à l'effacement, pas de revente de données"),
            ("non traité|que se passe-t-il si", "AMBIGUITE", "MOYENNE", "Edge case non traité", "Documenter et gérer les cas limites"),
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
    
    def _detecter_contradictions(self, texte: str) -> List[Dict[str, Any]]:
        """Détection de contradictions sémantiques"""
        contradictions = []
        
        patterns_contradictoires = [
            (["peut avoir plusieurs rôles", "plusieurs rôles"], ["un seul rôle", "un seul role"], "Contradiction sur les rôles: un utilisateur peut avoir plusieurs rôles mais aussi un seul rôle"),
            (["pas de limite de tentatives", "pas de limite"], ["verrouillage après", "verrouillage"], "Contradiction: pas de limite de tentatives mais verrouillage prévu"),
            (["tout le monde peut", "tous peuvent"], ["admin uniquement", "seul admin"], "Contradiction: accès pour tous mais restrictions admin"),
            (["modifiable par le client", "client modifie"], ["côté serveur", "serveur uniquement"], "Contradiction: prix modifiable par client mais calculé serveur"),
            (["données conservées", "conservées"], ["effacement", "supprimées"], "Contradiction: données conservées pour audit mais droit à l'effacement"),
            (["accessible à tous", "api ouverte"], ["authentification", "protégé"], "Contradiction: API ouverte mais authentification requise"),
        ]
        
        texte_lower = texte.lower()
        
        for pattern_pos, pattern_neg, description in patterns_contradictoires:
            pos_found = any(p in texte_lower for p in pattern_pos)
            neg_found = any(p in texte_lower for p in pattern_neg)
            
            if pos_found and neg_found:
                contradictions.append({
                    "id": len(contradictions) + 1,
                    "categorie": "CONTRADICTION",
                    "severite": "ELEVEE",
                    "titre": "Contradiction détectée",
                    "description": description,
                    "localisation": "Analyse sémantique",
                    "recommendation": "Clarifier l'exigence contradictoire"
                })
        
        return contradictions
    
    def _analyser_completude(self, texte: str) -> Dict[str, Any]:
        """Analyse la complétude du cahier des charges"""
        sections_attendues = {
            "description": ["description", "présentation", "contexte"],
            "objectifs": ["objectifs", "but", "finalité"],
            "fonctionnalites": ["fonctionnalité", "exigence", "feature"],
            "acteurs": ["utilisateur", "acteur", "rôle", "personne"],
            "contraintes": ["contrainte", "limitation", "prérequis"],
            "securite": ["sécurité", "authentification", "accès"],
            "technique": ["technique", "technologie", "stack", "architecture"],
            "delai": ["délai", "livrable", "échéance"]
        }
        
        texte_lower = texte.lower()
        sections_trouvees = {}
        
        for section, keywords in sections_attendues.items():
            sections_trouvees[section] = any(kw in texte_lower for kw in keywords)
        
        total = len(sections_attendues)
        presente = sum(1 for v in sections_trouvees.values() if v)
        score = (presente / total) * 100
        
        problemes = []
        
        if score < 50:
            problemes.append({
                "id": 1,
                "categorie": "AMBIGUITE",
                "severite": "ELEVEE",
                "titre": "Cahier des charges incomplet",
                "description": f" seulement {presente}/{total} sections essentielles présentes",
                "localisation": "Analyse de complétude",
                "recommendation": "Ajouter les sections manquantes: " + ", ".join([s for s, ok in sections_trouvees.items() if not ok])
            })
        
        for section, presente in sections_trouvees.items():
            if not presente:
                problemes.append({
                    "id": len(problemes) + 1,
                    "categorie": "AMBIGUITE",
                    "severite": "FAIBLE",
                    "titre": f"Section '{section}' manquante",
                    "description": f"La section '{section}' n'a pas été détectée",
                    "localisation": "Analyse de complétude",
                    "recommendation": f"Ajouter une section '{section}'"
                })
        
        return {
            "score_completude": score,
            "sections": sections_trouvees,
            "problemes": problemes
        }
    
    def _analyser_qualite(self, texte: str) -> Dict[str, Any]:
        """Analyse la qualité globale du document"""
        lignes = [l.strip() for l in texte.split("\n") if l.strip()]
        
        score = 100
        problemes = []
        
        if len(lignes) < 10:
            score -= 20
            problemes.append({"type": "longueur", "severite": "ELEVEE", "message": "Document trop court"})
        
        mots_techniques = ["api", "jwt", "oauth", "sql", "chiffrement", "hash", "token", "session", "rôle", "permission"]
        texte_lower = texte.lower()
        technique_count = sum(1 for mot in mots_techniques if mot in texte_lower)
        
        if technique_count < 3:
            score -= 15
            problemes.append({"type": "technique", "severite": "MOYENNE", "message": "Pas assez de détails techniques"})
        
        if "?" in texte:
            score -= 10
            problemes.append({"type": "ambiguite", "severite": "MOYENNE", "message": "Présence de questions non résolues"})
        
        return {
            "score_qualite": max(0, score),
            "nb_lignes": len(lignes),
            "mots_techniques": technique_count,
            "problemes": problemes
        }
    
    def _valider_references_croisees(self, texte: str, extractions: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Valide les références entre sections"""
        problemes = []
        
        actors = extractions.get("acteurs", [])
        functionalites = extractions.get("functionalites", [])
        
        if actors and not functionalites:
            problemes.append({
                "id": 1,
                "categorie": "AMBIGUITE",
                "severite": "MOYENNE",
                "titre": "Acteurs définis sans fonctionnalités",
                "description": "Des acteurs sont mentionnés mais aucune fonctionnalité n'est associée",
                "localisation": "Validation croisée",
                "recommendation": "Associer des fonctionnalités à chaque acteur"
            })
        
        texte_lower = texte.lower()
        
        if "données" in texte_lower or "données" in texte_lower:
            if "sécurité" not in texte_lower and "chiffrement" not in texte_lower:
                problemes.append({
                    "id": len(problemes) + 1,
                    "categorie": "SECURITE",
                    "severite": "ELEVEE",
                    "titre": "Données mentionnées sans sécurité",
                    "description": "Le document mentionne des données mais pas leur protection",
                    "localisation": "Validation croisée",
                    "recommendation": "Ajouter des exigences de sécurité pour les données"
                })
        
        if "paiement" in texte_lower or "carte" in texte_lower:
            if "pci" not in texte_lower and "conformité" not in texte_lower and "certification" not in texte_lower:
                problemes.append({
                    "id": len(problemes) + 1,
                    "categorie": "LEGAL",
                    "severite": "ELEVEE",
                    "titre": "Paiement sans conformité PCI",
                    "description": "Le document mentionne des paiements sans conformité PCI DSS",
                    "localisation": "Validation croisée",
                    "recommendation": "Ajouter les exigences de conformité PCI DSS"
                })
        
        return problemes
    
    def analyser_avance(self, texte: str) -> Dict[str, Any]:
        """Analyse avancée complète avec toutes les méthodes"""
        contradictions = self._detecter_contradictions(texte)
        completude = self._analyser_completude(texte)
        qualite = self._analyser_qualite(texte)
        extractions = self._extraire_elements(texte)
        references = self._valider_references_croisees(texte, extractions)
        
        all_problemes = []
        
        all_problemes.extend(contradictions)
        all_problemes.extend(completude.get("problemes", []))
        all_problemes.extend(references)
        
        return {
            "resume": {
                "total_problemes": len(all_problemes),
                "contradictions": len(contradictions),
                "completude_score": completude.get("score_completude", 0),
                "qualite_score": qualite.get("score_qualite", 0),
                "critiques": len([p for p in all_problemes if p.get("severite") == "CRITIQUE"]),
                "eleves": len([p for p in all_problemes if p.get("severite") == "ELEVEE"]),
                "moyennes": len([p for p in all_problemes if p.get("severite") == "MOYENNE"]),
                "faibles": len([p for p in all_problemes if p.get("severite") == "FAIBLE"]),
            },
            "problemes": all_problemes,
            "extraction": {
                **extractions,
                "completude": completude,
                "qualite": qualite
            },
            "analyse_avancee": {
                "contradictions": contradictions,
                "completude": completude,
                "qualite": qualite,
                "references": references
            }
        }


def analyser_cahier(texte: str, api_token: Optional[str] = None, use_ollama: bool = False, use_huggingface: bool = False, analyse_avancee: bool = False) -> Dict[str, Any]:
    """Fonction principale d'analyse"""
    analyzer = CahierDesChargesAnalyzer(api_token, use_ollama, use_huggingface)
    
    if analyse_avancee:
        return analyzer.analyser_avance(texte)
    
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
