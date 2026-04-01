import json
from datetime import datetime
from typing import Any
from src.services.validator import AnalysisResult, Severity


class ReportGenerator:
    def __init__(self):
        self.severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }

    def generate_json_report(
        self,
        result: AnalysisResult,
        filename: str = None,
        metadata: dict = None,
    ) -> dict:
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "filename": filename,
            "metadata": metadata or {},
            "summary": self._generate_summary(result),
            "extraction": self._format_extraction(result.extraction),
            "issues": self._format_issues(result.analysis.issues),
            "recommendations": self._format_recommendations(
                result.recommendations.recommendations
            ),
            "statistics": self._generate_statistics(result),
            "confidence_score": round(result.confidence_score, 2),
            "processing_time_ms": result.processing_time_ms,
        }
        
        return report

    def _generate_summary(self, result: AnalysisResult) -> dict:
        issue_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": len(result.analysis.issues),
        }
        
        for issue in result.analysis.issues:
            severity = issue.severity.value if isinstance(issue.severity, Severity) else issue.severity
            if severity in issue_counts:
                issue_counts[severity] += 1
        
        categories = {}
        for issue in result.analysis.issues:
            cat = issue.category.value if hasattr(issue.category, 'value') else issue.category
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_issues": issue_counts["total"],
            "by_severity": issue_counts,
            "by_category": categories,
            "confidence_level": self._get_confidence_level(result.confidence_score),
        }

    def _get_confidence_level(self, score: float) -> str:
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"

    def _format_extraction(self, extraction) -> dict:
        return {
            "functionalities": extraction.functionalities,
            "actors": extraction.actors,
            "constraints": extraction.constraints,
            "interfaces": extraction.interfaces,
            "data": extraction.data,
        }

    def _format_issues(self, issues) -> list[dict]:
        sorted_issues = sorted(
            issues,
            key=lambda x: self.severity_order.get(
                x.severity if isinstance(x.severity, Severity) else Severity(x.severity),
                99
            )
        )
        
        return [
            {
                "id": f"ISSUE-{i+1}",
                "category": issue.category.value if hasattr(issue.category, 'value') else issue.category,
                "pattern_id": issue.pattern_id,
                "issue": issue.issue,
                "location": issue.location,
                "severity": issue.severity.value if isinstance(issue.severity, Severity) else issue.severity,
                "recommendation": issue.recommendation,
            }
            for i, issue in enumerate(sorted_issues)
        ]

    def _format_recommendations(self, recommendations) -> list[dict]:
        sorted_recs = sorted(recommendations, key=lambda x: x.priority)
        
        return [
            {
                "issue_id": rec.issue_id,
                "priority": rec.priority,
                "recommendation": rec.recommendation,
                "implementation_hint": rec.implementation_hint,
            }
            for rec in sorted_recs
        ]

    def _generate_statistics(self, result: AnalysisResult) -> dict:
        total_issues = len(result.analysis.issues)
        
        if total_issues == 0:
            return {
                "total_issues": 0,
                "critical_percentage": 0,
                "high_percentage": 0,
                "issues_per_functionality": 0,
            }
        
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in result.analysis.issues:
            sev = issue.severity.value if isinstance(issue.severity, Severity) else issue.severity
            if sev in severity_counts:
                severity_counts[sev] += 1
        
        functionalities_count = len(result.extraction.functionalities) or 1
        
        return {
            "total_issues": total_issues,
            "critical_percentage": round(severity_counts["critical"] / total_issues * 100, 1),
            "high_percentage": round(severity_counts["high"] / total_issues * 100, 1),
            "issues_per_functionality": round(total_issues / functionalities_count, 1),
        }

    def to_json_string(self, report: dict, indent: int = 2) -> str:
        return json.dumps(report, indent=indent, ensure_ascii=False)

    def save_report(self, report: dict, filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json_string(report))
