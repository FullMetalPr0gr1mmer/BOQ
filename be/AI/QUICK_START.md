# Text-to-SQL RAG System - Quick Start Guide

## Prerequisites Checklist

- ✅ Task 1 Complete - Knowledge base parsed (162 chunks created)
- ⏳ Qdrant running on `localhost:6333`
- ✅ Ollama running with `nomic-embed-text` model

---

## Step 1: Start Qdrant

```bash
# Navigate to project root
cd /c/WORK/BOQ

# Start Qdrant via Docker Compose
docker-compose up -d qdrant

# Verify it's running
curl http://localhost:6333/health

# Should return: {"title":"qdrant - vector search engine",...}
```

**If Docker has issues:**
```bash
# Check Docker Desktop is running
docker ps

# If not working, start Docker Desktop manually, then retry
```

---

## Step 2: Embed Schema Knowledge

```bash
# Navigate to backend
cd /c/WORK/BOQ/be

# Run embedding script (first time - clears existing)
python AI/embed_schema_knowledge.py --clear

# Output should show:
# - Loading 162 chunks
# - Validation passed
# - Embedding batches (1-17)
# - Successfully embedded 162 chunks
# - Test searches with results
```

**Expected Time:** ~20-30 seconds

---

## Step 3: Verify Embeddings

### Test in Python:

```python
from AI.text2sql_vectorstore import get_text2sql_vector_store

# Get vector store
vs = get_text2sql_vector_store()

# Check stats
stats = vs.get_collection_stats()
print(f"Total vectors: {stats['total_vectors']}")
# Should be: 162

# Test search
results = vs.search("How do I join users and audit logs?", limit=3)
for r in results:
    print(f"\nType: {r['type']}")
    print(f"Score: {r['similarity_score']:.3f}")
    print(r['content'][:150] + "...")
```

### Expected Result:
```
Total vectors: 162

Type: relationship
Score: 0.856
Content: TABLE: audit_logs
MODEL: AuditLog
RELATIONSHIP: user
JOIN CONDITION: AuditLog.user_id == User.id...
```

---

## Common Commands

### Re-parse Models (after code changes)
```bash
cd /c/WORK/BOQ/be
python AI/parsers/parse_all.py
```

### Re-embed Knowledge Base
```bash
cd /c/WORK/BOQ/be
python AI/embed_schema_knowledge.py --clear
```

### Check Qdrant Status
```bash
# Health check
curl http://localhost:6333/health

# Collection info
curl http://localhost:6333/collections/text2sql_schema
```

### View Collection in Browser
Open: `http://localhost:6333/dashboard`

---

## Test Queries to Try

Once embeddings are loaded, test these queries:

### 1. Find Relationships (JOIN prevention)
```python
vs = get_text2sql_vector_store()

# Get all relationships for specific tables
results = vs.get_relationships_for_tables(["users", "audit_logs"])
for r in results:
    print(r['content'])
```

### 2. Find Business Rules
```python
results = vs.get_business_rules("What is an active project?")
for r in results:
    print(r['content'])
```

### 3. Get Table Schema
```python
results = vs.search_by_tables(
    query="What columns are in the projects table?",
    table_names=["projects"]
)
for r in results:
    print(r['content'])
```

### 4. General Search (auto-prioritizes)
```python
results = vs.search("How many users bought pro plans?", limit=5)
for r in results:
    print(f"[{r['type']}] {r['similarity_score']:.3f}")
```

---

## Troubleshooting

### Issue: "Connection refused to Qdrant"

**Solution:**
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# If not running:
docker-compose up -d qdrant

# Check logs:
docker logs boq-qdrant
```

---

### Issue: "nomic-embed-text model not found"

**Solution:**
```bash
# Pull the model via Ollama
ollama pull nomic-embed-text

# Verify it's available
ollama list | grep nomic
```

---

### Issue: "Embedding takes too long"

**Normal:** ~20-30 seconds for 162 chunks

**If slower:**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Restart Ollama: `docker-compose restart ollama`

---

### Issue: "Search returns no results"

**Solution:**
```python
# Check collection stats
vs = get_text2sql_vector_store()
stats = vs.get_collection_stats()
print(stats)

# If total_vectors is 0, re-embed:
# python AI/embed_schema_knowledge.py --clear
```

---

## What's Next?

Once embeddings are working (Step 3 passes), you're ready for:

### **Task 3: Query Pipeline**

This will include:
1. Two-stage retrieval (identify tables → fetch detailed schema)
2. Context assembly (organize chunks by type)
3. Prompt template for Llama 3.1
4. SQL generation function
5. Validation and error handling

Let me know when you're ready to proceed to Task 3!

---

## File Locations

```
/c/WORK/BOQ/
├── docker-compose.yml              ← Start Qdrant
│
└── be/
    ├── AI/
    │   ├── parsers/
    │   │   └── parse_all.py        ← Re-parse models
    │   │
    │   ├── knowledge_base/
    │   │   └── all_chunks_combined.json  ← Input chunks
    │   │
    │   ├── text2sql_vectorstore.py ← Vector store
    │   └── embed_schema_knowledge.py ← Embedding script
    │
    └── requirements.txt             ← Dependencies
```

---

## Quick Health Check

Run this one-liner to check everything:

```bash
curl http://localhost:6333/health && \
curl http://localhost:11434/api/tags && \
echo "All services running!"
```

If both return successfully, you're ready to embed!

---

**Status: Task 1 ✓ | Task 2 ✓ (pending Qdrant start) | Task 3 ⏳**

Start Qdrant and run the embedding script, then we'll move to Task 3!
