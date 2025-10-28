# BOQ AI Assistant - Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER INTERACTION LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  Chat Interface  │  │ Document Upload  │  │  Quick Actions   │         │
│  │  (ChatButton)    │  │  Component       │  │  (Suggestions)   │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
│           │                     │                      │                    │
│           └─────────────────────┴──────────────────────┘                    │
│                                 │                                           │
│                        React Frontend (Port 5173)                           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                    HTTP/REST     │
                    (axios)       │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FastAPI Backend (Port 8003)                                                │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Authentication Middleware (JWT)                                   │    │
│  │  ├─ Verify token                                                   │    │
│  │  ├─ Check user permissions                                         │    │
│  │  └─ Load user context                                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────┐         ┌─────────────────────┐                   │
│  │  /ai/chat           │         │  /ai/documents      │                   │
│  │  ├─ POST /chat      │         │  ├─ POST /upload    │                   │
│  │  ├─ GET /convs/{id} │         │  ├─ GET /           │                   │
│  │  ├─ GET /convs      │         │  ├─ POST /search    │                   │
│  │  └─ DELETE /conv    │         │  ├─ POST /ask       │                   │
│  └──────────┬──────────┘         │  └─ GET /tags       │                   │
│             │                    └──────────┬──────────┘                    │
│             │                               │                               │
└─────────────┼───────────────────────────────┼───────────────────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI PROCESSING LAYER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        BOQAgent (agent.py)                         │    │
│  │  ┌──────────────────────────────────────────────────────────────┐ │    │
│  │  │  1. Receive user message                                      │ │    │
│  │  │  2. Load conversation history                                 │ │    │
│  │  │  3. Build context with project info                           │ │    │
│  │  │  4. Determine if function call or direct response needed      │ │    │
│  │  └──────────────────────────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│               │                                      │                       │
│        Direct Response                        Function Call                 │
│               │                                      │                       │
│               ▼                                      ▼                       │
│  ┌─────────────────────┐           ┌─────────────────────────────┐          │
│  │  OllamaClient       │           │  BOQTools (tools.py)        │          │
│  │  (ollama_client.py) │           │  ├─ create_boq_project      │          │
│  │                     │           │  ├─ create_ran_project      │          │
│  │  ├─ Generate text   │           │  ├─ search_projects         │          │
│  │  ├─ Chat            │           │  ├─ get_project_summary     │          │
│  │  ├─ Function call   │           │  ├─ fetch_sites             │          │
│  │  └─ Extract JSON    │           │  ├─ add_inventory_item      │          │
│  └──────────┬──────────┘           │  ├─ search_inventory        │          │
│             │                      │  ├─ analyze_pricing         │          │
│             │                      │  └─ compare_projects        │          │
│             │                      └───────────┬─────────────────┘          │
│             │                                  │                            │
│             │                                  │ Database                   │
│             │                                  │ Operations                 │
│             │                                  │                            │
└─────────────┼──────────────────────────────────┼────────────────────────────┘
              │                                  │
              │                                  │
              ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT INTELLIGENCE LAYER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    RAGEngine (rag_engine.py)                       │    │
│  │                                                                    │    │
│  │  Document Processing Pipeline:                                    │    │
│  │  ┌──────────────────────────────────────────────────────────────┐│    │
│  │  │ 1. Upload PDF/DOCX/TXT                                       ││    │
│  │  │ 2. Extract text (pypdf/pdfplumber/python-docx)               ││    │
│  │  │ 3. Chunk text (500 chars, 100 overlap)                       ││    │
│  │  │ 4. Generate embeddings (sentence-transformers)               ││    │
│  │  │ 5. Store in Qdrant + database                                ││    │
│  │  │ 6. Extract tags & summary (Ollama)                           ││    │
│  │  └──────────────────────────────────────────────────────────────┘│    │
│  │                                                                    │    │
│  │  Q&A Pipeline:                                                     │    │
│  │  ┌──────────────────────────────────────────────────────────────┐│    │
│  │  │ 1. Receive question                                          ││    │
│  │  │ 2. Generate question embedding                               ││    │
│  │  │ 3. Search Qdrant for similar chunks                          ││    │
│  │  │ 4. Retrieve top 5 chunks                                     ││    │
│  │  │ 5. Send chunks + question to LLM                             ││    │
│  │  │ 6. Generate answer with citations                            ││    │
│  │  └──────────────────────────────────────────────────────────────┘│    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────┐                                                    │
│  │  VectorStore        │                                                    │
│  │  (vectorstore.py)   │                                                    │
│  │                     │                                                    │
│  │  ├─ embed_text      │                                                    │
│  │  ├─ add_chunks      │                                                    │
│  │  ├─ search          │                                                    │
│  │  └─ delete_document │                                                    │
│  └──────────┬──────────┘                                                    │
│             │                                                                │
└─────────────┼────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INFRASTRUCTURE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Docker Compose Services:                                                   │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │   Ollama         │  │   Qdrant         │  │   Redis          │         │
│  │   (Port 11434)   │  │   (Port 6333)    │  │   (Port 6379)    │         │
│  │                  │  │                  │  │                  │         │
│  │  LLM Inference   │  │  Vector DB       │  │  Task Queue      │         │
│  │  ├─ llama3.1:8b  │  │  ├─ Embeddings   │  │  ├─ Async jobs   │         │
│  │  ├─ Chat         │  │  ├─ Similarity   │  │  └─ Caching      │         │
│  │  └─ Functions    │  │  └─ Collections  │  │                  │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
│                                                                              │
│  ┌──────────────────┐                                                       │
│  │   n8n            │                                                       │
│  │   (Port 5678)    │                                                       │
│  │                  │                                                       │
│  │  Workflows       │                                                       │
│  │  ├─ Scheduled    │                                                       │
│  │  ├─ Webhooks     │                                                       │
│  │  └─ Integrations │                                                       │
│  └──────────────────┘                                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA PERSISTENCE LAYER                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  Microsoft SQL Server (MSSQL)                                      │    │
│  │                                                                    │    │
│  │  Existing Tables:                    New AI Tables:               │    │
│  │  ├─ users                            ├─ documents                 │    │
│  │  ├─ roles                            ├─ document_chunks           │    │
│  │  ├─ projects                         ├─ chat_history              │    │
│  │  ├─ inventory                        └─ ai_actions                │    │
│  │  ├─ lvl1, lvl3                                                    │    │
│  │  ├─ ran_projects                                                  │    │
│  │  └─ rop_projects                                                  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  File System                                                       │    │
│  │                                                                    │    │
│  │  uploads/documents/                                                │    │
│  │  ├─ 20251022_143052_specification.pdf                             │    │
│  │  ├─ 20251022_145022_contract.docx                                 │    │
│  │  └─ ...                                                            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### 1. Chat Conversation Flow

```
User Types Message
        │
        ▼
┌────────────────┐
│  ChatInterface │
│  Component     │
└───────┬────────┘
        │ POST /ai/chat
        │ { message, conversation_id, project_context }
        ▼
┌────────────────┐
│  ChatRoute.py  │
│  Authenticate  │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  BOQAgent      │
│  ├─ Load       │
│  │  history    │
│  ├─ Analyze    │
│  │  intent     │
│  └─ Decide     │
└────┬──────┬────┘
     │      │
Function    Direct
Call        Response
     │      │
     ▼      ▼
┌─────┐  ┌──────────┐
│Tools│  │ Ollama   │
│     │  │ LLM      │
└──┬──┘  └────┬─────┘
   │          │
   │ Execute  │ Generate
   │ Action   │ Text
   │          │
   └────┬─────┘
        │
        ▼
┌────────────────┐
│  Save to       │
│  chat_history  │
│  ai_actions    │
└───────┬────────┘
        │
        ▼
   Return Response
        │
        ▼
┌────────────────┐
│  Display in    │
│  Chat UI       │
└────────────────┘
```

### 2. Document Processing Flow

```
User Uploads PDF
        │
        ▼
┌────────────────┐
│ DocumentUpload │
│ Component      │
└───────┬────────┘
        │ POST /ai/documents/upload
        │ FormData: file, project_id, extract_tags
        ▼
┌────────────────┐
│ DocumentRoute  │
│ ├─ Save file   │
│ ├─ Create DB   │
│ │  record      │
│ └─ Queue task  │
└───────┬────────┘
        │
        ▼
┌────────────────────────┐
│ Background Processing  │
│ (async)                │
└───────┬────────────────┘
        │
        ▼
┌────────────────┐
│  RAGEngine     │
│  ├─ Extract    │──► pypdf/pdfplumber
│  │  text       │
│  ├─ Chunk      │──► Split text (500/100)
│  │  text       │
│  ├─ Generate   │──► sentence-transformers
│  │  embeddings │    (all-MiniLM-L6-v2)
│  ├─ Store      │──► Qdrant vector store
│  │  vectors    │
│  ├─ Save       │──► document_chunks table
│  │  chunks     │
│  └─ Extract    │──► Ollama analysis
│     metadata   │
└────────────────┘
        │
        ▼
┌────────────────┐
│ Update         │
│ processing_    │
│ status:        │
│ "completed"    │
└────────────────┘
```

### 3. RAG Q&A Flow

```
User Asks Question
        │
        ▼
┌────────────────┐
│ ChatInterface  │
│ or             │
│ DocumentAsk    │
└───────┬────────┘
        │ POST /ai/documents/ask
        │ { question, project_id }
        ▼
┌────────────────┐
│ RAGEngine      │
│ answer_        │
│ question()     │
└───────┬────────┘
        │
        ▼
┌─────────────────────────────┐
│ 1. Embed question           │
│    (sentence-transformers)  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. Search Qdrant            │
│    similarity_search(       │
│      query_vector,          │
│      limit=5,               │
│      threshold=0.7          │
│    )                        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 3. Retrieve matching chunks │
│    [                        │
│      {text, score, doc_id}, │
│      ...                    │
│    ]                        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 4. Build context prompt     │
│    "Context: [chunks]       │
│     Question: [question]    │
│     Answer with sources"    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 5. Send to Ollama LLM       │
│    llama3.1:8b              │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 6. Parse response           │
│    Extract citations        │
│    Calculate confidence     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 7. Return answer + sources  │
│    {                        │
│      answer: "...",         │
│      sources: [...],        │
│      confidence: 0.85       │
│    }                        │
└────────┬────────────────────┘
         │
         ▼
    Display to User
```

## Component Dependencies

```
Frontend:
  React App
  └── ChatButton
      └── ChatInterface
          ├── Uses: api.js (axios)
          └── Calls: /ai/chat, /ai/conversations

  Document Management
  └── DocumentUpload
      ├── Uses: api.js (axios)
      └── Calls: /ai/documents/upload

Backend:
  main.py
  ├── Includes: chat_router
  ├── Includes: document_router
  └── Middleware: JWT Auth, CORS

  APIs/AI/ChatRoute.py
  └── Uses: BOQAgent, ChatHistory model

  APIs/AI/DocumentRoute.py
  └── Uses: RAGEngine, Document model

  AI/agent.py (BOQAgent)
  ├── Uses: OllamaClient
  ├── Uses: BOQTools
  ├── Uses: RAGEngine
  └── Saves: ChatHistory, AIAction

  AI/rag_engine.py (RAGEngine)
  ├── Uses: VectorStore
  ├── Uses: OllamaClient
  └── Processes: PDFs, DOCX, TXT

  AI/vectorstore.py (VectorStore)
  ├── Uses: QdrantClient
  ├── Uses: SentenceTransformer
  └── Manages: Embeddings, Search

  AI/ollama_client.py (OllamaClient)
  └── Connects: Ollama Docker container

  AI/tools.py (BOQTools)
  └── Executes: Database operations

Infrastructure:
  Docker Compose
  ├── ollama (LLM)
  ├── qdrant (Vector DB)
  ├── redis (Cache/Queue)
  └── n8n (Workflows)

Database:
  MSSQL
  ├── Existing tables (projects, inventory, etc.)
  └── New AI tables (documents, chat_history, etc.)
```

---

This architecture provides:
- **Separation of concerns** (UI, API, AI, Infrastructure)
- **Scalability** (Docker, async processing)
- **Security** (JWT auth, permissions)
- **Performance** (Vector search, caching)
- **Maintainability** (Modular design, clear interfaces)
