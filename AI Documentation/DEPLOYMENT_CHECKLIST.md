# BOQ AI Assistant - Deployment Checklist

## Pre-Deployment Checks

### ✅ Files Created (25 files)

#### Infrastructure
- [x] `docker-compose.yml`
- [x] `setup-ai-services.bat`
- [x] `setup-ai-services.sh`

#### Backend - AI Module (5 files)
- [x] `be/AI/__init__.py`
- [x] `be/AI/agent.py`
- [x] `be/AI/ollama_client.py`
- [x] `be/AI/vectorstore.py`
- [x] `be/AI/rag_engine.py`
- [x] `be/AI/tools.py`

#### Backend - API Routes (3 files)
- [x] `be/APIs/AI/__init__.py`
- [x] `be/APIs/AI/ChatRoute.py`
- [x] `be/APIs/AI/DocumentRoute.py`

#### Backend - Models (2 files)
- [x] `be/Models/AI/__init__.py`
- [x] `be/Models/AI/Document.py` (✅ Fixed: metadata → chunk_metadata)

#### Backend - Schemas (2 files)
- [x] `be/Schemas/AI/__init__.py`
- [x] `be/Schemas/AI/ChatSchemas.py`

#### Backend - Configuration (2 files)
- [x] `be/requirements-ai.txt`
- [x] `be/main.py` (✅ Updated with AI routes)

#### Database Migration (1 file)
- [x] `be/alembic/versions/a068c6bdfd26_*.py` (✅ Fixed: metadata → chunk_metadata)

#### Frontend Components (3 files)
- [x] `fe/src/AIComponents/ChatInterface.jsx`
- [x] `fe/src/AIComponents/ChatButton.jsx`
- [x] `fe/src/AIComponents/DocumentUpload.jsx`

#### Frontend Styles (2 files)
- [x] `fe/src/css/ChatInterface.css`
- [x] `fe/src/css/DocumentUpload.css`

#### Documentation (6 files)
- [x] `AI_INTEGRATION_README.md`
- [x] `QUICK_START_AI.md`
- [x] `AI_IMPLEMENTATION_SUMMARY.md`
- [x] `AI_ARCHITECTURE_DIAGRAM.md`
- [x] `TROUBLESHOOTING.md`
- [x] `FIX_APPLIED.md`

---

## Deployment Steps

### Step 1: Docker Services Setup
```bash
[ ] cd C:\WORK\BOQ
[ ] Run setup-ai-services.bat
[ ] Wait for model download (~10 minutes)
[ ] Verify: docker ps (should show 4 containers)
```

**Verification:**
```bash
docker ps
# Should see: boq-ollama, boq-qdrant, boq-redis, boq-n8n
```

### Step 2: Backend Dependencies
```bash
[ ] cd C:\WORK\BOQ\be
[ ] pip install -r requirements-ai.txt
[ ] Verify installations completed
```

**Verification:**
```bash
pip list | grep -E "ollama|qdrant|sentence-transformers"
```

### Step 3: Database Migration
```bash
[ ] cd C:\WORK\BOQ\be
[ ] alembic upgrade head
[ ] Check for errors
```

**Verification:**
```sql
-- Connect to MSSQL and run:
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('documents', 'document_chunks', 'chat_history', 'ai_actions');
-- Should return 4 rows
```

### Step 4: Frontend Integration
```bash
[ ] Open fe/src/App.jsx
[ ] Add: import ChatButton from './AIComponents/ChatButton';
[ ] Add: <ChatButton /> in return statement
[ ] Save file
```

**Example:**
```jsx
import ChatButton from './AIComponents/ChatButton';

function App() {
  return (
    <div className="App">
      {/* Existing components */}

      {/* AI Chat Button - Add at the end */}
      <ChatButton />
    </div>
  );
}
```

### Step 5: Start Application
```bash
# Terminal 1: Backend
[ ] cd C:\WORK\BOQ\be
[ ] python main.py
[ ] Wait for "Application startup complete"

# Terminal 2: Frontend
[ ] cd C:\WORK\BOQ\fe
[ ] npm run dev
[ ] Wait for "Local: http://localhost:5173"
```

---

## Testing Checklist

### Basic Functionality
```bash
[ ] Open http://localhost:5173
[ ] Verify chat button appears (bottom-right, purple)
[ ] Click chat button
[ ] Chat interface opens
[ ] Type "Hello" and send
[ ] Receive response within 5-10 seconds
```

### Project Creation Test
```bash
[ ] In chat, type: "Create a new BOQ project called Test Project with PO-2025-TEST"
[ ] AI should respond with success message
[ ] Check database: SELECT * FROM projects WHERE project_name = 'Test Project'
[ ] Verify project exists
```

### Document Upload Test
```bash
[ ] Prepare a sample PDF file
[ ] Navigate to document upload (or use DocumentUpload component)
[ ] Upload PDF
[ ] Check "Auto-extract tags"
[ ] Upload
[ ] Wait for processing (~20-30 seconds)
[ ] Check status shows "completed"
```

### Document Q&A Test
```bash
[ ] After document is processed
[ ] In chat, ask: "What does the uploaded document say?"
[ ] Should get answer with citations
[ ] Verify sources are shown
```

### Search Test
```bash
[ ] In chat, type: "Search for all projects"
[ ] Should return list of projects
[ ] Verify data is correct
```

---

## System Health Checks

### Docker Services
```bash
✓ docker ps
  → 4 containers running

✓ docker stats
  → Memory usage < 8GB
  → CPU usage reasonable

✓ docker logs boq-ollama | tail -20
  → No errors

✓ docker logs boq-qdrant | tail -20
  → No errors
```

### Backend Health
```bash
✓ curl http://localhost:8003/docs
  → Swagger UI loads

✓ Check /ai/chat is listed
  → Yes, endpoint exists

✓ Check /ai/documents is listed
  → Yes, endpoint exists

✓ Backend logs show no errors
  → Check terminal output
```

### Frontend Health
```bash
✓ http://localhost:5173 loads
  → Application runs

✓ Browser console (F12) shows no errors
  → No red errors

✓ Chat button visible
  → Purple button bottom-right

✓ CSS loaded correctly
  → Button looks styled
```

### Database Health
```sql
✓ SELECT COUNT(*) FROM documents;
  → Returns count (even if 0)

✓ SELECT COUNT(*) FROM chat_history;
  → Returns count (even if 0)

✓ SELECT COUNT(*) FROM ai_actions;
  → Returns count (even if 0)

✓ Check alembic_version
  → Should be: a068c6bdfd26
```

### Qdrant Health
```bash
✓ curl http://localhost:6333/health
  → {"status": "ok"}

✓ curl http://localhost:6333/collections/boq_documents
  → Returns collection info
```

---

## Performance Baselines

Record these metrics for monitoring:

### Initial Response Times
```
First chat message (cold start): _____ seconds (expect: 5-10s)
Subsequent messages: _____ seconds (expect: 2-5s)
Document upload (1 page PDF): _____ seconds (expect: 10-20s)
Document search: _____ seconds (expect: <1s)
RAG Q&A: _____ seconds (expect: 3-7s)
```

### Resource Usage
```
Ollama container memory: _____ GB (expect: 4-6GB)
Qdrant container memory: _____ GB (expect: 0.5-1GB)
Total Docker memory: _____ GB (expect: 6-8GB)
CPU usage during inference: _____ % (expect: 20-30%)
```

---

## Post-Deployment Monitoring

### Day 1
- [ ] Monitor error rates in backend logs
- [ ] Check docker logs for any crashes
- [ ] Verify user adoption (check chat_history table)
- [ ] Test with real user scenarios

### Week 1
- [ ] Review ai_actions table for failures
- [ ] Check average response times
- [ ] Gather user feedback
- [ ] Optimize slow queries if needed

### Month 1
- [ ] Clean old conversations (>30 days)
- [ ] Backup Qdrant data
- [ ] Review and analyze usage patterns
- [ ] Plan enhancements based on feedback

---

## Rollback Plan

If critical issues occur:

### Quick Disable (No Data Loss)
```bash
# Stop AI services only
docker-compose down

# Keep backend running (AI endpoints will error gracefully)
```

### Full Rollback
```bash
# 1. Stop Docker services
docker-compose down

# 2. Remove AI routes from main.py
# Comment out:
# from APIs.AI import chat_router, document_router
# app.include_router(chat_router)
# app.include_router(document_router)

# 3. Rollback database
cd C:\WORK\BOQ\be
alembic downgrade -1

# 4. Remove chat button from frontend
# Comment out <ChatButton /> in App.jsx

# 5. Restart application normally
```

**Data preserved:**
- Uploaded documents (in uploads/documents/)
- Chat history (in database)
- Can re-enable later

---

## Success Criteria

Deployment is successful when:

- [x] All 4 Docker containers running
- [x] Backend starts without errors
- [x] Frontend displays chat button
- [x] Chat responds within 10 seconds
- [x] Document upload works
- [x] RAG Q&A returns answers
- [x] Function calls execute correctly
- [x] No errors in logs
- [x] Database tables created
- [x] Vector search works

---

## Common First-Run Issues

### "Model not found"
```bash
docker exec boq-ollama ollama pull llama3.1:8b
```

### "Qdrant connection refused"
```bash
docker restart boq-qdrant
# Wait 10 seconds
```

### "Chat button not appearing"
- Clear browser cache (Ctrl + Shift + Delete)
- Check App.jsx has `<ChatButton />` imported and rendered
- Check browser console for errors

### "Database migration failed"
```bash
# Check current version
alembic current

# Try again
alembic upgrade head
```

---

## Final Verification Script

Run this to verify everything:

```bash
# Check Docker
echo "Checking Docker..."
docker ps | grep -E "ollama|qdrant|redis|n8n" && echo "✓ Docker OK" || echo "✗ Docker FAIL"

# Check Ollama
echo "Checking Ollama..."
docker exec boq-ollama ollama list | grep llama && echo "✓ Ollama OK" || echo "✗ Ollama FAIL"

# Check Qdrant
echo "Checking Qdrant..."
curl -s http://localhost:6333/health | grep -q "ok" && echo "✓ Qdrant OK" || echo "✗ Qdrant FAIL"

# Check Backend
echo "Checking Backend..."
curl -s http://localhost:8003/docs | grep -q "Swagger" && echo "✓ Backend OK" || echo "✗ Backend FAIL"

# Check Frontend
echo "Checking Frontend..."
curl -s http://localhost:5173 | grep -q "html" && echo "✓ Frontend OK" || echo "✗ Frontend FAIL"

echo ""
echo "If all checks show ✓, system is ready!"
```

---

## Sign-Off

- [ ] All files created and verified
- [ ] Docker services running
- [ ] Database migrated
- [ ] Dependencies installed
- [ ] Backend running
- [ ] Frontend running
- [ ] Basic tests passed
- [ ] Documentation reviewed
- [ ] Ready for production use

**Deployed by:** _________________
**Date:** _________________
**Sign-off:** _________________

---

**Next Steps After Deployment:**
1. Read [QUICK_START_AI.md](QUICK_START_AI.md) for usage examples
2. Share [AI_INTEGRATION_README.md](AI_INTEGRATION_README.md) with team
3. Monitor logs for first 24 hours
4. Gather user feedback
5. Plan Phase 2 enhancements

🎉 **Congratulations!** Your BOQ AI Assistant is ready to use!
