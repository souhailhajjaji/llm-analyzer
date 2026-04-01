import pytest
from unittest.mock import Mock, patch

from src.services.llm_analyzer import OllamaAnalyzer, LLMResponse


class TestOllamaAnalyzer:
    @patch('src.services.llm_analyzer.httpx.Client')
    def test_health_check_connected(self, mock_client):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.get.return_value = mock_response
        
        analyzer = OllamaAnalyzer()
        result = analyzer.health_check()
        
        assert result is True

    @patch('src.services.llm_analyzer.httpx.Client')
    def test_health_check_disconnected(self, mock_client):
        mock_client.return_value.get.side_effect = Exception("Connection error")
        
        analyzer = OllamaAnalyzer()
        result = analyzer.health_check()
        
        assert result is False

    @patch('src.services.llm_analyzer.httpx.Client')
    def test_parse_json_response(self, mock_client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": '{"key": "value"}',
            "model": "llama3.2",
        }
        mock_response.raise_for_status = Mock()
        mock_client.return_value.post.return_value = mock_response
        
        analyzer = OllamaAnalyzer()
        result = analyzer._parse_json_response('{"key": "value"}')
        
        assert result == {"key": "value"}

    @patch('src.services.llm_analyzer.httpx.Client')
    def test_parse_json_fallback(self, mock_client):
        mock_response = Mock()
        mock_response.json.return_value = {"response": "plain text"}
        mock_response.raise_for_status = Mock()
        mock_client.return_value.post.return_value = mock_response
        
        analyzer = OllamaAnalyzer()
        result = analyzer._parse_json_response("This is plain text without JSON")
        
        assert result.get("raw") is not None

    def test_context_manager(self):
        analyzer = OllamaAnalyzer()
        
        with analyzer as a:
            assert a is analyzer
        
        analyzer.client.close.assert_called_once()
