import yaml
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class RulePattern:
    id: str
    name: str
    description: str
    indicators: List[str]
    severity: str
    recommendation: str


@dataclass
class RuleSet:
    version: str
    category: str
    description: str
    patterns: List[RulePattern]


class RulesLoader:
    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir

    def load_rules(self) -> Dict[str, RuleSet]:
        rules = {}
        for yaml_file in self.rules_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                patterns = [
                    RulePattern(
                        id=p["id"],
                        name=p["name"],
                        description=p["description"],
                        indicators=p.get("indicators", []),
                        severity=p["severity"],
                        recommendation=p["recommendation"],
                    )
                    for p in data.get("patterns", [])
                ]
                rules[data["category"]] = RuleSet(
                    version=data["version"],
                    category=data["category"],
                    description=data["description"],
                    patterns=patterns,
                )
        return rules

    def get_all_indicators(self) -> Dict[str, List[str]]:
        rules = self.load_rules()
        indicators = {}
        for category, rule_set in rules.items():
            indicators[category] = []
            for pattern in rule_set.patterns:
                indicators[category].extend(pattern.indicators)
        return indicators

    def get_pattern_by_id(self, pattern_id: str) -> RulePattern | None:
        rules = self.load_rules()
        for rule_set in rules.values():
            for pattern in rule_set.patterns:
                if pattern.id == pattern_id:
                    return pattern
        return None
