import re
from pathlib import Path
from typing import List, Dict, Any
from src.core.rules_loader import RulesLoader, RulePattern
from src.core.config import settings


class RuleBasedAnalyzer:
    def __init__(self, rules_dir: Path = None):
        self.rules_dir = rules_dir or settings.RULES_DIR
        self.loader = RulesLoader(self.rules_dir)
        self.rules = self.loader.load_rules()

    def analyze(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        issues = []

        for category, rule_set in self.rules.items():
            for pattern in rule_set.patterns:
                matches = self._check_pattern(pattern, text_lower)
                if matches:
                    issues.append({
                        "category": category,
                        "pattern_id": pattern.id,
                        "issue": pattern.name,
                        "location": matches[0] if matches else "",
                        "severity": pattern.severity,
                        "recommendation": pattern.recommendation,
                    })

        return {"issues": issues}

    def _check_pattern(self, pattern: RulePattern, text: str) -> List[str]:
        matches = []
        for indicator in pattern.indicators:
            if indicator.lower() in text:
                matches.append(indicator)
        return matches

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        functionalities = []
        actors = []
        data = []

        text_lower = text.lower()

        if any(w in text_lower for w in ["utilisateur", "gestion", "créer", "modifier", "supprimer", "ajouter"]):
            functionalities.append("Gestion des utilisateurs et opérations CRUD")

        if any(w in text_lower for w in ["utilisateur", "admin", "client", "gestionnaire"]):
            actors.extend([a for a in ["utilisateur", "admin", "client"] if a in text_lower])

        if any(w in text_lower for w in ["base de données", "sqlite", "mysql", "fichier", "stock"]):
            data.append("Données persistantes")

        return {
            "functionalities": list(set(functionalities)),
            "actors": list(set(actors)),
            "constraints": [],
            "interfaces": [],
            "data": list(set(data)),
        }

    def generate_recommendations(self, issues: List[Dict]) -> Dict[str, Any]:
        recommendations = []
        for issue in issues:
            severity_to_priority = {
                "critical": 1,
                "high": 2,
                "medium": 3,
                "low": 4,
            }
            recommendations.append({
                "issue_id": issue.get("pattern_id", ""),
                "priority": severity_to_priority.get(issue.get("severity", "medium"), 3),
                "recommendation": issue.get("recommendation", ""),
                "implementation_hint": f"Vérifier et implémenter {issue.get('issue', 'cette fonctionnalité')}",
            })
        return {"recommendations": recommendations}


def analyze_with_rules(text: str) -> Dict[str, Any]:
    analyzer = RuleBasedAnalyzer()
    issues_result = analyzer.analyze(text)
    extraction = analyzer.extract_entities(text)
    recommendations_result = analyzer.generate_recommendations(issues_result.get("issues", []))

    return {
        "extraction": extraction,
        "analysis": issues_result,
        "recommendations": recommendations_result,
    }
