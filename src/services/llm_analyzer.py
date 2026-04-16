import json
import time
import re
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from src.core.config import settings
from src.core.prompts import (
    SYSTEM_PROMPT,
    build_extraction_prompt,
    build_analysis_prompt,
    build_recommendation_prompt,
)


def validate_extraction_schema(data: dict | None) -> dict:
    """Validate and fix extraction JSON against expected schema.
    Returns the validated/fixed data with all required fields present."""
    
    # Key mapping: alternative names -> expected names
    key_mapping = {
        "maître_ouvre": "nom_client",
        "maitre_ouvre": "nom_client",
        "maitre_d_ouvrage": "nom_client",
        "titre": "objet",
        "consistance_des_prestations": "objet",
        "appel_d_offres": "objet",
        "délai_d_exécution": "delai_execution",
        "delai_execution": "delai_execution",
        "duree": "delai_execution",
        "cautionnement_provisoire": "caution_provisoire",
        "caution": "caution_provisoire",
        "cautionnement_définitif": "caution_provisoire",
        "date_limite": "date_limite_soumission",
        "date": "date_limite_soumission",
        "montant": "budget",
        "prix": "budget",
        "pièces_constitutives_du_marché": "references",
        "textes_généraux": "references",
        "exigences": "exigences",
        "conditions": "exigences",
        "pénalités_pour_retard": "exigences",
        "retenue_de_garantie": "modalites_paiement",
        "garantie": "modalites_paiement",
        "orientations_technologiques": "orientations_technologiques",
    }
    
    expected_structure = {
        "extraction": {
            "metadonnees": {
                "nom_client": (str, type(None)),
                "objet": (str, type(None)),
                "objectifs": (list,),
                "orientations_technologiques": (list,),
            },
            "contraintes_projet": {
                "date_limite_soumission": (str, type(None)),
                "budget": (str, type(None)),
                "caution_provisoire": (str, type(None)),
                "delai_execution": (str, type(None)),
            },
            "dossier_reponse": {
                "administratif": (list,),
                "technique": (list,),
                "financier": (list,),
            },
            "references": (list,),
            "exigences": (list,),
            "modalites_paiement": (list,),
        }
    }

    if not data or not isinstance(data, dict):
        return {"extraction": _default_extraction()}

    extraction = data.get("extraction", data)  # Handle both wrapped and unwrapped

    if not isinstance(extraction, dict):
        return {"extraction": _default_extraction()}
    
    # First, collect alternative key values BEFORE validation
    alt_values = {}
    for alt_key, std_key in key_mapping.items():
        if alt_key in extraction:
            value = extraction.get(alt_key)
            if value is not None:
                alt_values[std_key] = value

    # Validate metadonnees
    meta = extraction.get("metadonnees", {})
    if not isinstance(meta, dict):
        meta = {}
    validated_meta = {}
    for key, expected_types in expected_structure["extraction"]["metadonnees"].items():
        value = meta.get(key)
        if isinstance(value, expected_types):
            validated_meta[key] = value
        else:
            validated_meta[key] = [] if isinstance(expected_types, tuple) and list in expected_types else None
    extraction["metadonnees"] = validated_meta

    # Validate contraintes_projet
    contraintes = extraction.get("contraintes_projet", {})
    if not isinstance(contraintes, dict):
        contraintes = {}
    validated_contraintes = {}
    for key, expected_types in expected_structure["extraction"]["contraintes_projet"].items():
        value = contraintes.get(key)
        if isinstance(value, expected_types):
            validated_contraintes[key] = value
        else:
            validated_contraintes[key] = None
    extraction["contraintes_projet"] = validated_contraintes

    # Validate dossier_reponse
    dossier = extraction.get("dossier_reponse", {})
    if not isinstance(dossier, dict):
        dossier = {}
    validated_dossier = {}
    for key, expected_types in expected_structure["extraction"]["dossier_reponse"].items():
        value = dossier.get(key)
        if isinstance(value, expected_types):
            # Filter out entries that are too long (garbled text) or not strings
            cleaned = []
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and len(item.strip()) < 300:
                        cleaned.append(item.strip())
            validated_dossier[key] = cleaned
        else:
            validated_dossier[key] = []
    extraction["dossier_reponse"] = validated_dossier

    # Validate list fields
    for list_key in ["references", "exigences", "modalites_paiement"]:
        value = extraction.get(list_key, [])
        if not isinstance(value, list):
            extraction[list_key] = []
        else:
            # Clean: keep only strings under 300 chars
            extraction[list_key] = [
                item.strip() for item in value
                if isinstance(item, str) and len(item.strip()) < 300
            ]
    
    # Fill in missing values from alternative keys
    if alt_values:
        meta = extraction.get("metadonnees", {})
        contraintes = extraction.get("contraintes_projet", {})
        
        for key, value in alt_values.items():
            if key in expected_structure["extraction"]["metadonnees"]:
                if not meta.get(key):
                    meta[key] = value
            elif key in expected_structure["extraction"]["contraintes_projet"]:
                if not contraintes.get(key):
                    contraintes[key] = value
        
        extraction["metadonnees"] = meta
        extraction["contraintes_projet"] = contraintes

    return {"extraction": extraction}


def _default_extraction() -> dict:
    return {
        "metadonnees": {
            "nom_client": None,
            "objet": None,
            "objectifs": [],
            "orientations_technologiques": [],
        },
        "contraintes_projet": {
            "date_limite_soumission": None,
            "budget": None,
            "caution_provisoire": None,
            "delai_execution": None,
        },
        "dossier_reponse": {
            "administratif": [],
            "technique": [],
            "financier": [],
        },
        "references": [],
        "exigences": [],
        "modalites_paiement": [],
    }


def merge_extraction_with_fallback(llm_result: dict, regex_result: dict) -> dict:
    """Merge LLM extraction with regex fallback - use regex values for None/empty LLM fields."""
    extraction = llm_result.get("extraction", {})
    meta = extraction.get("metadonnees", {})
    contraintes = extraction.get("contraintes_projet", {})

    regex_meta = regex_result.get("metadonnees", {})
    regex_contraintes = regex_result.get("contraintes_projet", {})

    # Fill in None/empty LLM fields with regex values
    for key in ["nom_client", "objet"]:
        if not meta.get(key) and regex_meta.get(key):
            meta[key] = regex_meta[key]

    for key in ["objectifs", "orientations_technologiques"]:
        if not meta.get(key) or (isinstance(meta.get(key), list) and len(meta[key]) == 0):
            if regex_meta.get(key):
                meta[key] = regex_meta[key]

    for key in ["date_limite_soumission", "budget", "caution_provisoire", "delai_execution"]:
        if not contraintes.get(key) and regex_contraintes.get(key):
            contraintes[key] = regex_contraintes[key]

    return {"extraction": extraction}


@dataclass
class LLMResponse:
    content: str
    model: str
    duration_ms: int
    raw_response: dict


class QwenLocalAnalyzer:
    """Qwen2.5-0.5B local analyzer using HuggingFace transformers"""
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        max_new_tokens: int = 150,
        temperature: float = 0.1,
        timeout: int = 25,
    ):
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.timeout = timeout
        self.model = None
        self.tokenizer = None
        self._loaded = False
    
    def load(self):
        """Load model from HuggingFace cache"""
        if self._loaded:
            return
        
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            print(f"Loading {self.model_name} from cache...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="cpu",
                trust_remote_code=True
            )
            self._loaded = True
            print("Qwen model loaded successfully!")
        except Exception as e:
            print(f"Failed to load Qwen model: {e}")
            raise
    
    def _call(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Call Qwen model"""
        if not self._loaded:
            self.load()
        
        system = system_prompt or "Tu es un assistant expert en analyse de cahier des charges."
        
        start_time = time.time()
        
        full_prompt = f"{system}\n\n{prompt}"
        
        try:
            inputs = self.tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=1024)
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response[len(full_prompt):].strip()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return LLMResponse(
                content=response,
                model=self.model_name,
                duration_ms=duration_ms,
                raw_response={"response": response}
            )
        except Exception as e:
            raise RuntimeError(f"Qwen inference error: {e}")
    
    def validate_results(self, rule_results: dict, original_text: str) -> List[Dict]:
        """Qwen valide et corrige les résultats Rule-Based"""
        issues = rule_results.get("issues", [])
        
        if not issues:
            return []
        
        prompt = f"""Tu es un expert en sécurité informatique. Vérifie et corrige les problèmes détectés par un analyseur automatique.

Résultats de l'analyse Rule-Based:
{json.dumps(issues, indent=2, ensure_ascii=False)}

Cahier des charges original:
{original_text[:2000]}

Pour chaque problème, analyse:
1. Est-ce une vraie détection ou un faux positif?
2. La sévérité est-elle appropriée?
3. Y a-t-il des corrections à apporter?

Réponds en JSON strict avec ce format:
[
  {{
    "original_id": "ID du problème original",
    "valid": true/false,
    "corrected_severity": "critical/high/medium/low" (si différent),
    "confidence": 0.0-1.0,
    "comment": "explication courte"
  }}
]"""
        
        response = self._call(prompt)
        return self._parse_json_list(response.content)
    
    def find_missing_issues(self, original_text: str, rule_results: dict) -> List[Dict]:
        """Qwen découvre les problèmes manqués par Rule-Based"""
        existing_issues = set()
        for issue in rule_results.get("issues", []):
            existing_issues.add(issue.get("issue", "").lower())
        
        text_lower = original_text.lower()
        
        new_issues = []
        
        problem_patterns = {
            "données.*bancaires|carte.*bancaires|paiement": {
                "issue": "Données de paiement non sécurisées",
                "category": "security",
                "severity": "critical",
                "description": "Informations de carte bancaire non chiffrées"
            },
            "session.*jamais|expiration": {
                "issue": "Sessions sans expiration",
                "category": "security", 
                "severity": "high",
                "description": "Les sessions n'expirent jamais - risque de hijacking"
            },
            "côté client|prix.*client|modifi.*prix": {
                "issue": "Prix calculé côté client",
                "category": "security",
                "severity": "critical",
                "description": "Prix modifiable par l'utilisateur - fraude potentielle"
            },
            "comptes.*autrui|autrui.*modif": {
                "issue": "Modification des comptes d'autrui",
                "category": "security",
                "severity": "critical",
                "description": "Un utilisateur peut modifier les données d'autres utilisateurs"
            },
            "pas.*validation|aucun.*validation|validation": {
                "issue": "Validation des entrées manquante",
                "category": "security",
                "severity": "high",
                "description": "Aucune validation des entrées utilisateur"
            },
            "logs|journalisation|traces": {
                "issue": "Pas de logs de sécurité",
                "category": "security",
                "severity": "medium",
                "description": "Pas de journalisation des événements de sécurité"
            },
            "tokens?|jwt": {
                "issue": "Tokens non sécurisés",
                "category": "security",
                "severity": "high",
                "description": "Les tokens d'authentification ne sont pas sécurisés"
            },
            "role.*admin|vérification.*rôle|permission": {
                "issue": "Pas de vérification de rôle",
                "category": "security",
                "severity": "high",
                "description": "Les actions admin ne vérifient pas les permissions"
            }
        }
        
        for pattern, info in problem_patterns.items():
            import re
            if re.search(pattern, text_lower):
                if info["issue"].lower() not in existing_issues:
                    new_issues.append({
                        "issue": info["issue"],
                        "description": info["description"],
                        "category": info["category"],
                        "severity": info["severity"],
                        "location": "Analyse contextuelle",
                        "confidence": 0.85
                    })
                    existing_issues.add(info["issue"].lower())
        
        return new_issues
    
    def _parse_json_list(self, content: str) -> List[Dict]:
        """Parse JSON list from LLM response"""
        content = content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end != 0:
                try:
                    return json.loads(content[start:end])
                except:
                    pass
            return []
    
    def is_loaded(self) -> bool:
        return self._loaded
    
    def close(self):
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            self._loaded = False


class UnslothAnalyzer:
    def __init__(
        self,
        model_name: Optional[str] = None,
        max_seq_length: Optional[int] = None,
        temperature: Optional[float] = None,
    ):
        self.model_name = model_name or settings.QWEN_MODEL_NAME
        self.max_seq_length = max_seq_length or settings.QWEN_MAX_SEQ_LENGTH
        self.temperature = temperature or settings.QWEN_TEMPERATURE
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            from unsloth import FastModel
            print(f"Loading {self.model_name}...")
            self.model, self.tokenizer = FastModel.from_pretrained(
                model_name=self.model_name,
                max_seq_length=self.max_seq_length,
            )
            print(f"Model loaded successfully!")
        except Exception as e:
            print(f"Failed to load Unsloth model: {e}")
            raise

    def _call_model(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        system = system or SYSTEM_PROMPT
        
        start_time = time.time()
        
        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
            
            response = self.model.chat(
                tokenizer=self.tokenizer,
                message=messages,
                temperature=self.temperature,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return LLMResponse(
                content=response,
                model=self.model_name,
                duration_ms=duration_ms,
                raw_response={"response": response},
            )
        except Exception as e:
            raise RuntimeError(f"Unsloth inference error: {e}")

    def extract_entities(self, document_text: str) -> dict:
        from src.services.document_extractor import DocumentExtractor
        prompt = build_extraction_prompt(document_text)
        response = self._call_model(prompt)
        llm_result = self._parse_json_response(response.content)

        # Use regex extraction as fallback for empty/None fields
        doc_extractor = DocumentExtractor()
        regex_result = doc_extractor.extract_cps_metadata(document_text)

        return merge_extraction_with_fallback(llm_result, regex_result)

    def analyze_document(self, document_text: str) -> dict:
        prompt = build_analysis_prompt(document_text)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

    def generate_recommendations(self, document_text: str, issues: dict) -> dict:
        issues_str = json.dumps(issues, indent=2)
        prompt = build_recommendation_prompt(document_text, issues_str)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

    def analyze_full(self, document_text: str) -> dict:
        extraction = self.extract_entities(document_text)
        
        analysis = self.analyze_document(document_text)
        
        if analysis.get("issues"):
            recommendations = self.generate_recommendations(document_text, analysis)
        else:
            recommendations = {"recommendations": []}
        
        return {
            "extraction": extraction,
            "analysis": analysis,
            "recommendations": recommendations,
        }

    def _parse_json_response(self, content: str) -> dict:
        content = content.strip()

        # Strip markdown code fences
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(content)
            return validate_extraction_schema(parsed)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in content
        json_match = content.find("{")
        if json_match != -1:
            # Try from first { to end
            try:
                parsed = json.loads(content[json_match:])
                return validate_extraction_schema(parsed)
            except json.JSONDecodeError:
                # Try balanced braces
                depth = 0
                end_pos = json_match
                for i, c in enumerate(content[json_match:], json_match):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                try:
                    parsed = json.loads(content[json_match:end_pos])
                    return validate_extraction_schema(parsed)
                except (json.JSONDecodeError, IndexError):
                    pass

        # All parsing failed - return default structure
        return {"extraction": _default_extraction()}

    def health_check(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def close(self):
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class HuggingFaceAnalyzer:
    def __init__(
        self,
        model_name: Optional[str] = None,
        max_seq_length: Optional[int] = None,
        temperature: Optional[float] = None,
        device: Optional[str] = None,
    ):
        self.model_name = model_name or settings.HF_MODEL_NAME
        self.max_seq_length = max_seq_length or settings.HF_MAX_SEQ_LENGTH
        self.temperature = temperature or settings.HF_TEMPERATURE
        self.device = device or settings.HF_DEVICE
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            print(f"Loading {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=self.device,
                trust_remote_code=True,
            )
            print(f"Model loaded successfully!")
        except Exception as e:
            print(f"Failed to load HuggingFace model: {e}")
            raise

    def _call_model(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        system = system or SYSTEM_PROMPT
        
        start_time = time.time()
        
        try:
            full_prompt = f"{system}\n\n{prompt}"
            
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
            if self.device == "cpu":
                inputs = {k: v for k, v in inputs.items()}
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2000,
                temperature=0.1,
                do_sample=True,
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response[len(full_prompt):].strip()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return LLMResponse(
                content=response,
                model=self.model_name,
                duration_ms=duration_ms,
                raw_response={"response": response},
            )
        except Exception as e:
            raise RuntimeError(f"HuggingFace inference error: {e}")

    def extract_entities(self, document_text: str) -> dict:
        from src.services.document_extractor import DocumentExtractor
        prompt = build_extraction_prompt(document_text)
        response = self._call_model(prompt)
        llm_result = self._parse_json_response(response.content)

        # Use regex extraction as fallback for empty/None fields
        doc_extractor = DocumentExtractor()
        regex_result = doc_extractor.extract_cps_metadata(document_text)

        return merge_extraction_with_fallback(llm_result, regex_result)

    def analyze_document(self, document_text: str) -> dict:
        prompt = build_analysis_prompt(document_text)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

    def generate_recommendations(self, document_text: str, issues: dict) -> dict:
        issues_str = json.dumps(issues, indent=2)
        prompt = build_recommendation_prompt(document_text, issues_str)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

    def analyze_full(self, document_text: str) -> dict:
        extraction = self.extract_entities(document_text)
        
        analysis = self.analyze_document(document_text)
        
        if analysis.get("issues"):
            recommendations = self.generate_recommendations(document_text, analysis)
        else:
            recommendations = {"recommendations": []}
        
        return {
            "extraction": extraction,
            "analysis": analysis,
            "recommendations": recommendations,
        }

    def _parse_json_response(self, content: str) -> dict:
        content = content.strip()

        # Strip markdown code fences
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # Try direct JSON parse
        try:
            parsed = json.loads(content)
            return validate_extraction_schema(parsed)
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in content
        json_match = content.find("{")
        if json_match != -1:
            # Try from first { to end
            try:
                parsed = json.loads(content[json_match:])
                return validate_extraction_schema(parsed)
            except json.JSONDecodeError:
                # Try balanced braces
                depth = 0
                end_pos = json_match
                for i, c in enumerate(content[json_match:], json_match):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                try:
                    parsed = json.loads(content[json_match:end_pos])
                    return validate_extraction_schema(parsed)
                except (json.JSONDecodeError, IndexError):
                    pass

        # All parsing failed - return default structure
        return {"extraction": _default_extraction()}

    def health_check(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def close(self):
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class GroqAnalyzer:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout or settings.GROQ_TIMEOUT
        self.max_retries = max_retries
        self.base_url = "https://api.groq.com/openai/v1"
        self.client = httpx.Client(timeout=self.timeout)

    def _call_api(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        system = system or SYSTEM_PROMPT
        
        # Truncate prompt if too long (Groq llama-3.3-70b supports ~32K tokens)
        max_chars = 25000
        if len(prompt) > max_chars:
            prompt = prompt[:max_chars] + "\n\n[Texte tronqué]"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                # Create fresh client for each attempt
                client = httpx.Client(timeout=self.timeout)
                try:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return LLMResponse(
                        content=data["choices"][0]["message"]["content"],
                        model=data.get("model", self.model),
                        duration_ms=duration_ms,
                        raw_response=data,
                    )
                finally:
                    client.close()
            except httpx.HTTPStatusError as e:
                # Handle 429 (rate limit) with longer backoff
                if e.response.status_code == 429:
                    wait_time = 5 * (2 ** attempt)  # 5, 10, 20 seconds
                    if attempt < self.max_retries - 1:
                        time.sleep(wait_time)
                        continue
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Groq API error after {self.max_retries} attempts: {e}")
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Groq API error after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Unexpected error in _call_api")

    def extract_entities(self, document_text: str) -> dict:
        from src.services.document_extractor import DocumentExtractor
        prompt = build_extraction_prompt(document_text)
        response = self._call_api(prompt)
        llm_result = self._parse_json_response(response.content)

        doc_extractor = DocumentExtractor()
        regex_result = doc_extractor.extract_cps_metadata(document_text)

        return merge_extraction_with_fallback(llm_result, regex_result)

    def analyze_document(self, document_text: str) -> dict:
        prompt = build_analysis_prompt(document_text)
        response = self._call_api(prompt)
        return self._parse_json_response(response.content, is_extraction=False)

    def generate_recommendations(self, document_text: str, issues: dict) -> dict:
        issues_str = json.dumps(issues, indent=2)
        prompt = build_recommendation_prompt(document_text, issues_str)
        response = self._call_api(prompt)
        return self._parse_json_response(response.content)

    def analyze_full(self, document_text: str) -> dict:
        extraction = self.extract_entities(document_text)
        
        analysis = self.analyze_document(document_text)
        
        if analysis.get("issues"):
            recommendations = self.generate_recommendations(document_text, analysis)
        else:
            recommendations = {"recommendations": []}
        
        return {
            "extraction": extraction,
            "analysis": analysis,
            "recommendations": recommendations,
        }

    def _parse_json_response(self, content: str, is_extraction: bool = True) -> dict:
        content = content.strip()

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            parsed = json.loads(content)
            if is_extraction:
                return validate_extraction_schema(parsed)
            return parsed
        except json.JSONDecodeError:
            pass

        json_match = content.find("{")
        if json_match != -1:
            try:
                parsed = json.loads(content[json_match:])
                if is_extraction:
                    return validate_extraction_schema(parsed)
                return parsed
            except json.JSONDecodeError:
                depth = 0
                end_pos = json_match
                for i, c in enumerate(content[json_match:], json_match):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                try:
                    parsed = json.loads(content[json_match:end_pos])
                    if is_extraction:
                        return validate_extraction_schema(parsed)
                    return parsed
                except (json.JSONDecodeError, IndexError):
                    pass

        if is_extraction:
            return {"extraction": _default_extraction()}
        return {"resume": {"total_problemes": 0, "critiques": 0, "eleves": 0, "moyens": 0, "faibles": 0}, "problemes": []}

    def health_check(self) -> bool:
        try:
            response = self.client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class OllamaAnalyzer:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
    ):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=self.timeout)

    def _call_api(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        system = system or SYSTEM_PROMPT
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                duration_ms = int((time.time() - start_time) * 1000)
                
                return LLMResponse(
                    content=data.get("response", ""),
                    model=data.get("model", self.model),
                    duration_ms=duration_ms,
                    raw_response=data,
                )
            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Ollama API error after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)
        
        raise RuntimeError("Unexpected error in _call_api")

    def extract_entities(self, document_text: str) -> dict:
        from src.services.document_extractor import DocumentExtractor
        prompt = build_extraction_prompt(document_text)
        response = self._call_api(prompt)
        llm_result = self._parse_json_response(response.content)

        # Use regex extraction as fallback for empty/None fields
        doc_extractor = DocumentExtractor()
        regex_result = doc_extractor.extract_cps_metadata(document_text)

        return merge_extraction_with_fallback(llm_result, regex_result)

    def analyze_document(self, document_text: str) -> dict:
        prompt = build_analysis_prompt(document_text)
        response = self._call_api(prompt)
        return self._parse_json_response(response.content)

    def generate_recommendations(self, document_text: str, issues: dict) -> dict:
        issues_str = json.dumps(issues, indent=2)
        prompt = build_recommendation_prompt(document_text, issues_str)
        response = self._call_api(prompt)
        return self._parse_json_response(response.content)

    def analyze_full(self, document_text: str) -> dict:
        extraction = self.extract_entities(document_text)
        
        analysis = self.analyze_document(document_text)
        
        if analysis.get("issues"):
            recommendations = self.generate_recommendations(document_text, analysis)
        else:
            recommendations = {"recommendations": []}
        
        return {
            "extraction": extraction,
            "analysis": analysis,
            "recommendations": recommendations,
        }

    def _repair_json(self, content: str) -> str:
        """Repair malformed JSON by fixing common issues."""
        content = content.strip()
        
        if content.startswith("```"):
            content = content[3:]
            if content.startswith("json"):
                content = content[4:]
        if content.endswith("```"):
            content = content[:-3]
        
        first_brace = content.find("{")
        if first_brace > 0:
            content = content[first_brace:]
        
        last_brace = content.rfind("}")
        if last_brace >= 0:
            content = content[:last_brace + 1]
        
        content = content.replace("'", '"')
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        return content.strip()
    
    def _parse_json_response(self, content: str) -> dict:
        content = content.strip()

        repaired = self._repair_json(content)
        try:
            parsed = json.loads(repaired)
            return validate_extraction_schema(parsed)
        except json.JSONDecodeError:
            pass

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            parsed = json.loads(content)
            return validate_extraction_schema(parsed)
        except json.JSONDecodeError:
            pass

        json_match = content.find("{")
        if json_match != -1:
            try:
                parsed = json.loads(content[json_match:])
                return validate_extraction_schema(parsed)
            except json.JSONDecodeError:
                depth = 0
                end_pos = json_match
                for i, c in enumerate(content[json_match:], json_match):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end_pos = i + 1
                            break
                try:
                    parsed = json.loads(content[json_match:end_pos])
                    return validate_extraction_schema(parsed)
                except (json.JSONDecodeError, IndexError):
                    pass

        return {"extraction": _default_extraction()}

    def health_check(self) -> bool:
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AnalyzerWithFallback:
    def __init__(self):
        self.groq_analyzer: Optional[GroqAnalyzer] = None
        self._initialize()

    def _initialize(self):
        print("Initializing GroqAnalyzer...")
        self.groq_analyzer = GroqAnalyzer()
        if not self.groq_analyzer.health_check():
            self.groq_analyzer.close()
            self.groq_analyzer = None
            raise RuntimeError("Groq is not available")
        print("GroqAnalyzer initialized successfully")

    @property
    def analyzer(self):
        if self.groq_analyzer is not None:
            return self.groq_analyzer
        raise RuntimeError("No analyzer available")

    def extract_entities(self, document_text: str) -> dict:
        return self.analyzer.extract_entities(document_text)

    def analyze_document(self, document_text: str) -> dict:
        return self.analyzer.analyze_document(document_text)

    def generate_recommendations(self, document_text: str, issues: dict) -> dict:
        return self.analyzer.generate_recommendations(document_text, issues)

    def analyze_full(self, document_text: str) -> dict:
        return self.analyzer.analyze_full(document_text)

    def health_check(self) -> bool:
        return self.groq_analyzer is not None and self.groq_analyzer.health_check()

    def get_model_name(self) -> str:
        return self.groq_analyzer.model if self.groq_analyzer else "none"

    def close(self):
        if self.groq_analyzer is not None:
            self.groq_analyzer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
