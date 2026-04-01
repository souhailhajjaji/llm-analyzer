from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(str, Enum):
    BUGS_PATTERNS = "bugs_patterns"
    SECURITY_PATTERNS = "security_patterns"
    INCONSISTENCIES = "inconsistencies"


class Issue(BaseModel):
    category: Category
    pattern_id: str
    issue: str
    location: str
    severity: Severity
    recommendation: str

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v


class ExtractionData(BaseModel):
    functionalities: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    data: list[str] = Field(default_factory=list)


class AnalysisData(BaseModel):
    issues: list[Issue] = Field(default_factory=list)


class Recommendation(BaseModel):
    issue_id: str
    priority: int = Field(ge=1, le=5)
    recommendation: str
    implementation_hint: str


class RecommendationsData(BaseModel):
    recommendations: list[Recommendation] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    extraction: ExtractionData
    analysis: AnalysisData
    recommendations: RecommendationsData
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    processing_time_ms: int = Field(ge=0, default=0)

    def calculate_confidence(self) -> float:
        if not self.analysis.issues:
            return 0.8
        
        severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.75,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.25,
        }
        
        total_weight = sum(
            severity_weights.get(issue.severity, 0.5) 
            for issue in self.analysis.issues
        )
        
        avg_severity = total_weight / len(self.analysis.issues)
        
        return max(0.0, 1.0 - avg_severity)


class Validator:
    @staticmethod
    def validate_analysis_result(data: dict) -> AnalysisResult:
        try:
            extraction = ExtractionData(**data.get("extraction", {}))
        except Exception:
            extraction = ExtractionData()
        
        try:
            issues_data = data.get("analysis", {}).get("issues", [])
            issues = [Issue(**issue) for issue in issues_data]
            analysis = AnalysisData(issues=issues)
        except Exception:
            analysis = AnalysisData()
        
        try:
            recs_data = data.get("recommendations", {}).get("recommendations", [])
            recommendations = [Recommendation(**rec) for rec in recs_data]
            recommendations_data = RecommendationsData(recommendations=recommendations)
        except Exception:
            recommendations_data = RecommendationsData()
        
        result = AnalysisResult(
            extraction=extraction,
            analysis=analysis,
            recommendations=recommendations_data,
        )
        
        result.confidence_score = result.calculate_confidence()
        
        return result

    @staticmethod
    def validate_json_structure(data: dict) -> tuple[bool, list[str]]:
        errors = []
        
        if "extraction" not in data:
            errors.append("Missing 'extraction' key")
        
        if "analysis" not in data:
            errors.append("Missing 'analysis' key")
        
        return len(errors) == 0, errors
