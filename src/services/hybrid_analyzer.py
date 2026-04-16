"""
Hybrid Analyzer - Combine Rule-Based + Groq LLM
"""

import json
import time
from typing import List, Dict
from dataclasses import dataclass, asdict

from src.services.rule_analyzer import RuleBasedAnalyzer
from src.services.llm_analyzer import GroqAnalyzer
from src.core.config import settings


@dataclass
class HybridResult:
    total_issues: int
    critical: int
    high: int
    medium: int
    low: int
    issues: List[Dict]
    extraction: Dict
    recommendations: List[Dict]
    processing_time_ms: int
    model_used: str
    confidence_score: float


class HybridAnalyzer:
    def __init__(self, enable_llm: bool = True, min_confidence: float = 0.5):
        self.rule_analyzer = RuleBasedAnalyzer()
        self.llm_analyzer = GroqAnalyzer() if enable_llm and settings.USE_GROQ else None
        self.enable_llm = enable_llm
        self.min_confidence = min_confidence
    
    def analyze(self, text: str) -> HybridResult:
        start_time = time.time()
        
        rule_results = self.rule_analyzer.analyze(text)
        rule_extraction = self.rule_analyzer.extract_entities(text)
        
        all_issues = list(rule_results.get("issues", []))
        groq_issues = []
        
        if self.enable_llm and self.llm_analyzer:
            try:
                print("Groq: Recherche des problèmes...")
                missing = self._find_missing_issues_with_llm(text, rule_results)
                
                for issue in missing:
                    if issue.get("confidence", 0) >= self.min_confidence:
                        issue["id"] = f"Groq-{issue.get('issue', 'issue')[:20]}"
                        issue["source"] = "groq"
                        groq_issues.append(issue)
                
                print(f"Groq: {len(groq_issues)} problèmes trouvés")
            
            except Exception as e:
                print(f"Erreur Groq: {e}")
        
        all_issues.extend(groq_issues)
        all_issues = self._deduplicate(all_issues)
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in all_issues:
            sev = issue.get("severity", "medium")
            if sev in severity_counts:
                severity_counts[sev] += 1
        
        recommendations = self._generate_recommendations(all_issues)
        confidence = self._calculate_confidence(all_issues, groq_issues)
        duration_ms = int((time.time() - start_time) * 1000)
        
        return HybridResult(
            total_issues=len(all_issues),
            critical=severity_counts["critical"],
            high=severity_counts["high"],
            medium=severity_counts["medium"],
            low=severity_counts["low"],
            issues=all_issues,
            extraction=rule_extraction,
            recommendations=recommendations,
            processing_time_ms=duration_ms,
            model_used="llama-3.3-70b-versatile" if self.enable_llm and self.llm_analyzer else "Rule-Based only",
            confidence_score=confidence
        )
    
    def _deduplicate(self, issues: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for issue in issues:
            key = issue.get("issue", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(issue)
            elif not key:
                unique.append(issue)
        return unique
    
    def _generate_recommendations(self, issues: List[Dict]) -> List[Dict]:
        priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        recommendations = []
        for issue in issues:
            recommendations.append({
                "issue_id": issue.get("id", ""),
                "priority": priority_map.get(issue.get("severity", "medium"), 3),
                "recommendation": issue.get("recommendation", "Aucune recommandation"),
                "implementation_hint": f"Vérifier: {issue.get('issue', '')}"
            })
        recommendations.sort(key=lambda x: x["priority"])
        return recommendations
    
    def _calculate_confidence(self, all_issues: List[Dict], groq_issues: List[Dict]) -> float:
        if not groq_issues:
            return 0.8
        base = 0.6
        groq_ratio = len(groq_issues) / max(len(all_issues), 1)
        return min(0.95, base + (groq_ratio * 0.2))
    
    def _find_missing_issues_with_llm(self, text: str, rule_results: dict) -> List[Dict]:
        if not self.llm_analyzer:
            return []
        
        existing_issues = {issue.get("issue", "").lower() for issue in rule_results.get("issues", [])}
        
        prompt = f"""Tu es un expert en sécurité informatique. Analyse ce cahier des charges et détecte les problèmes de sécurité manquants.

Cahier des charges:
{text[:3000]}

Problèmes déjà détectés:
{json.dumps(rule_results.get("issues", [])[:10], indent=2, ensure_ascii=False)}

Réponds en JSON:
[
  {{
    "issue": "Titre du problème",
    "description": "Description",
    "severity": "critical|high|medium|low",
    "confidence": 0.0-1.0
  }}
]

JSON:"""

        try:
            response = self.llm_analyzer._call_api(prompt)
            return self._parse_llm_response(response.content, existing_issues)
        except Exception as e:
            print(f"Erreur LLM: {e}")
            return []

    def _parse_llm_response(self, content: str, existing_issues: set) -> List[Dict]:
        content = content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        try:
            issues = json.loads(content)
            return [i for i in issues if i.get("issue", "").lower() not in existing_issues]
        except json.JSONDecodeError:
            pass
        
        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end != 0:
                issues = json.loads(content[start:end])
                return [i for i in issues if i.get("issue", "").lower() not in existing_issues]
        except:
            pass
        
        return []

    def close(self):
        if self.llm_analyzer:
            self.llm_analyzer.close()


def analyze_hybrid(text: str, enable_llm: bool = True, min_confidence: float = 0.5) -> dict:
    analyzer = HybridAnalyzer(enable_llm=enable_llm, min_confidence=min_confidence)
    result = analyzer.analyze(text)
    analyzer.close()
    return asdict(result)