# BOQ AI Assistant - Implementation Guide

## Overview

This AI integration adds an intelligent assistant to your BOQ application that can:
- **Understand natural language** and execute actions within the application
- **Create and manage projects** (BOQ, RAN, ROP) through conversation
- **Process and analyze PDF documents** using RAG (Retrieval-Augmented Generation)
- **Answer questions** based on uploaded project documents
- **Search and analyze** project data intelligently
- **Auto-categorize documents** using AI-extracted tags

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Services                           │
├─────────────────────────────────────────────────────────────┤
│  Ollama (localhost:11434)    - Local LLM (llama3.1:8b)      │
│  Qdrant (localhost:6333)     - Vector database              │
│  Redis (localhost:6379)      - Task queue & caching         │
│  n8n (localhost:5678)        - Workflow automation          │
└─────────────────────────────────────────────────────────────┘
         ↓                             ↓
┌─────────────────────────────────────────────────────────────┐
│               FastAPI Backend (localhost:8003)               │
├─────────────────────────────────────────────────────────────┤
│  AI Module:                                                  │
│    - agent.py         - Main AI orchestrator                │
│    - tools.py         - Function calling tools              │
│    - rag_engine.py    - Document Q&A                        │
│    - ollama_client.py - LLM interface                       │
│    - vectorstore.py   - Qdrant integration                  │
│                                                              │
│  API Routes:                                                 │
│    - /ai/chat         - Conversational interface            │
│    - /ai/documents    - Document management                 │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│               React Frontend (localhost:5173)                │
├─────────────────────────────────────────────────────────────┤
│  - ChatInterface.jsx  - Chat UI component                   │
│  - ChatButton.jsx     - Floating chat button                │
│  - DocumentUpload.jsx - PDF upload interface                │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Docker Desktop installed and running
- Python 3.9+ (already installed for BOQ backend)
- Node.js 18+ (already installed for BOQ frontend)
- At least 8GB RAM available
- 10GB free disk space (for AI models)

### Step 1: Start AI Services

**Windows:**
```bash
# Navigate to BOQ directory
cd C:\WORK\BOQ

# Run setup script
setup-ai-services.bat
```

**Linux/Mac:**
```bash
# Navigate to BOQ directory
cd /c/WORK/BOQ

# Make script executable
chmod +x setup-ai-services.sh

# Run setup script
./setup-ai-services.sh
```

This will:
1. Start Docker containers (Ollama, Qdrant, Redis, n8n)
2. Pull the Llama 3.1 8B model (~4.7GB download)
3. Initialize all services

**Verify services are running:**
```bash
docker ps
```

You should see 4 containers running:
- `boq-ollama`
- `boq-qdrant`
- `boq-redis`
- `boq-n8n`

### Step 2: Install Python Dependencies

```bash
cd C:\WORK\BOQ\be

# Install AI-specific dependencies
pip install -r requirements-ai.txt
```

### Step 3: Run Database Migration

```bash
cd C:\WORK\BOQ\be

# Apply migration to create AI tables
alembic upgrade head
```

This creates 4 new tables:
- `documents` - Uploaded document metadata
- `document_chunks` - Text chunks with vector IDs
- `chat_history` - Conversation history
- `ai_actions` - Audit log of AI actions

### Step 4: Start Backend

```bash
cd C:\WORK\BOQ\be
python main.py
```

The backend should start on `http://localhost:8003`

### Step 5: Update Frontend

The frontend components are already created. You need to integrate them into your main app.

**Edit `fe/src/App.jsx`:**

```jsx
import ChatButton from './AIComponents/ChatButton';

function App() {
  // ... existing code ...

  return (
    <div className="App">
      {/* Your existing components */}

      {/* Add AI chat button - it will appear on all pages */}
      <ChatButton projectContext={currentProjectContext} />
    </div>
  );
}
```

**For project-specific pages**, pass project context:

```jsx
// In Project.jsx, for example
<ChatButton
  projectContext={{
    type: 'boq',
    id: projectId
  }}
/>
```

### Step 6: Start Frontend

```bash
cd C:\WORK\BOQ\fe
npm install  # Install any new dependencies
npm run dev
```

Frontend should start on `http://localhost:5173`

## Usage

### 1. Chat with AI Assistant

Click the floating chat button (bottom-right corner) to open the AI assistant.

**Example conversations:**

```
User: Create a new BOQ project called "Toronto 5G Deployment" with PO number PO-2025-001

AI: I've created the BOQ project "Toronto 5G Deployment" with PO-2025-001.
    Project ID: 123. What would you like to add to it?

User: Search for sites in Toronto

AI: I found 15 sites in Toronto:
    - Toronto-North-Cell-1
    - Toronto-South-Cell-2
    ...

User: Add inventory item for Toronto-North-Cell-1

AI: I can help you add inventory. Please provide:
    - Equipment type
    - Serial number
    - Status
```

### 2. Upload and Query Documents

**Upload a PDF:**

1. Click "Documents" in your navigation
2. Use the upload component to select a PDF
3. Enable "Auto-extract tags" option
4. Upload

The AI will:
- Extract all text from the PDF
- Split into searchable chunks
- Generate embeddings and store in Qdrant
- Auto-generate tags (e.g., "technical_spec", "antenna", "5G")
- Create a summary

**Ask questions about documents:**

```
User: What are the antenna specifications in the technical document?

AI: According to the technical specification (page 12), the antenna
    specifications are:
    - Frequency: 2.6 GHz
    - Gain: 18 dBi
    - Connector: 4.3-10 Female

    [Source: technical_spec_v2.pdf, Page 12]
```

### 3. Available AI Functions

The AI can call these functions automatically:

**Project Management:**
- `create_boq_project` - Create BOQ project
- `create_ran_project` - Create RAN project
- `create_rop_project` - Create ROP project
- `search_projects` - Search across all projects
- `get_project_summary` - Get project details

**Site & Inventory:**
- `fetch_sites` - List sites with filters
- `add_inventory_item` - Add inventory
- `search_inventory` - Search inventory

**Data Analysis:**
- `analyze_project_pricing` - Pricing analysis
- `compare_projects` - Side-by-side comparison

## API Endpoints

### Chat Endpoints

**POST /ai/chat**
```json
{
  "message": "Create a new project called Test",
  "conversation_id": "optional-uuid",
  "project_context": {
    "type": "boq",
    "id": 123
  }
}
```

Response:
```json
{
  "response": "I've created the project...",
  "conversation_id": "uuid",
  "actions_taken": ["create_boq_project"],
  "data": { "project_id": 456 }
}
```

**GET /ai/conversations/{conversation_id}**
- Retrieve conversation history

**GET /ai/conversations**
- List all user's conversations

**DELETE /ai/conversations/{conversation_id}**
- Delete conversation

### Document Endpoints

**POST /ai/documents/upload**
- Upload document (multipart/form-data)
- Fields: `file`, `project_type`, `project_id`, `auto_process`, `extract_tags`

**GET /ai/documents/**
- List uploaded documents
- Query params: `project_type`, `project_id`, `limit`

**GET /ai/documents/{document_id}**
- Get document details

**DELETE /ai/documents/{document_id}**
- Delete document and embeddings

**POST /ai/documents/search**
```json
{
  "query": "antenna specifications",
  "project_id": 123,
  "tags": ["technical_spec"],
  "limit": 10,
  "threshold": 0.7
}
```

**POST /ai/documents/ask**
```json
{
  "question": "What are the cable specifications?",
  "project_id": 123
}
```

**GET /ai/documents/tags/all**
- Get all unique tags with counts

## Configuration

### Ollama Model

Default model: `llama3.1:8b`

To change model:

```bash
# Pull a different model
docker exec boq-ollama ollama pull mistral:7b

# Edit be/AI/ollama_client.py
DEFAULT_MODEL = "mistral:7b"
```

**Recommended models:**
- `llama3.1:8b` - Best overall (4.7GB)
- `mistral:7b` - Faster, smaller (4.1GB)
- `phi3:medium` - Lightweight (7.9GB but very efficient)

### Vector Database

Qdrant dashboard: `http://localhost:6333/dashboard`

View collections, vector counts, and search directly.

### n8n Workflows

n8n UI: `http://localhost:5678`
- Username: `admin`
- Password: `admin123`

Create workflows for:
- Scheduled reports
- Email notifications
- External integrations (Slack, Teams, etc.)

## Performance Tuning

### For GPU Acceleration

If you have an NVIDIA GPU, uncomment in `docker-compose.yml`:

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

Restart: `docker-compose up -d`

### Chunk Size Tuning

Edit `be/AI/rag_engine.py`:

```python
CHUNK_SIZE = 500  # Increase for longer context
CHUNK_OVERLAP = 100  # Increase for better continuity
```

### Search Threshold

Lower threshold = more results (less accurate)
Higher threshold = fewer results (more accurate)

Default: 0.7 (good balance)

## Troubleshooting

### Ollama not responding

```bash
# Check container logs
docker logs boq-ollama

# Restart Ollama
docker restart boq-ollama

# Verify model is pulled
docker exec boq-ollama ollama list
```

### Qdrant connection error

```bash
# Check Qdrant is running
docker ps | grep qdrant

# View logs
docker logs boq-qdrant

# Restart
docker restart boq-qdrant
```

### Backend errors

Check logs in terminal where you ran `python main.py`

Common issues:
- Missing dependencies: `pip install -r requirements-ai.txt`
- Database not migrated: `alembic upgrade head`
- Qdrant not accessible: Check Docker containers

### Frontend not showing chat button

1. Check browser console for errors
2. Verify API is running on `localhost:8003`
3. Check CORS settings in `be/main.py`
4. Ensure ChatButton is imported and rendered

## Security

### Authentication

All AI endpoints require JWT authentication (same as existing BOQ endpoints).

### Permissions

AI respects existing role-based access control:
- Users can only access projects they have permissions for
- Actions are logged in `ai_actions` table
- Destructive operations require confirmation

### Data Privacy

- All AI processing is **local** (Ollama runs on your machine)
- No data is sent to external APIs
- Documents are stored locally in `uploads/documents/`
- Vector embeddings stored in local Qdrant instance

### Audit Trail

Every AI action is logged:
- User ID
- Action type
- Parameters
- Result
- Timestamp
- Execution time

Query audit log:
```sql
SELECT * FROM ai_actions
WHERE user_id = 1
ORDER BY timestamp DESC;
```

## Advanced Features

### Custom Function Tools

Add new capabilities by editing `be/AI/tools.py`:

```python
@staticmethod
def get_function_schemas():
    return [
        # ... existing functions ...
        {
            "name": "my_custom_function",
            "description": "Does something awesome",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            }
        }
    ]

@staticmethod
def my_custom_function(db: Session, user_id: int, **kwargs):
    # Implement function logic
    return {"success": True, "result": "Done!"}
```

### n8n Workflow Integration

Example: Weekly project summary email

1. Open n8n: `http://localhost:5678`
2. Create new workflow
3. Add schedule trigger (every Monday 9 AM)
4. Add HTTP request to `/ai/chat`:
   ```json
   {
     "message": "Summarize all projects updated this week"
   }
   ```
5. Add email node with response
6. Activate workflow

### Multi-turn Conversations

The AI maintains context across messages in a conversation:

```
User: Search for projects in Ontario
AI: Found 25 projects in Ontario...

User: Which ones are RAN projects?
AI: Of the 25 projects, 12 are RAN projects...

User: Show me the top 3 by budget
AI: Here are the top 3 RAN projects in Ontario by budget...
```

## Monitoring

### Check Service Health

```bash
# All services status
docker-compose ps

# Resource usage
docker stats

# Qdrant statistics
curl http://localhost:6333/collections/boq_documents
```

### Monitor AI Actions

SQL query for AI usage analytics:

```sql
-- Actions per user
SELECT u.username, COUNT(*) as action_count
FROM ai_actions a
JOIN users u ON a.user_id = u.id
GROUP BY u.username
ORDER BY action_count DESC;

-- Most used functions
SELECT action_type, COUNT(*) as count
FROM ai_actions
WHERE status = 'success'
GROUP BY action_type
ORDER BY count DESC;

-- Average execution time
SELECT action_type, AVG(execution_time_ms) as avg_ms
FROM ai_actions
GROUP BY action_type;
```

## Maintenance

### Backup Vector Database

```bash
# Backup Qdrant data
docker run --rm -v boq_qdrant-data:/data -v $(pwd):/backup ubuntu tar czf /backup/qdrant-backup.tar.gz /data
```

### Clear Chat History

```sql
-- Delete old conversations (older than 30 days)
DELETE FROM chat_history
WHERE timestamp < NOW() - INTERVAL 30 DAY;
```

### Update Ollama Model

```bash
# Pull latest version
docker exec boq-ollama ollama pull llama3.1:8b

# Restart to use new version
docker restart boq-ollama
```

## Cost Estimation

**Infrastructure costs:** $0 (all runs locally)

**Resource requirements:**
- CPU: ~20-30% during inference
- RAM: ~6-8GB (4GB for model + 2-4GB overhead)
- Disk: ~10GB (models + data)
- GPU: Optional (5-10x faster inference)

**Processing times (CPU):**
- Chat response: 2-5 seconds
- PDF processing (10 pages): 20-30 seconds
- Document search: <1 second
- Question answering: 3-7 seconds

**Processing times (GPU):**
- Chat response: 0.5-1 second
- PDF processing (10 pages): 5-10 seconds
- Document search: <1 second
- Question answering: 1-2 seconds

## Support

For issues or questions:
1. Check logs: `docker logs boq-ollama`, `docker logs boq-qdrant`
2. Review backend logs (FastAPI terminal output)
3. Check browser console for frontend errors
4. Verify all services are running: `docker ps`

## Future Enhancements

Potential additions:
- Voice input/output
- Multi-modal AI (images, diagrams)
- Advanced analytics dashboards
- Integration with external tools (Excel, AutoCAD)
- Fine-tuned models for BOQ-specific terminology
- Automated report generation
- Predictive project planning

---

**Version:** 1.0.0
**Last Updated:** 2025-10-22
**Author:** Claude AI Assistant
