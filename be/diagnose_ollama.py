"""
Test 5: Ollama API Test
Verify Ollama connection and text generation
"""
import sys
import time
import ollama

def main():
    print("=" * 60)
    print("TEST 5: OLLAMA API TEST")
    print("=" * 60)

    host = "http://localhost:11434"
    model = "llama3.2:1b"

    # Test connection
    print(f"\nConnecting to Ollama at {host}...", end=" ")
    start = time.time()
    try:
        client = ollama.Client(host=host)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test list models
    print("Listing available models...", end=" ")
    start = time.time()
    try:
        models_response = client.list()
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")

        # Handle different response types
        if hasattr(models_response, 'models'):
            model_list = models_response.models
        elif isinstance(models_response, dict):
            model_list = models_response.get('models', [])
        else:
            model_list = list(models_response) if hasattr(models_response, '__iter__') else []

        print(f"  Available models: {len(model_list)}")
        for m in model_list:
            if hasattr(m, 'model'):
                model_name = m.model
            elif hasattr(m, 'name'):
                model_name = m.name
            elif isinstance(m, dict):
                model_name = m.get('model', m.get('name', str(m)))
            else:
                model_name = str(m)
            print(f"    - {model_name}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test generate (short prompt)
    print(f"Testing generation with {model} (short)...", end=" ")
    start = time.time()
    try:
        response = client.generate(
            model=model,
            prompt="Say 'Hello' in one word.",
            options={"num_predict": 5}
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Response: {response['response'][:100]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test generate with longer prompt (simulating tag extraction)
    print(f"Testing generation (metadata extraction)...", end=" ")
    prompt = """Analyze this document excerpt and extract 3 relevant tags:

Document: "The LEGO Approach to Prompt Engineering. Building Better AI Conversations Brick by Brick."

Return only 3 tags as a comma-separated list."""

    start = time.time()
    try:
        response = client.generate(
            model=model,
            prompt=prompt,
            options={"num_predict": 20}
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Response: {response['response'][:150]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] OLLAMA API WORKING")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
