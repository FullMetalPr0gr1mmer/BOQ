"""
File Upload Validation Utilities

Provides security checks for file uploads including size limits and MIME type validation.
"""

from fastapi import HTTPException, UploadFile
from typing import List, Optional

# Default limits (can be overridden per endpoint)
MAX_CSV_FILE_SIZE = 50 * 1024 * 1024  # 50 MB for CSV files
MAX_EXCEL_FILE_SIZE = 100 * 1024 * 1024  # 100 MB for Excel files
MAX_DOCUMENT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB for Word/PDF documents
MAX_IMAGE_FILE_SIZE = 5 * 1024 * 1024  # 5 MB for images

# Allowed MIME types for different file categories
ALLOWED_CSV_TYPES = [
    'text/csv',
    'application/csv',
    'application/vnd.ms-excel',  # Some systems send CSV as this
]

ALLOWED_EXCEL_TYPES = [
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]

ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]


async def validate_csv_file(
    file: UploadFile,
    max_size: int = MAX_CSV_FILE_SIZE,
    strict_mime: bool = False
) -> None:
    """
    Validate CSV file upload.

    Args:
        file: The uploaded file
        max_size: Maximum file size in bytes
        strict_mime: If True, strictly validates MIME type (may reject valid CSVs)

    Raises:
        HTTPException: If validation fails
    """
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only CSV files are allowed."
        )

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb:.0f} MB."
        )

    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )

    # IMPORTANT: Reset file pointer after reading
    await file.seek(0)


async def validate_excel_file(
    file: UploadFile,
    max_size: int = MAX_EXCEL_FILE_SIZE
) -> None:
    """
    Validate Excel file upload.

    Args:
        file: The uploaded file
        max_size: Maximum file size in bytes

    Raises:
        HTTPException: If validation fails
    """
    # Validate file extension
    if not (file.filename.lower().endswith('.xlsx') or file.filename.lower().endswith('.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only Excel files (.xlsx, .xls) are allowed."
        )

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb:.0f} MB."
        )

    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )

    # IMPORTANT: Reset file pointer after reading
    await file.seek(0)


async def validate_document_file(
    file: UploadFile,
    allowed_extensions: List[str],
    max_size: int = MAX_DOCUMENT_FILE_SIZE
) -> None:
    """
    Validate document file upload (PDF, Word, etc.).

    Args:
        file: The uploaded file
        allowed_extensions: List of allowed file extensions (e.g., ['.pdf', '.docx'])
        max_size: Maximum file size in bytes

    Raises:
        HTTPException: If validation fails
    """
    # Validate file extension
    file_ext = '.' + file.filename.lower().split('.')[-1] if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb:.0f} MB."
        )

    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )

    # IMPORTANT: Reset file pointer after reading
    await file.seek(0)


async def validate_file_size_only(
    file: UploadFile,
    max_size: int = MAX_CSV_FILE_SIZE
) -> None:
    """
    Simple file size validation without MIME type checking.
    Useful for legacy endpoints that need size limits but flexible file types.

    Args:
        file: The uploaded file
        max_size: Maximum file size in bytes

    Raises:
        HTTPException: If validation fails
    """
    content = await file.read()
    file_size = len(content)

    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_mb:.0f} MB."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty."
        )

    await file.seek(0)
