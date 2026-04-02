"""
Interface Streamlit pour l'analyse de cahier des charges
Déployable gratuitement sur Hugging Face Spaces
"""

import streamlit as st
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from analyzer import analyser_cahier

load_dotenv(Path(__file__).parent / ".env")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

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
    
    categories = {
        "SECURITE": "🔐 Sécurité",
        "CONTRADICTION": "⚠️ Contradiction",
        "AMBIGUITE": "❓ Ambiguïté",
        "LEGAL": "⚖️ Légal",
        "EDGE_CASE": "🔄 Edge Case"
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
    """Affiche les éléments extraits"""
    
    extraction = result.get("extraction", {})
    
    if not any(extraction.values()):
        return
    
    st.divider()
    st.subheader("📦 Éléments Extraits")
    
    cols = st.columns(3)
    
    with cols[0]:
        st.markdown("### 🎯 Fonctionnalités")
        for f in extraction.get("functionalites", []):
            st.write(f"- {f}")
    
    with cols[1]:
        st.markdown("### 👤 Acteurs")
        for a in extraction.get("acteurs", []):
            st.write(f"- {a}")
    
    with cols[2]:
        st.markdown("### ⚡ Contraintes")
        for c in extraction.get("contraintes", []):
            st.write(f"- {c}")
    
    cols2 = st.columns(2)
    
    with cols2[0]:
        st.markdown("### 🖥️ Interfaces")
        for i in extraction.get("interfaces", []):
            st.write(f"- {i}")
    
    with cols2[1]:
        st.markdown("### 💾 Données")
        for d in extraction.get("donnees", []):
            st.write(f"- {d}")


def main():
    st.title("📋 Analyseur de Cahier des Charges")
    st.markdown("""
    Cet outil analyse votre cahier des charges et détecte:
    - 🔴 Contradictions
    - 🔐 Problèmes de sécurité
    - ⚖️ Problèmes légaux (RGPD)
    - ❓ Ambiguïtés
    - 🔄 Edge cases manquants
    """)
    
    st.sidebar.header("⚙️ Configuration")
    
    use_llm = st.sidebar.toggle("Utiliser Llama (HuggingFace)", value=False, help="Cochez pour utiliser le LLM, sinon uniquement rule-based")
    
    api_token = st.sidebar.text_input(
        "Token Hugging Face",
        type="password",
        help="Entrez votre token HF pour utiliser Llama"
    )
    
    st.sidebar.markdown("""
    ---
    **Toggle OFF**: Analyse rule-based rapide (29 règles)
    **Toggle ON**: Analyse avec Llama 3.2 (plus lent)
    
    Obtenir un token gratuit sur:
    [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    """)
    
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
..."""
    )
    
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
            token = api_token if api_token else HF_TOKEN
            result = analyser_cahier(texte, token if token else None, use_huggingface=use_llm)
            
            afficher_problemes(result)
            afficher_extraction(result)
            
            st.divider()
            
            with st.expander("📄 Voir la réponse JSON brute"):
                st.json(result)
    
    elif analyze_btn and not texte:
        st.warning("Veuillez coller un cahier des charges à analyser")


if __name__ == "__main__":
    main()
