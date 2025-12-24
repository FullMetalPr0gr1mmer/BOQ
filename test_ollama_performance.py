"""
Test Ollama model performance for RAG use cases
"""
import os
import time
import json

# Bypass proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

import ollama
from datetime import datetime

def test_simple_prompt(model_name):
    """Test 1: Simple prompt - baseline speed"""
    print(f"\n{'='*60}")
    print(f"TEST 1: Simple Prompt (Baseline Speed)")
    print(f"{'='*60}")

    prompt = "Hello! Can you introduce yourself in one sentence?"

    start = time.time()
    response = ollama.generate(
        model=model_name,
        prompt=prompt,
        options={'temperature': 0.7}
    )
    elapsed = time.time() - start

    print(f"Prompt: {prompt}")
    print(f"Response: {response['response']}")
    print(f"[TIME] {elapsed:.2f} seconds")
    print(f"[STATUS] {'PASS' if elapsed < 180 else 'FAIL'} (< 3 mins)")

    return elapsed

def test_rag_qa(model_name):
    """Test 2: Realistic RAG Q&A scenario"""
    print(f"\n{'='*60}")
    print(f"TEST 2: RAG Q&A (Document Analysis)")
    print(f"{'='*60}")

    # Simulate RAG context
    context = """
    [Source 1] The BOQ (Bill of Quantities) project is a telecommunications infrastructure
    management system. It tracks site data, equipment specifications, and project costs
    for mobile network deployments across multiple regions.

    [Source 2] The system includes modules for project management, financial tracking,
    and AI-powered document analysis. It uses FastAPI backend with React frontend.

    [Source 3] Key features include: JWT authentication, database migrations with Alembic,
    and integration with Ollama for AI capabilities including RAG-based document Q&A.
    """

    question = "What is the BOQ project and what are its main features?"

    prompt = f"""You are a precise document analysis assistant. Answer the question using ONLY the information in the context below.

Context from documents:
{context}

Question: {question}

Please answer based on the context above, citing sources."""

    start = time.time()
    response = ollama.generate(
        model=model_name,
        prompt=prompt,
        options={'temperature': 0.1}  # Low temp for factual responses
    )
    elapsed = time.time() - start

    print(f"Question: {question}")
    print(f"Response: {response['response'][:300]}...")
    print(f"[TIME] {elapsed:.2f} seconds")
    print(f"[STATUS] {'PASS' if elapsed < 180 else 'FAIL'} (< 3 mins)")

    return elapsed

def test_json_extraction(model_name):
    """Test 3: JSON metadata extraction (like _extract_metadata)"""
    print(f"\n{'='*60}")
    print(f"TEST 3: JSON Metadata Extraction")
    print(f"{'='*60}")

    document_sample = """
    TECHNICAL SPECIFICATION - 5G ANTENNA INSTALLATION

    Project: Network Expansion Phase 2
    Date: 2024-03-15
    Site: CAIRO-001, CAIRO-002, ALEX-003

    Equipment Required:
    - 5G Massive MIMO Antenna (Model: HUAWEI AAU5613)
    - Remote Radio Unit (RRU Model: ERICSSON 4449)
    - Fiber Optic Cables (Single Mode, 50m)

    This document outlines the technical requirements for installing 5G network
    equipment at three strategic locations in Egypt as part of our Q1 2024 deployment plan.
    """

    prompt = f"""Analyze this document excerpt and provide:
1. 5-10 relevant tags (e.g., "invoice", "technical_spec", "antenna", "5G")
2. A one-sentence summary
3. Document type (e.g., "technical specification", "invoice", "contract", "drawing")
4. Key entities mentioned (sites, equipment, dates)

Document excerpt:
{document_sample}

Respond in JSON format:
{{
    "tags": ["tag1", "tag2", ...],
    "summary": "One sentence summary",
    "document_type": "type",
    "entities": {{
        "sites": ["site1", "site2"],
        "equipment": ["equipment1"],
        "dates": ["2024-01-15"]
    }}
}}"""

    start = time.time()
    response = ollama.generate(
        model=model_name,
        prompt=prompt,
        format='json',  # JSON mode
        options={'temperature': 0.1}
    )
    elapsed = time.time() - start

    print(f"Document Type: Technical Specification")
    try:
        result = json.loads(response['response'])
        print(f"Extracted Tags: {result.get('tags', [])}")
        print(f"Summary: {result.get('summary', 'N/A')}")
        print(f"Document Type: {result.get('document_type', 'N/A')}")
        print(f"[JSON] Valid: YES")
    except json.JSONDecodeError as e:
        print(f"[JSON] Valid: NO - {e}")
        print(f"Raw response: {response['response'][:200]}")

    print(f"[TIME] {elapsed:.2f} seconds")
    print(f"[STATUS] {'PASS' if elapsed < 180 else 'FAIL'} (< 3 mins)")

    return elapsed

def main():
    model_name = "qwen2.5:7b"

    print(f"\n{'#'*60}")
    print(f"# OLLAMA MODEL PERFORMANCE TEST")
    print(f"# Model: {model_name}")
    print(f"# Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")

    try:
        # Run all tests
        time1 = test_simple_prompt(model_name)
        time2 = test_rag_qa(model_name)
        time3 = test_json_extraction(model_name)

        # Summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Test 1 (Simple):      {time1:6.2f}s")
        print(f"Test 2 (RAG Q&A):     {time2:6.2f}s")
        print(f"Test 3 (JSON Extract): {time3:6.2f}s")
        print(f"{'='*60}")
        print(f"Average:              {(time1+time2+time3)/3:6.2f}s")
        print(f"Max Time:             {max(time1,time2,time3):6.2f}s")
        print(f"{'='*60}")

        if max(time1, time2, time3) < 180:
            print(f"[PASS] ALL TESTS PASSED - Model meets 3-minute requirement!")
        else:
            print(f"[FAIL] SOME TESTS FAILED - Model exceeds 3-minute limit")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
