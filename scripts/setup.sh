#!/bin/bash

set -e

echo "=== Cahier Charges Analyzer - Setup ==="

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Vérifier Python
echo -e "${YELLOW}Vérification de Python...${NC}"
python3 --version

# 2. Créer l'environnement virtuel
echo -e "${YELLOW}Création de l'environnement virtuel...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Environnement virtuel créé${NC}"
else
    echo -e "${GREEN}Environnement virtuel déjà existant${NC}"
fi

# 3. Activer l'environnement
echo -e "${YELLOW}Activation de l'environnement...${NC}"
source venv/bin/activate

# 4. Installer les dépendances
echo -e "${YELLOW}Installation des dépendances...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}Dépendances installées${NC}"

# 5. Créer les dossiers
echo -e "${YELLOW}Création des dossiers...${NC}"
mkdir -p uploads
echo -e "${GREEN}dossiers créés${NC}"

echo -e "${GREEN}=== Setup terminé ! ===${NC}"
echo ""
echo "Pour démarrer l'API:"
echo "  source venv/bin/activate"
echo "  uvicorn src.api.main:app --reload"
