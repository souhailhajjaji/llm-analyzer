import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


class TestAPI:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["status"] == "running"

    def test_health_endpoint(self):
        from src.services.llm_analyzer import AnalyzerWithFallback
        from src.api.main import app
        
        app.state.analyzer = AnalyzerWithFallback()
        
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "ollama" in data

    def test_analyze_invalid_file_type(self):
        response = client.post(
            "/api/analyze",
            files={"file": ("test.txt", b"content", "text/plain")}
        )
        assert response.status_code == 400

    def test_analyze_text_endpoint(self):
        with patch('analyzer.analyser_cahier') as mock_analyze:
            mock_analyze.return_value = {
                "extraction": {},
                "analysis": {"issues": []},
                "recommendations": {"recommendations": []}
            }
            
            response = client.post(
                "/api/analyze/text",
                json={"text": "Test document content"}
            )
            assert response.status_code == 200

    def test_get_analysis_not_found(self):
        response = client.get("/api/analyze/nonexistent-id")
        assert response.status_code == 404

    def test_get_analysis_status_not_found(self):
        response = client.get("/api/analyze/nonexistent-id/status")
        assert response.status_code == 404

    def test_feedback_not_found(self):
        response = client.post(
            "/api/feedback",
            json={
                "analysis_id": "nonexistent",
                "issue_id": "ISSUE-1",
                "is_valid": True
            }
        )
        assert response.status_code == 404

    def test_process_time_header(self):
        response = client.get("/")
        assert "x-process-time" in response.headers
