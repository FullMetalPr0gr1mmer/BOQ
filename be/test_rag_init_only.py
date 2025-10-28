"""
Test: Just initialize RAG engine
"""
import time
import sys

print("=" * 60, flush=True)
print("RAG INIT TEST", flush=True)
print("=" * 60, flush=True)

print("\n1. Importing RAG engine...", end=" ", flush=True)
start = time.time()
from AI.rag_engine import RAGEngine
print(f"[{time.time()-start:.2f}s]", flush=True)

print("2. Creating RAG instance...", end=" ", flush=True)
start = time.time()
rag = RAGEngine()
print(f"[{time.time()-start:.2f}s]", flush=True)

print("\n" + "=" * 60, flush=True)
print("[SUCCESS] RAG initialized", flush=True)
print("=" * 60, flush=True)
