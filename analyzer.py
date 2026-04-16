"""
Analyseur de Cahier des Charges
Utilise Ollama (local) pour extraction des metadonnees uniquement
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

EXTRACTION_SYSTEM_PROMPT = """Tu es un assistant expert en extraction d'informations de cahier des charges.
Extrait uniquement les metadonnees du document. Ne detecte PAS les problemes de securite.
Reponds uniquement en JSON."""

EXTRACTION_USER_PROMPT = """Extrait les informations de ce cahier des charges:

{cahier_des_charges}

JSON:"""


class CahierDesChargesAnalyzer:
    def __init__(self, api_token: Optional[str] = None, use_ollama: bool = False, use_huggingface: bool = False, use_groq: bool = False, groq_api_key: Optional[str] = None):
        self.api_token = api_token
        self.use_ollama = use_ollama
        self.use_huggingface = use_huggingface
        self.use_groq = use_groq
        self.groq_api_key = groq_api_key
    
    def analyze(self, texte: str) -> Dict[str, Any]:
        """Analyse le cahier des charges - extraction uniquement"""
        
        if self.use_groq:
            extraction = self._extraire_metadonnees_groq(texte)
            if extraction:
                return {
                    "extraction": extraction,
                    "problemes": [],
                    "resume": {"total_problemes": 0, "critiques": 0, "eleves": 0, "moyens": 0, "faibles": 0}
                }
        
        if self.use_ollama:
            extraction = self._extraire_metadonnees_ollama(texte)
            if extraction:
                return {
                    "extraction": extraction,
                    "problemes": [],
                    "resume": {"total_problemes": 0, "critiques": 0, "eleves": 0, "moyens": 0, "faibles": 0}
                }
        
        if self.use_huggingface:
            extraction = self._extraire_metadonnees_huggingface(texte)
            if extraction:
                return {
                    "extraction": extraction,
                    "problemes": [],
                    "resume": {"total_problemes": 0, "critiques": 0, "eleves": 0, "moyens": 0, "faibles": 0}
                }
        
        # Fallback: extraction locale avec regex
        extraction = self._extraire_elements_cps(texte)
        if extraction:
            problemes = self._analyser_cps_elements(texte)
            severites = {"CRITIQUE": 0, "ELEVEE": 0, "MOYENNE": 0, "FAIBLE": 0}
            for p in problemes:
                severites[p["severite"]] += 1
            return {
                "extraction": extraction,
                "problemes": problemes,
                "resume": {
                    "total_problemes": len(problemes),
                    "critiques": severites["CRITIQUE"],
                    "eleves": severites["ELEVEE"],
                    "moyens": severites["MOYENNE"],
                    "faibles": severites["FAIBLE"]
                }
            }
        
        return self._erreur("Extraction failed")
    
    def _extraire_metadonnees_ollama(self, texte: str) -> Optional[Dict[str, Any]]:
        """Extrait les metadonnees avec Ollama"""
        full_prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\n{EXTRACTION_USER_PROMPT.format(cahier_des_charges=texte)}"
        
        print(f"[DEBUG] Extraction Ollama - prompt length: {len(full_prompt)}")
        
        payload = {
            "model": "llama3.2",
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4000
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
                    return self._parser_extraction(texte_reponse)
        except Exception as e:
            print(f"Ollama extraction error: {e}")
        
        return None
    
    def _extraire_metadonnees_huggingface(self, texte: str) -> Optional[Dict[str, Any]]:
        """Extrait les metadonnees avec Hugging Face"""
        if not HF_AVAILABLE:
            return None
        
        full_prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\n{EXTRACTION_USER_PROMPT.format(cahier_des_charges=texte)}"
        
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
            return self._parser_extraction(texte_reponse)
            
        except Exception as e:
            print(f"HF extraction error: {e}")
        
        return None
    
    def _extraire_metadonnees_groq(self, texte: str) -> Optional[Dict[str, Any]]:
        """Extrait les metadonnees avec Groq API"""
        if not self.groq_api_key:
            return None
        
        full_prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\n{EXTRACTION_USER_PROMPT.format(cahier_des_charges=texte)}"
        
        try:
            import httpx
            
            response = httpx.Client(timeout=120).post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": full_prompt}
                    ],
                    "temperature": 0.3,
                },
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                texte_reponse = result["choices"][0]["message"]["content"]
                if texte_reponse:
                    return self._parser_extraction(texte_reponse)
        except Exception as e:
            print(f"Groq extraction error: {e}")
        
        return None
    
    def _parser_extraction(self, texte: str) -> Optional[Dict[str, Any]]:
        """Parse la reponse JSON d'extraction"""
        if not texte:
            return None
        
        try:
            debut = texte.find("{")
            fin = texte.rfind("}") + 1
            if debut != -1 and fin != 0:
                json_str = texte[debut:fin]
                result = json.loads(json_str)
                
                if "extraction" in result:
                    return result["extraction"]
                return result
        except (json.JSONDecodeError, Exception) as e:
            print(f"Parser extraction error: {e}")
        
        return None
    
    def _parser_reponse(self, texte: str) -> Dict[str, Any]:
        """Parse la reponse JSON du modele (legacy)"""
        if not texte:
            return self._erreur("Reponse vide")
        
        try:
            debut = texte.find("{")
            fin = texte.rfind("}") + 1
            if debut != -1 and fin != 0:
                json_str = texte[debut:fin]
                result = json.loads(json_str)
                
                if "resume" in result and "problemes" in result:
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
            print(f"[DEBUG] API Token: {self.api_token[:20] if self.api_token else 'None'}...")
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
                "metadonnees": {"nom_client": None, "objet": None, "objectifs": [], "orientations_technologiques": []},
                "contraintes_projet": {"date_limite_soumission": None, "budget": None, "caution_provisoire": None, "delai_execution": None},
                "dossier_reponse": {"administratif": [], "technique": [], "financier": []},
                "references": [], "exigences": [], "modalites_paiement": []
            }
        }
    
    def _analyse_regles(self, texte: str) -> Dict[str, Any]:
        """Analyse par règles locales (fallback sans LLM)"""
        probleme_id = 0
        problemes = []
        
        # Analy CPS - Analyse des éléments du cahier des charges
        problemes.extend(self._analyser_cps_elements(texte))
        probleme_id = len(problemes)
        
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
        
        extraction = self._extraire_elements_cps(texte)
        
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
    
    def _analyser_cps_elements(self, texte: str) -> List[Dict[str, Any]]:
        """Analyse les éléments spécifiques du cahier des charges"""
        import re
        problemes = []
        probleme_id = 0
        
        elements_cps = {
            "Nom client": {
                "patterns": [r"nom du client", r"client\s*:", r"société", r"raison sociale", r"entreprise\s*:", r"bénéficiaire", r"atlas digital", r"🏢"],
                "categorie": "COMPLETUDE",
                "severite": "ELEVEE",
                "titre": "Nom client manquant",
                "recommendation": "Ajouter le nom du client ou de l'entreprise"
            },
            "Objet": {
                "patterns": [r"objet\s*:", r"objet du marché", r"objet du contrat", r"description du projet", r"contexte", r"présentation", r"📌"],
                "categorie": "COMPLETUDE",
                "severite": "CRITIQUE",
                "titre": "Objet manquant",
                "recommendation": "Définir clairement l'objet du marché"
            },
            "Objectifs du projet": {
                "patterns": [r"objectifs?\s*:", r"but du projet", r"finalité", r"résultats attendus", r"objectifs.*projet", r"🎯"],
                "categorie": "COMPLETUDE",
                "severite": "ELEVEE",
                "titre": "Objectifs du projet non définis",
                "recommendation": "Détailler les objectifs du projet"
            },
            "Orientations technologiques": {
                "patterns": [r"technolog", r"stack", r"architecture", r"environ(nement)?\s*(technique|dev|prod)", r"outils", r"langage", r"framework", r"backend", r"frontend", r"base de données", r"🧭"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Orientations technologiques non définies",
                "recommendation": "Préciser les orientations technologiques"
            },
            "Date limite de soumission": {
                "patterns": [r"date limite", r"date.*soumission", r"remise.*offre", r"dépot.*dossier", r"échéance", r"fin de validité", r"📅"],
                "categorie": "COMPLETUDE",
                "severite": "CRITIQUE",
                "titre": "Date limite de soumission manquante",
                "recommendation": "Indiquer la date limite de soumission"
            },
            "Budget": {
                "patterns": [r"budget", r"prix", r"coût", r"montant", r"tarif", r"(dh|mad|€|eur|dollars?)\s*\d", r"\d+\s*(dh|mad|€|eur)", r"💰"],
                "categorie": "COMPLETUDE",
                "severite": "CRITIQUE",
                "titre": "Budget non défini",
                "recommendation": "Préciser le budget alloué"
            },
            "Caution provisoire": {
                "patterns": [r"caution", r"garantie", r"provision", r"warrantage", r"bloqué", r"garantie.*banque", r"🔒"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Caution provisoire non définie",
                "recommendation": "Indiquer le montant de la caution provisoire"
            },
            "Délai d'exécution": {
                "patterns": [r"délai", r"durée", r"durée.*exécution", r"temps.*réalisation", r"livraison", r"délai.*livraison", r"⏱️"],
                "categorie": "COMPLETUDE",
                "severite": "CRITIQUE",
                "titre": "Délai d'exécution non défini",
                "recommendation": "Préciser le délai d'exécution"
            },
            "Références": {
                "patterns": [r"référence", r"portfolio", r"réalisation", r"projet.*réalisé", r"expérience", r"certificat", r"attestation", r"📚"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Références non mentionnées",
                "recommendation": "Ajouter les références et réalisations"
            },
            "Exigences": {
                "patterns": [r"exigence", r"contrainte", r"spécification", r"condition", r"critère", r"besoin", r"⚙️"],
                "categorie": "QUALITE",
                "severite": "ELEVEE",
                "titre": "Exigences non définies",
                "recommendation": "Détailler les exigences techniques et fonctionnelles"
            },
            "Modalité de paiement": {
                "patterns": [r"paiement", r"règlement", r"avance", r"acompte", r"traite", r"échéancier", r"facturation", r"💳"],
                "categorie": "COMPLETUDE",
                "severite": "ELEVEE",
                "titre": "Modalités de paiement non définies",
                "recommendation": "Préciser les modalités de paiement"
            },
            "Dossier administratif": {
                "patterns": [r"pièce.?administrative", r"document.?administratif", r"rc|registre.*commerce", r"attestation.*cnss", r"carte.*identit", r"administratif", r"📑"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Dossier administratif non détaillé",
                "recommendation": "Lister les pièces administratives requises"
            },
            "Dossier technique": {
                "patterns": [r"dossier technique", r"offre technique", r"méthodologie", r"planning", r"équipe", r"compétence", r"technique", r"🛠️"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Dossier technique non détaillé",
                "recommendation": "Détailler les exigences du dossier technique"
            },
            "Dossier financier": {
                "patterns": [r"dossier financier", r"offre financière", r"devis", r"bordereau.*prix", r"pom", r"montant.*global", r"financier", r"💵"],
                "categorie": "QUALITE",
                "severite": "MOYENNE",
                "titre": "Dossier financier non détaillé",
                "recommendation": "Détailler les exigences du dossier financier"
            }
        }
        
        texte_lower = texte.lower()
        
        for element_name, config in elements_cps.items():
            found = False
            for pattern in config["patterns"]:
                if re.search(pattern, texte_lower):
                    found = True
                    break
            
            if not found:
                probleme_id += 1
                problemes.append({
                    "id": probleme_id,
                    "categorie": config["categorie"],
                    "severite": config["severite"],
                    "titre": config["titre"],
                    "description": f"L'élément '{element_name}' n'a pas été détecté dans le document",
                    "localisation": f"Élément CPS: {element_name}",
                    "recommendation": config["recommendation"]
                })
        
        return problemes
    
    def _extraire_elements_cps(self, texte: str) -> Dict[str, Any]:
        """Extrait les éléments CPS du cahier des charges.
        Uses DocumentExtractor.extract_cps_metadata() for core metadata,
        with strict guards for list fields to avoid garbled text."""
        import re
        from src.services.document_extractor import DocumentExtractor

        # Use our improved regex metadata extraction
        doc_extractor = DocumentExtractor()
        meta_result = doc_extractor.extract_cps_metadata(texte)

        # Handle both flat format and nested format from extract_cps_metadata
        # Flat: {nom_client: ..., contraintes_projet: {...}}
        # Nested: {metadonnees: {...}, contraintes_projet: {...}}
        if "metadonnees" in meta_result:
            meta = meta_result.get("metadonnees", {})
        else:
            meta = {
                "nom_client": meta_result.get("nom_client"),
                "objet": meta_result.get("objet"),
                "objectifs": meta_result.get("objectifs", []),
                "orientations_technologiques": meta_result.get("orientations_technologiques", []),
            }
        
        contraintes = meta_result.get("contraintes_projet", {}) or {}

        # Start with the metadata extraction result
        extraction = {
            "metadonnees": meta,
            "contraintes_projet": contraintes,
            "dossier_reponse": {"administratif": [], "technique": [], "financier": []},
            "references": [],
            "exigences": [],
            "modalites_paiement": [],
        }

        # Helper: filter out garbled/legal-reference noise from list items
        def _clean_items(raw_items: list, max_len: int = 150) -> list:
            cleaned = []
            noise_patterns = [
                r"décret", r"loi\s+n[°\s]", r"dou\s+al", r"ramadan", r"rabii",
                r"hija", r"article\s+\d+", r"EMO", r"relative\s+au\s+contrôle",
                r"formant\s+code\s+de\s+commerce", r"prévalent", r"se\s+dérober",
                r"avances\s+en\s+matière", r"contrôle\s+financier",
            ]
            for item in raw_items:
                item = item.strip()
                if not item or len(item) > max_len:
                    continue
                if re.search('|'.join(noise_patterns), item, re.I):
                    continue
                cleaned.append(item)
            return cleaned

        # Dossier de réponse - Administrative (strict: look for numbered pieces)
        admin_match = re.search(
            r"(?:dossier\s*(?:de\s*)?réponse\s*(?:administratif)?)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:technique|financier|dossier|$))",
            texte, re.I | re.DOTALL
        )
        if admin_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{5,150})", admin_match.group(1))
            extraction["dossier_reponse"]["administratif"] = _clean_items(items)

        # Dossier de réponse - Technique
        tech_match = re.search(
            r"(?:offre\s*(?:technique)?|dossier\s*technique|mémoire\s*technique)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:financier|$))",
            texte, re.I | re.DOTALL
        )
        if tech_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{5,150})", tech_match.group(1))
            extraction["dossier_reponse"]["technique"] = _clean_items(items)

        # Dossier de réponse - Financier
        fin_match = re.search(
            r"(?:offre\s*financière|dossier\s*financier|devis|bordereau\s*(?:des\s*)?prix)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:article|conditions|$))",
            texte, re.I | re.DOTALL
        )
        if fin_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{5,150})", fin_match.group(1))
            extraction["dossier_reponse"]["financier"] = _clean_items(items)

        # References - look for actual law/decree references, not random text
        ref_match = re.search(
            r"(?:références?(?:\s*bibliographiques?)?|textes\s*(?:de\s*)?référence|références\s*législatives?)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:exigences|modalités|dossier|$))",
            texte, re.I | re.DOTALL
        )
        if ref_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{10,200})", ref_match.group(1))
            extraction["references"] = _clean_items(items, max_len=200)

        # Exigences - look for explicit requirement sections
        exi_match = re.search(
            r"(?:exigences?(?:\s*(?:fonctionnelles?|techniques?|de\s*sécurité|spécifiques))?|prescriptions\s*(?:spéciales?|particulières)?)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:modalités|paiement|dossier|article\s+\d+|$))",
            texte, re.I | re.DOTALL
        )
        if exi_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{10,200})", exi_match.group(1))
            extraction["exigences"] = _clean_items(items, max_len=200)

        # Modalités de paiement - look for actual payment terms
        pai_match = re.search(
            r"(?:modalités?\s*(?:de\s*)?paiement|conditions?\s*(?:de\s*)?paiement|échéancier\s*(?:de\s*)?paiement)\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:dossier|article\s+\d+|conditions?\s+(?:de|générales)|$))",
            texte, re.I | re.DOTALL
        )
        if pai_match:
            items = re.findall(r"(?:[-•·]|\d+[\.)])\s*([^\n]{10,200})", pai_match.group(1))
            extraction["modalites_paiement"] = _clean_items(items, max_len=200)

        return extraction
    
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


def analyser_cahier(texte: str, api_token: Optional[str] = None, use_ollama: bool = False, use_huggingface: bool = False, use_groq: bool = False, groq_api_key: Optional[str] = None, analyse_avancee: bool = False) -> Dict[str, Any]:
    """Fonction principale d'analyse"""
    analyzer = CahierDesChargesAnalyzer(api_token, use_ollama, use_huggingface, use_groq, groq_api_key)
    
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
