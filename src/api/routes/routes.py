import uuid
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel

from src.services.document_extractor import DocumentExtractor
from src.services.validator import Validator
from src.core.config import settings
from src.services.report_generator import ReportGenerator
from src.services.rule_analyzer import analyze_with_rules
from src.services.hybrid_analyzer import analyze_hybrid
from analyzer import analyser_cahier

router = APIRouter()

ANALYSIS_STORE = {}

class AnalyzeRequest(BaseModel):
    text: str
    enable_llm: bool = True
    analyse_avancee: bool = False

class AnalyzeResponse(BaseModel):
    id: str
    status: str
    result: Optional[dict] = None

class FeedbackRequest(BaseModel):
    analysis_id: str
    issue_id: str
    is_valid: bool
    comment: Optional[str] = None


@router.get("/health")
async def health_check(request: Request):
    analyzer = request.app.state.analyzer
    
    return {
        "status": "healthy" if analyzer.health_check() else "degraded",
        "model": analyzer.get_model_name(),
    }


@router.post("/analyze")
async def analyze_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    allowed = [".docx", ".pdf"]
    if not any(file.filename.endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail=f"Only {allowed} files are supported")
    
    analysis_id = str(uuid.uuid4())
    
    temp_path = f"uploads/{analysis_id}_{file.filename}"
    content = await file.read()
    
    with open(temp_path, "wb") as f:
        f.write(content)
    
    ANALYSIS_STORE[analysis_id] = {
        "status": "processing",
        "filename": file.filename,
        "started_at": time.time(),
    }
    
    background_tasks.add_task(process_analysis, analysis_id, temp_path, request)
    
    return {
        "id": analysis_id,
        "status": "processing",
        "message": "Analysis started. Use /analyze/{id}/status to check progress.",
    }


async def process_analysis(analysis_id: str, file_path: str, request: Request):
    try:
        extractor = DocumentExtractor()
        extracted = extractor.extract_text_only(file_path)
        
        analyzer = request.app.state.analyzer
        result = analyzer.analyze_full(extracted)
        
        validator = Validator()
        validated = validator.validate_analysis_result(result)
        
        validated.processing_time_ms = int((time.time() - ANALYSIS_STORE[analysis_id]["started_at"]) * 1000)
        
        report_gen = ReportGenerator()
        report = report_gen.generate_json_report(validated, filename=file_path.split("/")[-1])
        
        ANALYSIS_STORE[analysis_id] = {
            "status": "completed",
            "result": report,
            "completed_at": time.time(),
        }
        
    except Exception as e:
        ANALYSIS_STORE[analysis_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": time.time(),
        }


@router.post("/analyze/text")
async def analyze_text(request: Request, analyze_request: AnalyzeRequest):
    analysis_id = str(uuid.uuid4())
    
    ANALYSIS_STORE[analysis_id] = {
        "status": "processing",
        "filename": "text_input",
        "started_at": time.time(),
    }
    
    try:
        result = analyser_cahier(
            analyze_request.text,
            api_token=settings.HF_TOKEN,
            use_ollama=settings.USE_OLLAMA,
            use_huggingface=settings.USE_HUGGINGFACE,
            use_groq=settings.USE_GROQ,
            groq_api_key=settings.GROQ_API_KEY,
            analyse_avancee=analyze_request.analyse_avancee
        )
        
        ANALYSIS_STORE[analysis_id] = {
            "status": "completed",
            "result": result,
            "completed_at": time.time(),
        }

    except Exception as e:
        import traceback
        ANALYSIS_STORE[analysis_id] = {
            "status": "failed",
            "error": str(e) + "\n" + traceback.format_exc(),
            "failed_at": time.time(),
        }
    
    return ANALYSIS_STORE[analysis_id]


@router.post("/analyze/hybrid")
async def analyze_hybrid_endpoint(request: Request, analyze_request: AnalyzeRequest):
    """Analyse hybride Rule-Based + Qwen LLM"""
    analysis_id = str(uuid.uuid4())
    
    ANALYSIS_STORE[analysis_id] = {
        "status": "processing",
        "filename": "text_input",
        "started_at": time.time(),
    }
    
    try:
        result = analyze_hybrid(
            analyze_request.text, 
            enable_llm=analyze_request.enable_llm
        )
        
        ANALYSIS_STORE[analysis_id] = {
            "status": "completed",
            "result": result,
            "completed_at": time.time(),
        }

    except Exception as e:
        import traceback
        ANALYSIS_STORE[analysis_id] = {
            "status": "failed",
            "error": str(e) + "\n" + traceback.format_exc(),
            "failed_at": time.time(),
        }
    
    return ANALYSIS_STORE[analysis_id]


@router.get("/analyze/{analysis_id}")
async def get_analysis(analysis_id: str):
    if analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = ANALYSIS_STORE[analysis_id]
    
    if analysis["status"] == "completed":
        return analysis["result"]
    elif analysis["status"] == "failed":
        raise HTTPException(status_code=500, detail=analysis.get("error", "Analysis failed"))
    else:
        return {"status": "processing", "message": "Analysis still in progress"}


@router.get("/analyze/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    if analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = ANALYSIS_STORE[analysis_id]
    
    return {
        "id": analysis_id,
        "status": analysis["status"],
        "filename": analysis.get("filename"),
    }


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    if request.analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    analysis = ANALYSIS_STORE[request.analysis_id]
    
    if "feedback" not in analysis:
        analysis["feedback"] = []
    
    analysis["feedback"].append({
        "issue_id": request.issue_id,
        "is_valid": request.is_valid,
        "comment": request.comment,
        "timestamp": time.time(),
    })
    
    return {"status": "feedback recorded", "feedback": analysis["feedback"]}


@router.get("/analyses")
async def get_analyses():
    """Retourne la liste de toutes les analyses de la session"""
    analyses = []
    for analysis_id, data in ANALYSIS_STORE.items():
        result = data.get("result", {})
        extraction = result.get("extraction", {})
        resume = result.get("resume", {})
        
        nom_client = None
        objet = None
        
        if extraction:
            metadonnees = extraction.get("metadonnees", {})
            nom_client = metadonnees.get("nom_client")
            objet = metadonnees.get("objet")
        
        analyses.append({
            "id": analysis_id,
            "filename": data.get("filename"),
            "status": data.get("status"),
            "nom_client": nom_client,
            "objet": objet,
            "total_problemes": resume.get("total_problemes", 0),
            "created_at": data.get("started_at") or data.get("completed_at") or data.get("failed_at"),
        })
    
    analyses.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    
    return {"analyses": analyses}


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Supprime une analyse de l'historique"""
    if analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    del ANALYSIS_STORE[analysis_id]
    return {"status": "deleted", "id": analysis_id}
