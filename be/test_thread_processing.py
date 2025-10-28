"""
Test: Can Threading Work for Document Processing?
Test if threading actually executes or if something blocks it
"""
import sys
import time
import threading
import logging

# Set up logging to see thread output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def heavy_import_in_thread():
    """Simulate the RAG engine import in a thread"""
    logger.info("[THREAD] Thread started")

    try:
        logger.info("[THREAD] Starting heavy import (RAG engine)...")
        start = time.time()

        # This is what the background task does
        from AI.rag_engine import get_rag_engine

        elapsed = time.time() - start
        logger.info(f"[THREAD] Import completed in {elapsed:.2f}s")

        logger.info("[THREAD] Initializing RAG engine...")
        start = time.time()
        rag_engine = get_rag_engine()
        elapsed = time.time() - start
        logger.info(f"[THREAD] RAG engine initialized in {elapsed:.2f}s")

        logger.info("[THREAD] Thread completed successfully!")
        return True

    except Exception as e:
        logger.error(f"[THREAD] Error: {e}")
        import traceback
        logger.error(f"[THREAD] Traceback: {traceback.format_exc()}")
        return False

def main():
    print("=" * 60)
    print("TEST: THREADING WITH RAG ENGINE")
    print("=" * 60)

    print("\nStarting thread...")
    start_time = time.time()

    # Start thread (same as DocumentRoute.py fix)
    thread = threading.Thread(
        target=heavy_import_in_thread,
        daemon=True,
        name="test-rag-thread"
    )
    thread.start()
    print(f"Thread started at t=0s")

    # Wait and monitor
    max_wait = 60  # 60 seconds max
    check_interval = 2  # Check every 2 seconds

    elapsed = 0
    while thread.is_alive() and elapsed < max_wait:
        time.sleep(check_interval)
        elapsed = time.time() - start_time
        print(f"t={elapsed:.1f}s - Thread still running...")

    if thread.is_alive():
        print(f"\n[TIMEOUT] Thread still running after {max_wait}s")
        print("Thread may be hung or just taking too long")
        return False
    else:
        elapsed = time.time() - start_time
        print(f"\n[SUCCESS] Thread completed in {elapsed:.2f}s")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
