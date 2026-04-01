import json
import time
import re
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from src.core.config import settings
from src.core.prompts import (
    SYSTEM_PROMPT,
    build_extraction_prompt,
    build_analysis_prompt,
    build_recommendation_prompt,
)


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
        prompt = build_extraction_prompt(document_text)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

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
            json_match = content.find("{")
            if json_match != -1:
                try:
                    return json.loads(content[json_match:])
                except json.JSONDecodeError:
                    pass
            
            return {"raw": content, "error": "Failed to parse JSON"}

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
                max_new_tokens=50,
                temperature=0.3,
                do_sample=False,
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
        prompt = build_extraction_prompt(document_text)
        response = self._call_model(prompt)
        return self._parse_json_response(response.content)

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
            json_match = content.find("{")
            if json_match != -1:
                try:
                    return json.loads(content[json_match:])
                except json.JSONDecodeError:
                    pass
            
            return {"raw": content, "error": "Failed to parse JSON"}

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
        prompt = build_extraction_prompt(document_text)
        response = self._call_api(prompt)
        return self._parse_json_response(response.content)

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

    def _parse_json_response(self, content: str) -> dict:
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
            json_match = content.find("{")
            if json_match != -1:
                try:
                    return json.loads(content[json_match:])
                except json.JSONDecodeError:
                    pass
            
            return {"raw": content, "error": "Failed to parse JSON"}

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
        self.hf_analyzer: Optional[HuggingFaceAnalyzer] = None
        self.ollama_analyzer: Optional[OllamaAnalyzer] = None
        self._initialize()

    def _initialize(self):
        if settings.USE_HUGGINGFACE:
            try:
                print("Initializing HuggingFaceAnalyzer (primary)...")
                self.hf_analyzer = HuggingFaceAnalyzer()
                print("HuggingFaceAnalyzer initialized successfully")
            except Exception as e:
                print(f"Failed to initialize HuggingFaceAnalyzer: {e}")
                print("Will use OllamaAnalyzer as fallback")
                self.hf_analyzer = None
        
        if self.hf_analyzer is None:
            try:
                print("Initializing OllamaAnalyzer...")
                self.ollama_analyzer = OllamaAnalyzer()
                if self.ollama_analyzer.health_check():
                    print("OllamaAnalyzer initialized successfully")
                else:
                    self.ollama_analyzer.close()
                    self.ollama_analyzer = None
                    raise RuntimeError("Ollama is not available")
            except Exception as e:
                print(f"Failed to initialize OllamaAnalyzer: {e}")
                self.ollama_analyzer = None

    @property
    def analyzer(self):
        if self.hf_analyzer is not None:
            return self.hf_analyzer
        if self.ollama_analyzer is not None:
            return self.ollama_analyzer
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
        if self.hf_analyzer is not None and self.hf_analyzer.health_check():
            return True
        if self.ollama_analyzer is not None:
            return self.ollama_analyzer.health_check()
        return False

    def get_model_name(self) -> str:
        if self.hf_analyzer is not None:
            return self.hf_analyzer.model_name
        if self.ollama_analyzer is not None:
            return self.ollama_analyzer.model
        return "none"

    def close(self):
        if self.hf_analyzer is not None:
            self.hf_analyzer.close()
        if self.ollama_analyzer is not None:
            self.ollama_analyzer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
