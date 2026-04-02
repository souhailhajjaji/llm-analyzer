import os
import pytest
from analyzer import analyser_cahier, CahierDesChargesAnalyzer


class TestAnalyseRegles:
    """Tests pour l'analyseur de règles locales"""

    HF_TOKEN = os.environ.get("HF_TOKEN", "")

    def test_avec_huggingface(self):
        """Test avec l'API Hugging Face"""
        texte = "Les mots de passe sont stockés en clair"
        result = analyser_cahier(texte, api_token=self.HF_TOKEN, use_huggingface=True)
        assert result["resume"]["total_problemes"] >= 1

    def test_contradiction_detection(self):
        """Détection de contradictions sémantiques"""
        texte = """
        Un utilisateur peut avoir plusieurs rôles
        Un utilisateur ne peut avoir qu'un seul rôle
        """
        result = analyser_cahier(texte, analyse_avancee=True)
        assert len(result["analyse_avancee"]["contradictions"]) >= 1

    def test_completude_analysis(self):
        """Analyse de complétude du cahier des charges"""
        texte = "Description du projet"
        result = analyser_cahier(texte, analyse_avancee=True)
        assert "completude_score" in result["resume"]

    def test_qualite_analysis(self):
        """Analyse de qualité du document"""
        texte = """
        Cahier des charges - Projet complet
        
        1. Description
        Nous développons une API avec JWT et chiffrement.
        
        2. Fonctionnalités
        - Inscription utilisateur
        - Authentification par token
        
        3. Sécurité
        - Les mots de passe sont hashés avec bcrypt
        - Sessions avec expiration
        """
        result = analyser_cahier(texte, analyse_avancee=True)
        assert "score_qualite" in result["analyse_avancee"]["qualite"]

    def test_cross_reference_validation(self):
        """Validation des références croisées"""
        texte = """
        Les données des utilisateurs sont stockées en base de données.
        Le système de paiement traite les cartes bancaires.
        """
        result = analyser_cahier(texte, analyse_avancee=True)
        assert len(result["analyse_avancee"]["references"]) >= 1

    def test_aucun_probleme(self):
        """Test avec un texte sans problèmes"""
        texte = """
        Cahier des charges - Application simple
        
        - Inscription avec email validé
        - Authentification avec mot de passe hashé
        - Rôles: admin peut gérer les utilisateurs
        - Les prix sont calculés côté serveur
        """
        result = analyser_cahier(texte, use_huggingface=False)
        assert result["resume"]["total_problemes"] == 0

    def test_api_sans_auth(self):
        """Détection API sans authentification"""
        texte = "L'API est accessible sans authentification"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "sans authentification" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_mots_passe_en_clair(self):
        """Détection mots de passe en clair"""
        texte = "Les mots de passe sont stockés en clair"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if p["categorie"] == "SECURITE"]
        assert len(problemes) >= 1

    def test_base64(self):
        """Détection Base64"""
        texte = "Les mots de passe sont chiffrés avec Base64"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if p["categorie"] == "SECURITE"]
        assert len(problemes) >= 1

    def test_sessions_infinies(self):
        """Détection sessions infinies"""
        texte = "Les sessions n'expirent jamais pour éviter la reconnexion"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "session" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_contradiction_roles(self):
        """Détection contradiction rôles (sans doublon)"""
        texte = """
        Un utilisateur peut avoir plusieurs rôles
        Un utilisateur ne peut avoir qu'un seul rôle
        """
        result = analyser_cahier(texte, use_huggingface=False)
        contradictions = [p for p in result["problemes"] if p["categorie"] == "CONTRADICTION"]
        assert len(contradictions) >= 1

    def test_rgpd(self):
        """Détection problèmes RGPD"""
        texte = "Les données personnelles peuvent être revendues à des partenaires"
        result = analyser_cahier(texte, use_huggingface=False)
        legals = [p for p in result["problemes"] if p["categorie"] == "LEGAL"]
        assert len(legals) >= 1

    def test_donnees_non_chiffrees(self):
        """Détection données non chiffrées"""
        texte = "Les données médicales sont stockées sans chiffrement"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "chiffr" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_api_ouverte(self):
        """Détection API ouverte"""
        texte = "API ouverte pour les partenaires externes"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "api" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_acces_sans_autorisation(self):
        """Détection accès sans autorisation"""
        texte = "Tous les utilisateurs ont accès complet"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "accès" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_secret_medical(self):
        """Détection secret médical"""
        texte = "Pas de mention du secret médical"
        result = analyser_cahier(texte, use_huggingface=False)
        legals = [p for p in result["problemes"] if p["categorie"] == "LEGAL"]
        assert len(legals) >= 1

    def test_edge_case_non_traite(self):
        """Détection edge case non traité"""
        texte = "Que se passe-t-il si le médecin n'est pas disponible?"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "non traité" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_sauvegarde_non_chiffree(self):
        """Détection sauvegardes non chiffrées"""
        texte = "Sauvegardes non chiffrées"
        result = analyser_cahier(texte, use_huggingface=False)
        problemes = [p for p in result["problemes"] if "sauvegarde" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_prix_cote_client(self):
        """Détection prix côté client"""
        texte = "Le prix total est calculé côté client pour affichage rapide"
        result = analyser_cahier(texte, use_huggingface=False)
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
        result = analyser_cahier(texte, use_huggingface=False)
        fonctionnel = result["extraction"]["functionalites"]
        assert len(fonctionnel) >= 3

    def test_extraction_acteurs(self):
        """Test extraction des acteurs"""
        texte = """
        Utilisateurs: clients et administrateurs
        """
        result = analyser_cahier(texte, use_huggingface=False)
        acteurs = result["extraction"]["acteurs"]
        assert len(acteurs) >= 1

    def test_resume_compte_bien(self):
        """Test que le résumé compte bien les problèmes"""
        texte = """
        API sans authentification
        Mots de passe en clair
        Sessions n'expirent jamais
        """
        result = analyser_cahier(texte, use_huggingface=False)
        resume = result["resume"]
        assert resume["total_problemes"] == resume["critiques"] + resume["eleves"] + resume["moyens"] + resume["faibles"]

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

    def test_donnees_non_chiffrees(self):
        """Détection données non chiffrées"""
        texte = "Les données médicales sont stockées sans chiffrement"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "chiffr" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_api_ouverte(self):
        """Détection API ouverte"""
        texte = "API ouverte pour les partenaires externes"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "api" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_acces_sans_autorisation(self):
        """Détection accès sans autorisation"""
        texte = "Tous les utilisateurs ont accès complet"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "accès" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_secret_medical(self):
        """Détection secret médical"""
        texte = "Pas de mention du secret médical"
        result = analyser_cahier(texte)
        legals = [p for p in result["problemes"] if p["categorie"] == "LEGAL"]
        assert len(legals) >= 1

    def test_edge_case_non_traite(self):
        """Détection edge case non traité"""
        texte = "Que se passe-t-il si le médecin n'est pas disponible?"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "non traité" in p["titre"].lower()]
        assert len(problemes) >= 1

    def test_sauvegarde_non_chiffree(self):
        """Détection sauvegardes non chiffrées"""
        texte = "Sauvegardes non chiffrées"
        result = analyser_cahier(texte)
        problemes = [p for p in result["problemes"] if "sauvegarde" in p["titre"].lower()]
        assert len(problemes) >= 1

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
        analyzer = CahierDesChargesAnalyzer(use_huggingface=False)
        assert analyzer.api_token is not None  # Default token set
        assert analyzer.use_ollama is False
        assert analyzer.use_huggingface is False

    def test_initialisation_avec_token(self):
        """Test initialisation avec token"""
        analyzer = CahierDesChargesAnalyzer(api_token="test_token", use_huggingface=False)
        assert analyzer.api_token == "test_token"
        assert "Authorization" in analyzer.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
