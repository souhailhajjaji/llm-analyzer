#!/bin/bash

set -e

echo "=== Ollama Setup ==="

MODEL=${1:-llama3.2}

# Check if Ollama is already running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama est déjà en cours d'exécution"
else
    echo "Démarrage d'Ollama..."
    
    # Try to start Ollama via Docker if available
    if command -v docker &> /dev/null; then
        echo "Utilisation de Docker pour Ollama..."
        docker run -d --name ollama --network host \
            -v ollama-data:/root/.ollama \
            ollama/ollama:latest || true
        sleep 5
    else
        echo "Docker non disponible. Veuillez installer Ollama manuellement:"
        echo "  https://ollama.ai"
        exit 1
    fi
fi

# Pull the model if not already installed
echo "Vérification du modèle $MODEL..."
if docker exec ollama ollama list | grep -q "$MODEL"; then
    echo "Modèle $MODEL déjà installé"
else
    echo "Téléchargement du modèle $MODEL..."
    docker exec ollama ollama pull $MODEL
    echo "Modèle $MODEL installé"
fi

# Test the connection
echo "Test de connexion..."
response=$(curl -s http://localhost:11434/api/tags)
if echo "$response" | grep -q "$MODEL"; then
    echo -e "\n=== Ollama est prêt ! ==="
    echo "Modèle: $MODEL"
    echo "API: http://localhost:11434"
else
    echo "Erreur: impossible de se connecter à Ollama"
    exit 1
fi
