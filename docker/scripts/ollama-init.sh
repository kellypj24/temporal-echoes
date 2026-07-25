#!/bin/bash
# Ollama initialization script for Temporal Echoes
# Starts Ollama and optionally pulls required models

set -e

echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "Ollama is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Ollama failed to start"
        exit 1
    fi
    sleep 2
done

# Pull models if AUTO_PULL_MODELS is set
if [ "${AUTO_PULL_MODELS:-false}" = "true" ]; then
    echo "Auto-pulling models..."
    
    # Pull Llama 3.2 (primary model)
    if [ "${PULL_LLAMA32:-true}" = "true" ]; then
        echo "Pulling llama3.2:3b..."
        ollama pull llama3.2:3b || echo "Warning: Failed to pull llama3.2:3b"
    fi
    
    # Pull Gemma 3 (alternative model)
    if [ "${PULL_GEMMA3:-false}" = "true" ]; then
        echo "Pulling gemma3:4b..."
        ollama pull gemma3:4b || echo "Warning: Failed to pull gemma3:4b"
    fi
    
    echo "Model pulling complete!"
else
    echo "Skipping auto-pull. Set AUTO_PULL_MODELS=true to enable."
    echo "To manually pull models:"
    echo "  docker exec temporal-echoes-ollama ollama pull llama3.2:3b"
fi

echo "Ollama is ready for Temporal Echoes!"

# Keep Ollama running
wait $OLLAMA_PID

