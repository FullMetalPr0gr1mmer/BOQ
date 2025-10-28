# Troubleshooting Guide - BOQ AI Assistant

## Common Issues and Solutions

### 1. SQLAlchemy Error: "Attribute name 'metadata' is reserved"

**Error:**
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API
```

**Solution:**
✅ **FIXED** - The column has been renamed from `metadata` to `chunk_metadata` in:
- `Models/AI/Document.py`
- `alembic/versions/a068c6bdfd26_*.py`
- `AI/rag_engine.py`

If you see this error, run:
```bash
cd C:\WORK\BOQ\be
alembic downgrade -1  # Undo last migration if already applied
alembic upgrade head  # Apply with fix
```

---

### 2. Docker Container Not Starting

**Error:**
```
Error response from daemon: driver failed programming external connectivity
```

**Solution:**
```bash
# Stop all containers
docker-compose down

# Check if ports are in use
netstat -ano | findstr :11434
netstat -ano | findstr :6333
netstat -ano | findstr :6379
netstat -ano | findstr :5678

# Kill process using port (replace PID)
taskkill /PID <pid> /F

# Restart
docker-compose up -d
```

---

### 3. Ollama Model Not Found

**Error:**
```
Error: model 'llama3.1:8b' not found
```

**Solution:**
```bash
# Check available models
docker exec boq-ollama ollama list

# Pull model if missing
docker exec boq-ollama ollama pull llama3.1:8b

# Verify
docker exec boq-ollama ollama run llama3.1:8b "Hello"
```

**Alternative smaller model:**
```bash
docker exec boq-ollama ollama pull mistral:7b
```
Then update `be/AI/ollama_client.py`:
```python
DEFAULT_MODEL = "mistral:7b"
```

---

### 4. Qdrant Connection Error

**Error:**
```
ConnectionError: Cannot connect to Qdrant at localhost:6333
```

**Solution:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# View logs
docker logs boq-qdrant

# Restart Qdrant
docker restart boq-qdrant

# Wait 10 seconds, then test
curl http://localhost:6333/health
```

If port 6333 is blocked, change in `docker-compose.yml`:
```yaml
qdrant:
  ports:
    - "6334:6333"  # Use different host port
```

Then update `be/AI/vectorstore.py`:
```python
def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6334):
```

---

### 5. Database Migration Failed

**Error:**
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**Solution:**
```bash
cd C:\WORK\BOQ\be

# Check current revision
alembic current

# Check history
alembic history

# Upgrade to latest
alembic upgrade head

# If it fails, check logs
alembic upgrade head --sql  # Preview SQL without executing
```

**Manual fix if needed:**
```sql
-- Connect to MSSQL and check
SELECT * FROM alembic_version;

-- If stuck, manually update revision
UPDATE alembic_version SET version_num = 'a068c6bdfd26';
```

---

### 6. Import Errors in Backend

**Error:**
```
ModuleNotFoundError: No module named 'ollama'
ModuleNotFoundError: No module named 'qdrant_client'
```

**Solution:**
```bash
cd C:\WORK\BOQ\be

# Install AI dependencies
pip install -r requirements-ai.txt

# Verify installations
pip list | grep ollama
pip list | grep qdrant
pip list | grep sentence-transformers
```

**If using virtual environment:**
```bash
# Activate venv first
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Then install
pip install -r requirements-ai.txt
```

---

### 7. Frontend Chat Button Not Appearing

**Problem:** Chat button doesn't show on frontend

**Solution:**

1. **Check if ChatButton is imported:**
```jsx
// In fe/src/App.jsx
import ChatButton from './AIComponents/ChatButton';
```

2. **Check if it's rendered:**
```jsx
function App() {
  return (
    <div className="App">
      {/* Your existing components */}

      <ChatButton />  {/* Add this */}
    </div>
  );
}
```

3. **Check browser console for errors (F12)**
```
Look for:
- Import errors
- API connection errors
- CORS errors
```

4. **Verify CSS is loaded:**
```jsx
// Check if these exist
fe/src/css/ChatInterface.css
fe/src/css/DocumentUpload.css
```

5. **Clear browser cache:**
```
Ctrl + Shift + Delete (Chrome/Edge)
Or hard refresh: Ctrl + F5
```

---

### 8. CORS Error in Browser Console

**Error:**
```
Access to XMLHttpRequest at 'http://localhost:8003/ai/chat'
from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solution:**

Check `be/main.py` has correct CORS configuration:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Restart backend after changes:
```bash
cd C:\WORK\BOQ\be
python main.py
```

---

### 9. API Returns 401 Unauthorized

**Error:**
```json
{"detail": "Not authenticated"}
```

**Solution:**

1. **Check if user is logged in:**
   - Frontend should have JWT token in localStorage
   - Open browser console: `localStorage.getItem('token')`

2. **Login again:**
   - Go to login page
   - Login with valid credentials
   - Token should be stored automatically

3. **Check API client configuration (`fe/src/api.js`):**
```javascript
// Should have interceptor that adds token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

### 10. Chat Response Very Slow (>30 seconds)

**Problem:** AI takes too long to respond

**Causes & Solutions:**

**1. First run (model loading):**
- First request loads model into memory (~5-10 seconds)
- Subsequent requests are faster

**2. CPU bottleneck:**
- Check CPU usage during inference
- Consider:
  - Switching to smaller model (mistral:7b)
  - Adding GPU acceleration
  - Reducing context size

**3. Switch to smaller/faster model:**
```bash
docker exec boq-ollama ollama pull mistral:7b
```
Update `be/AI/ollama_client.py`:
```python
DEFAULT_MODEL = "mistral:7b"
```

**4. Enable GPU (NVIDIA only):**

Uncomment in `docker-compose.yml`:
```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

Restart:
```bash
docker-compose down
docker-compose up -d
```

---

### 11. Document Upload Fails

**Error:**
```json
{"detail": "Unsupported file type"}
```

**Solution:**

1. **Check file extension is allowed:**
   - `.pdf` ✅
   - `.docx` ✅
   - `.doc` ✅
   - `.txt` ✅
   - Others ❌

2. **Check file size:**
   - Default max: Check `be/main.py` or FastAPI config
   - If too large, increase limit

3. **Check file permissions:**
   - Ensure `uploads/documents/` folder exists
   - Check write permissions

**Create upload directory manually:**
```bash
mkdir -p C:\WORK\BOQ\be\uploads\documents
```

---

### 12. Vector Search Returns No Results

**Problem:** Document Q&A says "no relevant information found"

**Causes & Solutions:**

**1. Document not processed:**
```bash
# Check document status in database
SELECT id, filename, processing_status FROM documents;
```
Status should be `completed`, not `pending` or `failed`.

**2. Qdrant collection empty:**
```bash
# Check Qdrant
curl http://localhost:6333/collections/boq_documents
```
Should show `points_count > 0`.

**3. Threshold too high:**
In `be/AI/rag_engine.py`, lower threshold:
```python
search_results = self.search_documents(
    query=query,
    limit=5,
    score_threshold=0.5  # Lower from 0.7
)
```

**4. Re-process document:**
- Delete document via API
- Upload again
- Check processing completes

---

### 13. Background Task Not Running

**Problem:** Document uploaded but never processes

**Check:**

1. **View backend logs:**
   - Look for "Background processing error"
   - Check stack trace

2. **Common causes:**
   - PDF library not installed: `pip install pypdf pdfplumber`
   - Qdrant not reachable
   - Sentence-transformers model not downloaded

3. **Manual processing:**
```python
# In Python shell
from AI import get_rag_engine
from Database.session import SessionLocal

db = SessionLocal()
rag = get_rag_engine()

rag.process_document(
    file_path="path/to/file.pdf",
    document_id=123,
    db=db,
    extract_tags=True
)
```

---

### 14. Memory Issues (Out of Memory)

**Error:**
```
docker: Error response from daemon: OCI runtime create failed
```

**Solution:**

1. **Increase Docker memory:**
   - Docker Desktop → Settings → Resources
   - Increase Memory to 8GB+

2. **Use smaller model:**
```bash
docker exec boq-ollama ollama pull phi3:mini  # 2.3GB
```

3. **Close other applications**

4. **Monitor memory:**
```bash
docker stats
```

---

### 15. Function Call Failed

**Problem:** AI says it executed action but nothing happened

**Debug:**

1. **Check ai_actions table:**
```sql
SELECT * FROM ai_actions
WHERE status = 'failed'
ORDER BY timestamp DESC;
```

2. **Look at error_message column**

3. **Common issues:**
   - Permission denied (user doesn't have access)
   - Invalid parameters
   - Database constraint violation

4. **Test function directly:**
```python
# In Python shell
from AI.tools import BOQTools
from Database.session import SessionLocal

db = SessionLocal()
tools = BOQTools()

result = tools.create_boq_project(
    db=db,
    user_id=1,
    project_name="Test",
    po="PO-123"
)
print(result)
```

---

## Quick Diagnostic Commands

### Check All Services
```bash
# Docker services
docker ps

# Backend health (if implemented)
curl http://localhost:8003/health

# Qdrant health
curl http://localhost:6333/health

# Ollama models
docker exec boq-ollama ollama list
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker logs boq-ollama
docker logs boq-qdrant
docker logs boq-redis
docker logs boq-n8n

# Backend (in terminal where it runs)
# Should see FastAPI startup and request logs
```

### Database Checks
```sql
-- Check AI tables exist
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('documents', 'document_chunks', 'chat_history', 'ai_actions');

-- Check document processing
SELECT id, filename, processing_status, processing_error
FROM documents
ORDER BY upload_date DESC;

-- Check conversation count
SELECT COUNT(DISTINCT conversation_id) as total_conversations
FROM chat_history;

-- Check action success rate
SELECT
  status,
  COUNT(*) as count,
  AVG(execution_time_ms) as avg_time_ms
FROM ai_actions
GROUP BY status;
```

---

## Getting Help

If you encounter an issue not covered here:

1. **Check logs** (most important!)
   - Backend terminal output
   - Docker logs: `docker logs boq-ollama`
   - Browser console (F12)

2. **Verify setup:**
   - All Docker containers running
   - Database migration applied
   - Dependencies installed
   - Frontend components imported

3. **Test components individually:**
   - Ollama: `docker exec boq-ollama ollama list`
   - Qdrant: `curl http://localhost:6333/health`
   - Backend: `curl http://localhost:8003/docs`
   - Frontend: Check browser console

4. **Common fixes that solve 80% of issues:**
   ```bash
   # Restart everything
   docker-compose down
   docker-compose up -d

   cd be
   pip install -r requirements-ai.txt
   alembic upgrade head
   python main.py

   cd ../fe
   npm install
   npm run dev
   ```

---

**Still stuck?** Create an issue with:
- Error message (full stack trace)
- Logs from backend and Docker
- Steps to reproduce
- Your environment (OS, Python version, Docker version)
