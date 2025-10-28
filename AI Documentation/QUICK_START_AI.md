# Quick Start Guide - BOQ AI Assistant

## 5-Minute Setup

### 1. Start AI Services (One-time setup)

**Windows:**
```bash
cd C:\WORK\BOQ
setup-ai-services.bat
```

**Mac/Linux:**
```bash
cd /c/WORK/BOQ
chmod +x setup-ai-services.sh
./setup-ai-services.sh
```

Wait ~5-10 minutes for model download (4.7GB).

### 2. Install Dependencies & Migrate Database

```bash
cd C:\WORK\BOQ\be
pip install -r requirements-ai.txt
alembic upgrade head
```

### 3. Start Backend

```bash
cd C:\WORK\BOQ\be
python main.py
```

### 4. Update Frontend (One-time)

Edit `fe/src/App.jsx` and add:

```jsx
import ChatButton from './AIComponents/ChatButton';

// Inside your App component's return statement:
<ChatButton />
```

### 5. Start Frontend

```bash
cd C:\WORK\BOQ\fe
npm run dev
```

## First Steps

### Open Chat
Click the purple floating button (bottom-right corner)

### Try These Commands

1. **Create a project:**
   ```
   Create a new BOQ project called "Test Project" with PO number PO-2025-TEST
   ```

2. **Search:**
   ```
   Search for all projects in Ontario
   ```

3. **Upload a PDF:**
   - Click "Documents" or use the upload component
   - Select a PDF file
   - Enable "Auto-extract tags"
   - Upload

4. **Ask about documents:**
   ```
   What are the specifications mentioned in the uploaded document?
   ```

5. **Analyze data:**
   ```
   Show me a summary of project ID 123
   ```

## Verify Everything Works

### Check Services
```bash
docker ps
```
You should see 4 containers running.

### Test Ollama
```bash
docker exec boq-ollama ollama list
```
Should show `llama3.1:8b`.

### Test API
Open browser: `http://localhost:8003/docs`

You should see Swagger UI with `/ai/chat` and `/ai/documents` endpoints.

### Test Chat
1. Open frontend: `http://localhost:5173`
2. Click chat button
3. Type "Hello"
4. You should get a response within 2-5 seconds

## Troubleshooting

**"Ollama not responding"**
```bash
docker restart boq-ollama
```

**"Model not found"**
```bash
docker exec boq-ollama ollama pull llama3.1:8b
```

**"Database error"**
```bash
cd C:\WORK\BOQ\be
alembic upgrade head
```

**"Chat button not visible"**
- Check browser console for errors
- Verify you imported and added `<ChatButton />` to App.jsx
- Clear browser cache

## Next Steps

Read the full documentation: [AI_INTEGRATION_README.md](AI_INTEGRATION_README.md)

## What Can the AI Do?

✅ Create projects (BOQ, RAN, ROP)
✅ Search projects, sites, inventory
✅ Upload and process PDFs
✅ Answer questions about documents
✅ Analyze pricing and data
✅ Compare projects
✅ Generate summaries
✅ Auto-categorize documents with tags

## Example Conversations

**Create and populate a project:**
```
User: Create a new RAN project called "Toronto Metro 5G"
AI: Created RAN project "Toronto Metro 5G" (ID: 45)

User: Add 20 antennas to this project
AI: I can help add inventory. What's the site name?

User: Toronto-North-Cell-1
AI: Added inventory item for Toronto-North-Cell-1
```

**Document analysis:**
```
User: Upload technical_specs.pdf
AI: Document uploaded. Found 15 pages. Auto-generated tags:
    technical_spec, antenna, 5G, installation

User: What are the antenna specifications?
AI: According to technical_specs.pdf (page 7):
    - Frequency: 2.6 GHz
    - Gain: 18 dBi
    - Connector: 4.3-10 Female
```

**Data insights:**
```
User: Compare pricing between project 10 and project 20
AI: Project 10: Total $1.2M, 500 items
    Project 20: Total $980K, 450 items
    Project 20 has better cost efficiency...
```

---

**Need help?** Check the logs:
- Backend: Terminal where you ran `python main.py`
- Docker: `docker logs boq-ollama`
- Frontend: Browser console (F12)
