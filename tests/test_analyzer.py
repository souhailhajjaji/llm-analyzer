import pytest
from unittest.mock import Mock, patch

from src.services.llm_analyzer import (
    OllamaAnalyzer, LLMResponse,
    validate_extraction_schema, _default_extraction, merge_extraction_with_fallback,
)


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
    def test_parse_json_response_valid(self, mock_client):
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": '{"key": "value"}',
            "model": "llama3.2",
        }
        mock_response.raise_for_status = Mock()
        mock_client.return_value.post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        result = analyzer._parse_json_response('{"key": "value"}')

        # Non-extraction JSON is wrapped in the default extraction schema
        assert "extraction" in result
        assert result["extraction"] is not None

    @patch('src.services.llm_analyzer.httpx.Client')
    def test_parse_json_fallback_returns_default(self, mock_client):
        mock_response = Mock()
        mock_response.json.return_value = {"response": "plain text"}
        mock_response.raise_for_status = Mock()
        mock_client.return_value.post.return_value = mock_response

        analyzer = OllamaAnalyzer()
        result = analyzer._parse_json_response("This is plain text without JSON")

        # Should return default extraction structure, not {"raw": ...}
        assert "extraction" in result
        assert result["extraction"].get("metadonnees") is not None

    def test_context_manager(self):
        analyzer = OllamaAnalyzer()
        close_mock = Mock()
        analyzer.client.close = close_mock

        with analyzer as a:
            assert a is analyzer

        close_mock.assert_called_once()


class TestValidateExtractionSchema:
    def test_valid_extraction_passes_through(self):
        data = {
            "extraction": {
                "metadonnees": {"nom_client": "OMPIC", "objet": "Test", "objectifs": [], "orientations_technologiques": []},
                "contraintes_projet": {"date_limite_soumission": None, "budget": None, "caution_provisoire": "3%", "delai_execution": "12 mois"},
                "dossier_reponse": {"administratif": [], "technique": [], "financier": []},
                "references": [], "exigences": [], "modalites_paiement": [],
            }
        }
        result = validate_extraction_schema(data)
        assert result["extraction"]["metadonnees"]["nom_client"] == "OMPIC"

    def test_invalid_extraction_returns_default(self):
        result = validate_extraction_schema(None)
        assert "extraction" in result
        assert result["extraction"]["metadonnees"]["nom_client"] is None

    def test_garbled_dossier_filtered_out(self):
        garbled = "this is a very long garbled text that exceeds three hundred characters and should be filtered out because it is clearly not a proper dossier item but rather some random text from the document that got mixed up during extraction process and should never appear in the final results shown to the user at all"
        assert len(garbled) > 300  # Ensure it's actually over the limit
        data = {
            "extraction": {
                "metadonnees": {"nom_client": None, "objet": None, "objectifs": [], "orientations_technologiques": []},
                "contraintes_projet": {"date_limite_soumission": None, "budget": None, "caution_provisoire": None, "delai_execution": None},
                "dossier_reponse": {
                    "administratif": ["short item", garbled],
                    "technique": [], "financier": [],
                },
                "references": [], "exigences": [], "modalites_paiement": [],
            }
        }
        result = validate_extraction_schema(data)
        admin = result["extraction"]["dossier_reponse"]["administratif"]
        assert len(admin) == 1
        assert admin[0] == "short item"


class TestMergeExtractionWithFallback:
    def test_llm_values_preserved(self):
        llm = {"extraction": {"metadonnees": {"nom_client": "LLM Client", "objet": "LLM Object", "objectifs": ["obj1"], "orientations_technologiques": []}, "contraintes_projet": {"date_limite_soumission": "2025-01-01", "budget": "100000", "caution_provisoire": "3%", "delai_execution": "12 mois"}, "dossier_reponse": {"administratif": [], "technique": [], "financier": []}, "references": [], "exigences": [], "modalites_paiement": []}}
        regex = {"metadonnees": {"nom_client": "Regex Client"}, "contraintes_projet": {"budget": "50000"}}
        result = merge_extraction_with_fallback(llm, regex)
        assert result["extraction"]["metadonnees"]["nom_client"] == "LLM Client"

    def test_regex_fills_empty_llm_fields(self):
        llm = {"extraction": {"metadonnees": {"nom_client": None, "objet": None, "objectifs": [], "orientations_technologiques": []}, "contraintes_projet": {"date_limite_soumission": None, "budget": None, "caution_provisoire": None, "delai_execution": None}, "dossier_reponse": {"administratif": [], "technique": [], "financier": []}, "references": [], "exigences": [], "modalites_paiement": []}}
        regex = {"metadonnees": {"nom_client": "Regex Client", "objet": "Regex Object"}, "contraintes_projet": {"budget": "50000", "caution_provisoire": "3%"}}
        result = merge_extraction_with_fallback(llm, regex)
        assert result["extraction"]["metadonnees"]["nom_client"] == "Regex Client"
        assert result["extraction"]["metadonnees"]["objet"] == "Regex Object"
        assert result["extraction"]["contraintes_projet"]["budget"] == "50000"
        assert result["extraction"]["contraintes_projet"]["caution_provisoire"] == "3%"
