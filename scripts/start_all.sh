#!/bin/bash

echo "=== Démarrage des services ==="

# Démarrer Ollama (Docker)
echo "[1/3] Vérification Ollama..."
if docker ps | grep -q ollama; then
    echo "  - Ollama (Docker) déjà en cours"
elif docker ps -a | grep -q ollama; then
    docker start ollama
    echo "  - Ollama (Docker) démarré"
else
    echo "  - Installation de Ollama requise"
    exit 1
fi

# Attendre qu'Ollama soit prêt
sleep 2
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  - Ollama connecté"
else
    echo "  - Erreur: Ollama non accessible"
    exit 1
fi

# Démarrer l'API
echo "[2/3] Vérification API..."
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  - API déjà en cours sur port 8000"
else
    echo "  - Démarrage de l'API..."
    source venv/bin/activate
    nohup uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
    sleep 3
fi

# Vérification finale
echo "[3/3] Vérification finale..."
HEALTH=$(curl -s http://localhost:8000/api/health)
echo "  - Health: $HEALTH"

echo ""
echo "=== Services démarrés ==="
echo "  - API: http://localhost:8000"
echo "  - Ollama: http://localhost:11434"
echo ""
echo "Endpoints:"
echo "  - Health: curl http://localhost:8000/api/health"
echo "  - Analyser: curl -X POST -F 'file=@file.docx' http://localhost:8000/api/analyze"
