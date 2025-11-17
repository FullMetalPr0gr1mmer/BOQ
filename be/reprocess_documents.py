"""
Re-process existing documents to generate embeddings with new vector dimensions

This script re-embeds all documents in the database using the nomic-embed-text model (768-dim)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from Database.session import Session
from sqlalchemy import text
from AI.rag_engine import get_rag_engine
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reprocess_all_documents():
    """Re-process all documents in the database"""

    db = Session()
    rag_engine = get_rag_engine()

    try:
        # Get all documents
        result = db.execute(text("SELECT id, filename, file_path, processing_status FROM documents ORDER BY id"))
        documents = result.fetchall()

        if not documents:
            logger.info("No documents found in database")
            return

        logger.info(f"Found {len(documents)} documents to re-process")
        print("\n" + "=" * 80)
        print(f"DOCUMENTS TO RE-PROCESS: {len(documents)}")
        print("=" * 80)

        for doc in documents:
            doc_id, filename, file_path, processing_status = doc
            print(f"\n{doc_id}. {filename}")
            print(f"   Path: {file_path}")
            print(f"   Status: {processing_status}")

        print("=" * 80)
        response = input("\nDo you want to re-process all documents? (yes/no): ").strip().lower()

        if response != 'yes':
            logger.info("Operation cancelled by user")
            return

        # Process each document
        success_count = 0
        error_count = 0

        for doc in documents:
            doc_id, filename, file_path, processing_status = doc

            try:
                logger.info(f"Processing document {doc_id}: {filename}")

                if not os.path.exists(file_path):
                    logger.error(f"File not found: {file_path}")
                    error_count += 1
                    continue

                # Process the document
                rag_engine.process_document(
                    file_path=file_path,
                    document_id=doc_id,
                    filename=filename
                )

                logger.info(f"Successfully processed document {doc_id}")
                success_count += 1

            except Exception as e:
                logger.error(f"Error processing document {doc_id}: {e}")
                error_count += 1
                import traceback
                traceback.print_exc()

        print("\n" + "=" * 80)
        print("RE-PROCESSING COMPLETE")
        print("=" * 80)
        print(f"Success: {success_count} documents")
        print(f"Errors: {error_count} documents")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    reprocess_all_documents()
