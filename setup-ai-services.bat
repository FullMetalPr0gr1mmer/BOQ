@echo off
REM Setup script for BOQ AI Services (Windows)

echo ==========================================
echo BOQ AI Services Setup
echo ==========================================
echo.

REM Start Docker Compose services
echo Starting Docker services...
docker-compose up -d

REM Wait for Ollama to be ready
echo Waiting for Ollama to start...
timeout /t 10 /nobreak >nul

REM Pull the Llama 3.1 model (8B version)
echo Pulling Llama 3.1 model (this may take several minutes)...
docker exec boq-ollama ollama pull llama3.1:8b

REM Alternative: Pull Mistral for smaller/faster model
REM docker exec boq-ollama ollama pull mistral:7b

REM Verify Ollama is working
echo Testing Ollama...
docker exec boq-ollama ollama run llama3.1:8b "Hello, respond with just 'OK'"

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Services running:
echo   - Ollama: http://localhost:11434
echo   - Qdrant: http://localhost:6333/dashboard
echo   - Redis: localhost:6379
echo   - n8n: http://localhost:5678 (user: admin, password: admin123)
echo.
echo Next steps:
echo   1. Install Python dependencies: pip install -r be\requirements-ai.txt
echo   2. Run database migrations: alembic upgrade head
echo   3. Start FastAPI backend: cd be ^&^& python main.py
echo.
pause
