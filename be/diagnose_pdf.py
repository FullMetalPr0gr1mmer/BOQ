"""
Test 2: PDF Extraction Test
Verify PDF text extraction works
"""
import sys
import time
import pdfplumber

def main():
    print("=" * 60)
    print("TEST 2: PDF EXTRACTION TEST")
    print("=" * 60)

    pdf_path = "uploads/documents/20251026_081008_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print(f"\nTesting PDF: {pdf_path}")
    print("=" * 60)

    # Test file exists
    print("Checking file exists...", end=" ")
    import os
    if not os.path.exists(pdf_path):
        print(f"[FAIL]")
        print(f"  File not found: {pdf_path}")
        return False
    print(f"[PASS]")

    # Test PDF extraction
    print("Extracting text from PDF...", end=" ")
    start = time.time()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            print(f"[PASS] ({time.time() - start:.2f}s)")
            print(f"  Pages: {num_pages}")

            # Extract text from first page
            print("Extracting first page...", end=" ")
            start = time.time()
            first_page_text = pdf.pages[0].extract_text()
            print(f"[PASS] ({time.time() - start:.2f}s)")
            print(f"  First page length: {len(first_page_text)} chars")
            print(f"  Preview: {first_page_text[:200]}...")

            # Extract all text
            print("Extracting all pages...", end=" ")
            start = time.time()
            all_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)

            total_text = "\n".join(all_text)
            print(f"[PASS] ({time.time() - start:.2f}s)")
            print(f"  Total text length: {len(total_text)} chars")
            print(f"  Total pages with text: {len(all_text)}")

            if len(total_text) > 0:
                print("\n" + "=" * 60)
                print("[SUCCESS] PDF EXTRACTION WORKING")
                print("=" * 60)
                return True
            else:
                print("\n" + "=" * 60)
                print("[FAILED] NO TEXT EXTRACTED")
                print("=" * 60)
                return False

    except Exception as e:
        print(f"[FAIL] ({time.time() - start:.2f}s)")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
