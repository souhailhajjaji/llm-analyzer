"""
Hybrid Analyzer - Combine Rule-Based + Qwen LLM
Fuse les résultats pour un rapport complet
"""

import json
import uuid
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from src.services.rule_analyzer import RuleBasedAnalyzer
from src.services.llm_analyzer import QwenLocalAnalyzer


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
    """Analyseur hybride Rule-Based + Qwen LLM"""
    
    def __init__(self, enable_llm: bool = True, min_confidence: float = 0.5):
        self.rule_analyzer = RuleBasedAnalyzer()
        self.llm_analyzer = QwenLocalAnalyzer() if enable_llm else None
        self.enable_llm = enable_llm
        self.min_confidence = min_confidence
    
    def analyze(self, text: str) -> HybridResult:
        """Analyse complète hybride"""
        start_time = time.time()
        
        rule_results = self.rule_analyzer.analyze(text)
        rule_extraction = self.rule_analyzer.extract_entities(text)
        
        all_issues = list(rule_results.get("issues", []))
        
        qwen_issues = []
        
        if self.enable_llm and self.llm_analyzer:
            try:
                if not self.llm_analyzer.is_loaded():
                    print("Chargement de Qwen (une fois)...")
                    self.llm_analyzer.load()
                
                if self.llm_analyzer.is_loaded():
                    print("Qwen: Recherche des problèmes manqués...")
                    missing = self.llm_analyzer.find_missing_issues(text, rule_results)
                    
                    for issue in missing:
                        if issue.get("confidence", 0) >= self.min_confidence:
                            issue["id"] = f"Qwen-{issue.get('issue', 'issue')[:20]}"
                            issue["source"] = "qwen"
                            qwen_issues.append(issue)
                    
                    print(f"Qwen: {len(qwen_issues)} nouveaux problèmes découverts")
                    
            except Exception as e:
                print(f"Erreur Qwen: {e}")
        
        all_issues.extend(qwen_issues)
        
        all_issues = self._deduplicate(all_issues)
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in all_issues:
            sev = issue.get("severity", "medium")
            if sev in severity_counts:
                severity_counts[sev] += 1
        
        recommendations = self._generate_recommendations(all_issues)
        
        confidence = self._calculate_confidence(all_issues, qwen_issues)
        
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
            model_used="Qwen2.5-0.5B" if self.enable_llm else "Rule-Based only",
            confidence_score=confidence
        )
    
    def _deduplicate(self, issues: List[Dict]) -> List[Dict]:
        """Supprime les doublons"""
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
        """Génère les recommandations triées par priorité"""
        priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        
        recommendations = []
        for issue in issues:
            recommendations.append({
                "issue_id": issue.get("id", ""),
                "priority": priority_map.get(issue.get("severity", "medium"), 3),
                "recommendation": issue.get("recommendation", "Aucune recommandation"),
                "implementation_hint": f"Vérifier et implémenter: {issue.get('issue', '')}"
            })
        
        recommendations.sort(key=lambda x: x["priority"])
        return recommendations
    
    def _calculate_confidence(self, all_issues: List[Dict], qwen_issues: List[Dict]) -> float:
        """Calcule le score de confiance"""
        if not qwen_issues:
            return 0.8
        
        base = 0.6
        qwen_ratio = len(qwen_issues) / max(len(all_issues), 1)
        
        return min(0.95, base + (qwen_ratio * 0.2))
    
    def close(self):
        if self.llm_analyzer:
            self.llm_analyzer.close()


def analyze_hybrid(text: str, enable_llm: bool = True, min_confidence: float = 0.5) -> dict:
    """Fonction principale d'analyse hybride"""
    analyzer = HybridAnalyzer(enable_llm=enable_llm, min_confidence=min_confidence)
    result = analyzer.analyze(text)
    analyzer.close()
    
    return asdict(result)