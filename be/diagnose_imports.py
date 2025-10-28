"""
Test 1: Import Test
Verify all required modules can be imported
"""
import sys
import time

def test_import(module_name, import_statement):
    """Test a single import"""
    print(f"Testing: {module_name}...", end=" ")
    start = time.time()
    try:
        exec(import_statement)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

def main():
    print("=" * 60)
    print("TEST 1: IMPORT TEST")
    print("=" * 60)

    tests = [
        ("Python Standard Libraries", "import os, sys, json, re, logging"),
        ("SQLAlchemy", "from sqlalchemy import create_engine; from sqlalchemy.orm import sessionmaker"),
        ("PDF Processing", "import pdfplumber; from pypdf import PdfReader"),
        ("Document Processing", "from docx import Document"),
        ("Qdrant Client", "from qdrant_client import QdrantClient"),
        ("SentenceTransformers", "from sentence_transformers import SentenceTransformer"),
        ("Ollama Client", "import ollama"),
        ("Environment", "from dotenv import load_dotenv"),
        ("Custom: Database Session", "from Database.session import Base"),
        ("Custom: AI Models", "from Models.AI import Document, DocumentChunk"),
        ("Custom: Vector Store", "from AI.vectorstore import get_vector_store"),
        ("Custom: Ollama Client", "from AI.ollama_client import get_ollama_client"),
        ("Custom: RAG Engine", "from AI.rag_engine import get_rag_engine"),
    ]

    results = []
    for name, import_stmt in tests:
        results.append(test_import(name, import_stmt))

    print("\n" + "=" * 60)
    print(f"RESULTS: {sum(results)}/{len(results)} tests passed")
    if all(results):
        print("[SUCCESS] ALL IMPORTS WORKING")
    else:
        print("[FAILED] SOME IMPORTS FAILED")
    print("=" * 60)

    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
