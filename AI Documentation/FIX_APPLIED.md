# Fix Applied: SQLAlchemy Reserved Keyword Issue

## Issue
`metadata` is a reserved keyword in SQLAlchemy's Declarative API and cannot be used as a column name.

**Error:**
```
sqlalchemy.exc.InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API
```

## Solution Applied ✅

### Files Modified:

1. **`be/Models/AI/Document.py`** (Line 68)
   - Changed: `metadata = Column(JSON, default=dict)`
   - To: `chunk_metadata = Column(JSON, default=dict)`

2. **`be/alembic/versions/a068c6bdfd26_add_ai_tables_for_documents_and_chat.py`** (Line 56)
   - Changed: `sa.Column('metadata', sa.JSON(), nullable=True)`
   - To: `sa.Column('chunk_metadata', sa.JSON(), nullable=True)`

3. **`be/AI/rag_engine.py`** (Line 94)
   - Changed: `metadata=chunk.get('metadata', {})`
   - To: `chunk_metadata=chunk.get('metadata', {})`

## Impact

- ✅ Database migration will now work correctly
- ✅ Document chunk metadata will be stored properly
- ✅ No functional changes - just renamed the column

## Next Steps

If you already ran the migration and got the error:

```bash
cd C:\WORK\BOQ\be

# Downgrade (remove the failed migration)
alembic downgrade -1

# Now upgrade with the fix
alembic upgrade head
```

If you haven't run migration yet, just proceed normally:

```bash
cd C:\WORK\BOQ\be
alembic upgrade head
```

## Verification

After migration, verify the column exists:

```sql
-- Check column name in document_chunks table
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'document_chunks';
```

You should see `chunk_metadata` (not `metadata`) with type `nvarchar`.

---

**Status:** ✅ Fixed and ready to deploy
**Date:** 2025-10-22
