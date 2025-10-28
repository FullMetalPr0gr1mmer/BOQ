#!/bin/bash
# Setup script for BOQ AI Services

echo "=========================================="
echo "BOQ AI Services Setup"
echo "=========================================="

# Start Docker Compose services
echo "Starting Docker services..."
docker-compose up -d

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
sleep 10

# Pull the Llama 3.1 model (8B version - good balance of performance and size)
echo "Pulling Llama 3.1 model (this may take several minutes)..."
docker exec boq-ollama ollama pull llama3.1:8b

# Alternative: Pull Mistral if you want a smaller/faster model
# docker exec boq-ollama ollama pull mistral:7b

# Verify Ollama is working
echo "Testing Ollama..."
docker exec boq-ollama ollama run llama3.1:8b "Hello, respond with just 'OK'"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - Ollama: http://localhost:11434"
echo "  - Qdrant: http://localhost:6333/dashboard"
echo "  - Redis: localhost:6379"
echo "  - n8n: http://localhost:5678 (user: admin, password: admin123)"
echo ""
echo "Next steps:"
echo "  1. Install Python dependencies: pip install -r be/requirements-ai.txt"
echo "  2. Run database migrations: alembic upgrade head"
echo "  3. Start FastAPI backend: cd be && python main.py"
echo ""
