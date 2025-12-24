"""
NDPD Data API Routes

This module provides CRUD operations for managing NDPD (Network Deployment Planning Data).
It includes pagination, search, and full CRUD functionality.
"""

from typing import List, Optional
import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_

from APIs.Core import get_db, get_current_user
from Models.Admin.User import User
from Models.NDPD.NDPDData import NDPDData
from Schemas.NDPD.NDPDDataSchema import (
    CreateNDPDData,
    UpdateNDPDData,
    NDPDDataOut,
    NDPDDataPagination
)

NDPDRoute = APIRouter(prefix="/ndpd", tags=["NDPD Data"])


# ===========================
# CREATE
# ===========================

@NDPDRoute.post("/", response_model=NDPDDataOut, status_code=status.HTTP_201_CREATED)
def create_ndpd_record(
    data: CreateNDPDData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new NDPD data record.
    """
    try:
        new_record = NDPDData(
            period=data.period,
            ct=data.ct,
            actual_sites=data.actual_sites,
            forecast_sites=data.forecast_sites
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating NDPD record: {str(e)}"
        )


# ===========================
# CSV UPLOAD (Must be before /{record_id} routes)
# ===========================

@NDPDRoute.post("/upload-csv", status_code=status.HTTP_200_OK)
async def upload_ndpd_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a CSV file to bulk-add NDPD data records.
    CSV format: Period,CT,Actual Sites,Forecast Sites
    """
    # Check file extension
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )

    try:
        # Read file content
        content = await file.read()

        # Try multiple encodings to handle different CSV formats
        csv_content = None
        encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1', 'iso-8859-1']

        for encoding in encodings:
            try:
                csv_content = StringIO(content.decode(encoding))
                break
            except UnicodeDecodeError:
                continue

        if csv_content is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file. Please ensure it's saved in UTF-8 or Windows-1252 encoding."
            )

        # Parse CSV
        csv_reader = csv.DictReader(csv_content)

        inserted_count = 0
        updated_count = 0
        errors = []

        # Get the actual column names from the CSV
        fieldnames = csv_reader.fieldnames
        if not fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file appears to be empty or has no headers"
            )

        # Create a flexible column mapping (case-insensitive, handles spaces)
        column_map = {}
        for field in fieldnames:
            field_clean = field.strip().lower()
            if 'period' in field_clean:
                column_map['period'] = field
            elif field_clean == 'ct':
                column_map['ct'] = field
            elif 'actual' in field_clean and 'site' in field_clean:
                column_map['actual_sites'] = field
            elif 'forecast' in field_clean and 'site' in field_clean:
                column_map['forecast_sites'] = field

        # Validate that we found all required columns
        missing_columns = []
        if 'period' not in column_map:
            missing_columns.append('Period')
        if 'ct' not in column_map:
            missing_columns.append('CT')
        if 'actual_sites' not in column_map:
            missing_columns.append('Actual Sites')
        if 'forecast_sites' not in column_map:
            missing_columns.append('Forecast Sites')

        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV is missing required columns: {', '.join(missing_columns)}. Found columns: {', '.join(fieldnames)}"
            )

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is header
            try:
                # Extract data from CSV using the mapped column names
                period = row.get(column_map['period'], '').strip()
                ct = row.get(column_map['ct'], '').strip()
                actual_sites_str = row.get(column_map['actual_sites'], '').strip()
                forecast_sites_str = row.get(column_map['forecast_sites'], '').strip()

                # Skip empty rows
                if not period and not ct:
                    continue

                # Validate required fields
                if not period:
                    errors.append(f"Row {row_num}: Period is required")
                    continue
                if not ct:
                    errors.append(f"Row {row_num}: CT is required")
                    continue

                # Parse numbers
                try:
                    actual_sites = int(actual_sites_str) if actual_sites_str else 0
                    forecast_sites = int(forecast_sites_str) if forecast_sites_str else 0
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid number format for sites")
                    continue

                # Check if record exists (by period and CT)
                existing_record = db.query(NDPDData).filter(
                    NDPDData.period == period,
                    NDPDData.ct == ct
                ).first()

                if existing_record:
                    # Update existing record
                    existing_record.actual_sites = actual_sites
                    existing_record.forecast_sites = forecast_sites
                    updated_count += 1
                else:
                    # Create new record
                    new_record = NDPDData(
                        period=period,
                        ct=ct,
                        actual_sites=actual_sites,
                        forecast_sites=forecast_sites
                    )
                    db.add(new_record)
                    inserted_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue

        # Commit all changes
        db.commit()

        return {
            "message": "CSV upload completed",
            "inserted_count": inserted_count,
            "updated_count": updated_count,
            "total_processed": inserted_count + updated_count,
            "errors": errors if errors else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV file: {str(e)}"
        )


# ===========================
# DELETE ALL (Must be before /{record_id} routes)
# ===========================

@NDPDRoute.delete("/delete-all", status_code=status.HTTP_200_OK)
def delete_all_ndpd_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all NDPD data records.
    Only senior_admin can perform this operation.
    """
    # Check if user is senior_admin
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only senior admin can delete all NDPD records"
        )

    try:
        # Count records before deletion
        record_count = db.query(NDPDData).count()

        if record_count == 0:
            raise HTTPException(status_code=404, detail="No NDPD records found")

        # Delete all records
        deleted_count = db.query(NDPDData).delete(synchronize_session=False)
        db.commit()

        return {
            "message": f"Successfully deleted all {deleted_count} NDPD records",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting all NDPD records: {str(e)}"
        )


# ===========================
# BULK DELETE (Must be before /{record_id} routes)
# ===========================

@NDPDRoute.delete("/bulk/delete", status_code=status.HTTP_200_OK)
def bulk_delete_ndpd_records(
    record_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete multiple NDPD data records at once.
    """
    try:
        deleted_count = db.query(NDPDData).filter(NDPDData.id.in_(record_ids)).delete(synchronize_session=False)
        db.commit()

        return {
            "message": f"Successfully deleted {deleted_count} NDPD records",
            "deleted_count": deleted_count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting NDPD records: {str(e)}"
        )


# ===========================
# READ (GET ALL with Pagination & Search)
# ===========================

@NDPDRoute.get("/", response_model=NDPDDataPagination)
def get_all_ndpd_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: Optional[str] = Query(None, description="Search by period or CT name")
):
    """
    Get all NDPD data records with pagination and search.
    """
    try:
        query = db.query(NDPDData)

        # Apply search filter if provided
        if search:
            search_filter = or_(
                NDPDData.period.ilike(f"%{search}%"),
                NDPDData.ct.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Get total count
        total = query.count()

        # Get paginated results
        records = query.order_by(NDPDData.id.desc()).offset(skip).limit(limit).all()

        return NDPDDataPagination(records=records, total=total)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching NDPD records: {str(e)}"
        )


# ===========================
# READ (GET by ID)
# ===========================

@NDPDRoute.get("/{record_id}", response_model=NDPDDataOut)
def get_ndpd_record_by_id(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific NDPD data record by ID.
    """
    record = db.query(NDPDData).filter(NDPDData.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NDPD record with ID {record_id} not found"
        )

    return record


# ===========================
# UPDATE
# ===========================

@NDPDRoute.put("/{record_id}", response_model=NDPDDataOut)
def update_ndpd_record(
    record_id: int,
    data: UpdateNDPDData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing NDPD data record.
    """
    record = db.query(NDPDData).filter(NDPDData.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NDPD record with ID {record_id} not found"
        )

    try:
        # Update only provided fields
        if data.period is not None:
            record.period = data.period
        if data.ct is not None:
            record.ct = data.ct
        if data.actual_sites is not None:
            record.actual_sites = data.actual_sites
        if data.forecast_sites is not None:
            record.forecast_sites = data.forecast_sites

        db.commit()
        db.refresh(record)
        return record
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating NDPD record: {str(e)}"
        )


# ===========================
# DELETE
# ===========================

@NDPDRoute.delete("/{record_id}", status_code=status.HTTP_200_OK)
def delete_ndpd_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an NDPD data record.
    """
    record = db.query(NDPDData).filter(NDPDData.id == record_id).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NDPD record with ID {record_id} not found"
        )

    try:
        db.delete(record)
        db.commit()
        return {
            "message": f"NDPD record {record_id} deleted successfully",
            "deleted_id": record_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting NDPD record: {str(e)}"
        )
