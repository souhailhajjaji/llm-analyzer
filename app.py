"""
Interface Streamlit pour l'analyse de cahier des charges
Déployable gratuitement sur Hugging Face Spaces
"""

import streamlit as st
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
from analyzer import analyser_cahier
from src.services.document_extractor import DocumentExtractor
from src.services.llm_analyzer import AnalyzerWithFallback
from src.core.config import settings

load_dotenv(Path(__file__).parent / ".env")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

if "history" not in st.session_state:
    st.session_state.history = []

if "current_result" not in st.session_state:
    st.session_state.current_result = None

st.set_page_config(
    page_title="Analyseur de Cahier des Charges",
    page_icon="📋",
    layout="wide"
)


def afficher_problemes(result: dict):
    """Affiche les problèmes détectés"""
    
    if "erreur" in result:
        st.error(f"Erreur: {result['erreur']}")
        return
    
    resume = result.get("resume", {})
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Problèmes", resume.get("total_problemes", 0))
    with col2:
        st.metric("Critiques", resume.get("critiques", 0), delta_color="inverse")
    with col3:
        st.metric("Élevés", resume.get("eleves", 0), delta_color="inverse")
    with col4:
        st.metric("Moyens", resume.get("moyens", 0), delta_color="inverse")
    with col5:
        st.metric("Faibles", resume.get("faibles", 0), delta_color="normal")
    
    st.divider()
    
    probleme_colors = {
        "CRITIQUE": "🔴",
        "ELEVEE": "🟠",
        "MOYENNE": "🟡",
        "FAIBLE": "🟢"
    }
    
    probleme_colors.update({
        "COMPLETUDE": "📋",
        "QUALITE": "✨",
        "RISQUE": "⚠️"
    })
    
    categories = {
        "SECURITE": "🔐 Sécurité",
        "CONTRADICTION": "⚠️ Contradiction",
        "AMBIGUITE": "❓ Ambiguïté",
        "LEGAL": "⚖️ Légal",
        "EDGE_CASE": "🔄 Edge Case",
        "COMPLETUDE": "📋 Complétude",
        "QUALITE": "✨ Qualité",
        "RISQUE": "⚠️ Risque"
    }
    
    problemes = result.get("problemes", [])
    
    if not problemes:
        st.success("Aucun problème détecté ! 🎉")
        return
    
    for p in problemes:
        severity = p.get("severite", "MOYENNE")
        emoji = probleme_colors.get(severity, "🟡")
        cat = categories.get(p.get("categorie", ""), p.get("categorie", ""))
        
        with st.expander(f"{emoji} {p.get('titre', 'Problème')}"):
            st.markdown(f"**Catégorie:** {cat}")
            st.markdown(f"**Sévérité:** {severity}")
            st.markdown(f"**Localisation:** {p.get('localisation', 'Non spécifiée')}")
            st.markdown(f"**Description:** {p.get('description', '')}")
            st.markdown(f"**Recommandation:** {p.get('recommendation', '')}")


def afficher_extraction(result: dict):
    """Affiche les elements extraits"""

    extraction = result.get("extraction", {})

    if not extraction:
        st.warning("⚠️ Aucune donnée extraite. Le document ne contient peut-être pas les informations attendues.")
        return

    st.divider()
    st.subheader("📦 Elements Extraits")

    # Check if extraction had parsing errors
    if extraction.get("error"):
        st.warning(f"⚠️ Erreur d'extraction: {extraction.get('error')}")
        st.info("Les valeurs ci-dessous proviennent de l'extraction regex de secours.")

    meta = extraction.get("metadonnees", {})
    contraintes = extraction.get("contraintes_projet", {})
    dossier = extraction.get("dossier_reponse", {})

    # Check for garbled data warning
    has_garbled = False
    for section_key in ["administratif", "technique", "financier"]:
        for item in dossier.get(section_key, []):
            if len(item) > 200:
                has_garbled = True
                break

    if has_garbled:
        st.info("💡 Certaines données du dossier de réponse sont longues et peuvent contenir du texte non structuré.")

    cols = st.columns(2)

    with cols[0]:
        st.markdown("### 📋 Metadonnees")
        if meta.get("nom_client"):
            st.markdown(f"**Nom client:** {meta['nom_client']}")
        else:
            st.markdown("**Nom client:** ❌ Non défini")
        if meta.get("objet"):
            st.markdown(f"**Objet:** {meta['objet']}")
        else:
            st.markdown("**Objet:** ❌ Non défini")
        if meta.get("objectifs"):
            st.markdown("**Objectifs:**")
            for o in meta["objectifs"]:
                st.write(f"- {o}")
        else:
            st.markdown("**Objectifs:** ❌ Non définis")
        if meta.get("orientations_technologiques"):
            st.markdown("**Orientations technologiques:**")
            for t in meta["orientations_technologiques"]:
                st.write(f"- {t}")
        else:
            st.markdown("**Orientations technologiques:** ⚠️ Non définies")

    with cols[1]:
        st.markdown("### ⏰ Contraintes Projet")
        if contraintes.get("date_limite_soumission"):
            st.markdown(f"**Date limite:** {contraintes['date_limite_soumission']}")
        else:
            st.markdown("**Date limite:** ❌ Non définie")
        if contraintes.get("budget"):
            st.markdown(f"**Budget:** {contraintes['budget']}")
        else:
            st.markdown("**Budget:** ❌ Non défini")
        if contraintes.get("caution_provisoire"):
            st.markdown(f"**Caution provisoire:** {contraintes['caution_provisoire']}")
        else:
            st.markdown("**Caution provisoire:** ⚠️ Non définie")
        if contraintes.get("delai_execution"):
            st.markdown(f"**Delai execution:** {contraintes['delai_execution']}")
        else:
            st.markdown("**Delai execution:** ❌ Non défini")

    # Dossier de Reponse - with garbled data filtering
    if dossier.get("administratif") or dossier.get("technique") or dossier.get("financier"):
        st.markdown("### 📁 Dossier de Reponse")
        cols2 = st.columns(3)

        with cols2[0]:
            st.markdown("**Administratif:**")
            items = [a for a in dossier.get("administratif", []) if len(a) < 200]
            if items:
                for a in items:
                    st.write(f"- {a}")
            else:
                st.write("_(aucun élément court trouvé)_")

        with cols2[1]:
            st.markdown("**Technique:**")
            items = [t for t in dossier.get("technique", []) if len(t) < 200]
            if items:
                for t in items:
                    st.write(f"- {t}")
            else:
                st.write("_(aucun élément court trouvé)_")

        with cols2[2]:
            st.markdown("**Financier:**")
            items = [f for f in dossier.get("financier", []) if len(f) < 200]
            if items:
                for f in items:
                    st.write(f"- {f}")
            else:
                st.write("_(aucun élément court trouvé)_")

    cols3 = st.columns(3)

    with cols3[0]:
        st.markdown("### 📚 References")
        refs = extraction.get("references", [])
        if refs:
            for r in refs:
                st.write(f"- {r}")
        else:
            st.write("_(aucune référence trouvée)_")

    with cols3[1]:
        st.markdown("### ✅ Exigences")
        exigs = extraction.get("exigences", [])
        if exigs:
            for e in exigs:
                st.write(f"- {e}")
        else:
            st.write("_(aucune exigence trouvée)_")

    with cols3[2]:
        st.markdown("### 💳 Modalites Paiement")
        modalites = extraction.get("modalites_paiement", [])
        if modalites:
            for p in modalites:
                st.write(f"- {p}")
        else:
            st.write("_(aucune modalité trouvée)_")


def main():
    st.title("📋 Analyseur de Cahier des Charges - Extraction")
    st.markdown("Cet outil extrait les metadonnees de votre cahier des charges.")
    
    st.sidebar.header("⚙️ Configuration")
    
    use_llm = st.sidebar.toggle("Utiliser Llama", value=False, help="Cochez pour utiliser le LLM")
    
    api_token = st.sidebar.text_input(
        "Token Hugging Face",
        type="password",
        help="Entrez votre token HF pour utiliser Llama"
    )
    
    st.sidebar.markdown("""
    ---
    **Toggle OFF**: Analyse rule-based rapide
    **Toggle ON**: Analyse avec Llama 3.2
    
    Obtenir un token sur:
    [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    """)

    tab1, tab2 = st.tabs(["📝 Coller le texte", "📁 Télécharger .docx"])

    with tab1:
        texte = st.text_area(
            "Collez votre cahier des charges ici:",
            height=300,
            placeholder="""Cahier des charges - Système de gestion des utilisateurs

🎯 2. Objectifs fonctionnels
- Permettre aux utilisateurs de s'inscrire
- Permettre aux utilisateurs de se connecter
...

🔐 5. Exigences de sécurité
- Les mots de passe sont stockés en clair
...""",
            label_visibility="collapsed"
        )

    with tab2:
        uploaded_file = st.file_uploader(
            "Choisissez un fichier (.docx ou .pdf)",
            type=["docx", "pdf"],
            help="Téléchargez un fichier Word ou PDF contenant le cahier des charges"
        )
        
        if uploaded_file is not None:
            try:
                extractor = DocumentExtractor()
                file_bytes = BytesIO(uploaded_file.getvalue())
                doc = extractor.extract(file_bytes, filename=uploaded_file.name)
                texte = doc.full_text
                st.success(f"✅ Fichier chargé: {uploaded_file.name}")
                with st.expander("👀 Aperçu du contenu"):
                    st.text(texte[:1000] + "..." if len(texte) > 1000 else texte)
            except Exception as e:
                st.error(f"Erreur lors de l'extraction: {e}")
                texte = ""
        else:
            st.info("Téléchargez un fichier .docx pour l'analyser")
            texte = ""
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        analyze_btn = st.button("🔍 Analyser", type="primary", use_container_width=True)
    
    with col2:
        example_btn = st.button("📝 Charger un exemple", use_container_width=True)
    
    if example_btn:
        st.session_state.example_loaded = True
    
    if "example_loaded" in st.session_state:
        st.code("""Cahier des charges - Système de gestion des utilisateurs

🎯 2. Objectifs fonctionnels
- Permettre aux utilisateurs de s'inscrire
- Permettre aux utilisateurs de se connecter
- Gérer les rôles (Admin / User)

📋 3. Exigences fonctionnelles
🔹 3.1 Inscription
- Email unique
- Mot de passe min 8 caractères
- Pas de chiffres requis

🔹 3.2 Authentification
- Pas de limite de tentatives
- Verrouillage après 3 tentatives (CONTRADICTION!)

🔹 3.3 Gestion des rôles
- Deux rôles: Admin et User
- Un utilisateur peut avoir plusieurs rôles
- Un utilisateur ne peut avoir qu'un seul rôle (CONTRADICTION!)

🔹 3.4 Accès aux ressources
- Seul Admin peut supprimer
- Tous peuvent modifier leurs données
- Un utilisateur peut modifier les données des autres (FACHE!)

🔹 3.5 Suppression
- Suppression de compte
- Données conservées pour audit (RGPD?)

🔐 5. Sécurité
- Mots de passe stockés en clair (CRITIQUE!)
- Sessions n'expirent jamais (CRITIQUE!)
- API sans authentification (CRITIQUE!)
- Pas de validation des entrées (CRITIQUE!)""", language="markdown")
    
    if analyze_btn and texte:
        with st.spinner("Analyse en cours..."):
            # Use more text to capture all CPS info (delay, caution are later in document)
            max_chars = 15000
            texte_truncated = texte[:max_chars] if len(texte) > max_chars else texte
            
            # Try LLM first, fall back to rule-based on any error
            try:
                analyzer = AnalyzerWithFallback()
                extraction = analyzer.extract_entities(texte_truncated)
                analysis = analyzer.analyze_document(texte_truncated)
                result = {
                    "extraction": extraction.get("extraction", {}),
                    "problemes": analysis.get("problemes", []),
                    "resume": analysis.get("resume", {
                        "total_problemes": len(analysis.get("problemes", [])),
                        "critiques": sum(1 for p in analysis.get("problemes", []) if p.get("severite") == "CRITIQUE"),
                        "eleves": sum(1 for p in analysis.get("problemes", []) if p.get("severite") == "ELEVEE"),
                        "moyens": sum(1 for p in analysis.get("problemes", []) if p.get("severite") == "MOYENNE"),
                        "faibles": sum(1 for p in analysis.get("problemes", []) if p.get("severite") == "FAIBLE"),
                    }),
                }
            except Exception as e:
                # Fall back to rule-based analysis
                st.warning(f"⚠️ LLM rate-limited, utilisation de l'analyse rule-based")
                result = analyser_cahier(texte, None, use_huggingface=False)
            
            extraction = result.get("extraction", {})
            meta = extraction.get("metadonnees", {}) if extraction else {}
            
            history_item = {
                "id": len(st.session_state.history) + 1,
                "nom_client": meta.get("nom_client", "Non défini"),
                "objet": meta.get("objet", "Non défini"),
                "total_problemes": result.get("resume", {}).get("total_problemes", 0),
                "result": result,
                "timestamp": None
            }
            st.session_state.history.insert(0, history_item)
            if len(st.session_state.history) > 10:
                st.session_state.history = st.session_state.history[:10]
            
            st.session_state.current_result = result
            afficher_problemes(result)
            afficher_extraction(result)
            
            st.divider()
            
            with st.expander("📄 Voir la réponse JSON brute"):
                st.json(result)
    
    elif analyze_btn and not texte:
        st.warning("Veuillez coller un cahier des charges à analyser")
    
    if st.session_state.history:
        st.sidebar.divider()
        with st.sidebar.expander("📜 Historique des analyses", expanded=False):
            for i, item in enumerate(st.session_state.history):
                if st.button(f"#{item['id']} - {(item['nom_client'] or 'Non défini')[:20]}... ({item['total_problemes']} pb)", key=f"history_{i}"):
                    st.session_state.current_result = item["result"]
                st.caption(f"Objet: {(item['objet'] or 'Non défini')[:30]}...")
                st.divider()


if __name__ == "__main__":
    main()
