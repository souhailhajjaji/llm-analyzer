import pytest
from analyzer import analyser_cahier, CahierDesChargesAnalyzer


class TestAnalyseRegles:
    """Tests pour l'analyseur de règles locales"""

    def test_aucun_probleme(self):
        """Test avec un texte sans problèmes"""
        texte = """
        Cahier des charges - Application simple
        
        - Inscription avec email validé
        - Authentification avec mot de passe hashé
        - Rôles: admin peut gérer les utilisateurs
        - Les prix sont calculés côté serveur
        """
        result = analyser_cahier(texte)
        assert result["resume"]["total_problemes"] == 0

    def test_api_sans_auth(self):
        """Détection API sans authentification"""
        texte = "L'API est accessible sans authentification"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "sans authentification" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_mots_passe_en_clair(self):
        """Détection mots de passe en clair"""
        texte = "Les mots de passe sont stockés en clair"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if p["categorie"] == "SECURITE"]
        assert len(problemes) >= 1

    def test_base64(self):
        """Détection Base64"""
        texte = "Les mots de passe sont chiffrés avec Base64"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if p["categorie"] == "SECURITE"]
        assert len(problemes) >= 1

    def test_sessions_infinies(self):
        """Détection sessions infinies"""
        texte = "Les sessions n'expirent jamais pour éviter la reconnexion"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "session" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_contradiction_roles(self):
        """Détection contradiction rôles (sans doublon)"""
        texte = """
        Un utilisateur peut avoir plusieurs rôles
        Un utilisateur ne peut avoir qu'un seul rôle
        """
        result = analyser_cahier(texte)
        contradictions = [p for p in result["problemes"] if p["categorie"] == "CONTRADICTION"]
        assert len(contradictions) >= 1

    def test_rgpd(self):
        """Détection problèmes RGPD"""
        texte = "Les données personnelles peuvent être revendues à des partenaires"
        result = analyser_cahier(texte)
        legals = [p for p in result["problemes"] if p["categorie"] == "LEGAL"]
        assert len(legals) >= 1

    def test_prix_cote_client(self):
        """Détection prix côté client"""
        texte = "Le prix total est calculé côté client pour affichage rapide"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "prix" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_extraction_fonctionnalites(self):
        """Test extraction des fonctionnalités"""
        texte = """
        - Inscription des utilisateurs
        - Authentification par mot de passe
        - Gestion des produits
        - Paiement par carte bancaire
        """
        result = analyser_cahier(texte)
        fonctionnel = result["extraction"]["functionalites"]
        assert len(fonctionnel) >= 3

    def test_extraction_acteurs(self):
        """Test extraction des acteurs"""
        texte = """
        Utilisateurs: clients et administrateurs
        """
        result = analyser_cahier(texte)
        acteurs = result["extraction"]["acteurs"]
        assert len(acteurs) >= 1

    def test_resume_compte_bien(self):
        """Test que le résumé compte bien les problèmes"""
        texte = """
        API sans authentification
        Mots de passe en clair
        Sessions n'expirent jamais
        """
        result = analyser_cahier(texte)
        resume = result["resume"]
        assert resume["total_problemes"] == resume["critiques"] + resume["eleves"] + resume["moyens"] + resume["faibles"]


class TestCahierDesChargesAnalyzer:
    """Tests pour la classe Analyzer"""

    def test_initialisation(self):
        """Test initialisation"""
        analyzer = CahierDesChargesAnalyzer()
        assert analyzer.api_token is None
        assert analyzer.use_ollama is True

    def test_initialisation_avec_token(self):
        """Test initialisation avec token"""
        analyzer = CahierDesChargesAnalyzer(api_token="test_token")
        assert analyzer.api_token == "test_token"
        assert "Authorization" in analyzer.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
