# Text-to-SQL Quick Reference Card

## 🚀 Daily Usage Commands

### Generate SQL (Simple)
```python
from AI.text2sql_generator import text_to_sql

sql = text_to_sql("Show me all users with their roles")
print(sql)
```

### Generate SQL (Advanced)
```python
from AI.text2sql_generator import Text2SQLGenerator

generator = Text2SQLGenerator()
result = generator.generate_sql(
    question="How many active users per project?",
    database="SQL Server",
    validate=True
)

print(f"SQL: {result.sql}")
print(f"Confidence: {result.confidence}")
print(f"Ready: {result.execution_ready}")
```

### Add Feedback (User Clicks 👍)
```python
from AI.feedback_loop import add_feedback

add_feedback(
    question="Show active projects",
    correct_sql="SELECT * FROM projects WHERE ..."
)
```

---

## 🔧 Maintenance Commands

### Re-parse Models (After Code Changes)
```bash
cd /c/WORK/BOQ/be
python AI/parsers/parse_all.py
```

### Re-embed Knowledge Base
```bash
python AI/embed_schema_knowledge.py --clear
```

### Test System
```bash
python AI/test_text2sql.py
```

---

## 📊 Monitoring

### Check Collection Stats
```python
from AI.text2sql_vectorstore import get_text2sql_vector_store

vs = get_text2sql_vector_store()
print(vs.get_collection_stats())
```

### Check Feedback Stats
```python
from AI.feedback_loop import get_feedback_loop

feedback = get_feedback_loop()
print(feedback.get_stats())
```

---

## 🏥 Health Checks

```bash
# Qdrant
curl http://localhost:6333/health

# Ollama
curl http://localhost:11434/api/tags

# Collection
python -c "from AI.text2sql_vectorstore import get_text2sql_vector_store; print(get_text2sql_vector_store().get_collection_stats())"
```

---

## 🎯 Key Files

| File | Purpose |
|------|---------|
| `text2sql_generator.py` | Main SQL generation |
| `text2sql_vectorstore.py` | Vector retrieval |
| `feedback_loop.py` | Continuous improvement |
| `embed_schema_knowledge.py` | Embedding script |
| `knowledge_base/business_logic_glossary.txt` | Edit business rules here |
| `knowledge_base/few_shot_examples.json` | Auto-generated examples |

---

## 🔥 Hot Tips

1. **Low confidence?** → Add few-shot examples via feedback
2. **Wrong table?** → Check business_logic_glossary.txt
3. **Wrong JOIN?** → Verify SQLAlchemy relationships exist
4. **Slow?** → Reduce `max_context_chunks` parameter
5. **New tables?** → Re-run parse_all.py + embed_schema_knowledge.py

---

## 📞 Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| "Connection refused" | Start Qdrant: `docker-compose up -d qdrant` |
| "Model not found" | Pull model: `ollama pull llama3.1:8b` |
| "No results" | Check vectors: `vs.get_collection_stats()` |
| "Hallucinations" | Add business rules, re-embed |

---

**Need Help?** Check `COMPLETE_SYSTEM_SUMMARY.md` for full documentation.
