from typing import Optional
from fastapi import status, Query, HTTPException, Depends, APIRouter, UploadFile, File, Request
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
import csv
import io
import json
import logging

# Core and Schema Imports
from APIs.Core import get_db, get_current_user
from Schemas.BOQ.POReportSchema import POReportOut, POReportCreate, POReportUpdate, POReportUploadResponse

# Model Imports
from Models.BOQ.POReport import POReport
from Models.Admin.User import User
from Models.Admin.AuditLog import AuditLog

logger = logging.getLogger(__name__)
POReportRouter = APIRouter(prefix="/po-report", tags=["PO Report"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_audit_log_sync(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: str = None,
    resource_name: str = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Create an audit log entry (synchronous version)."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


def require_approval_access(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that checks if user has access to any approval stage.
    Only users with approval, triggering, or logistics access can view PO Report data.
    Senior admins always have access.
    """
    # Senior admin always has access
    if current_user.role and current_user.role.name == "senior_admin":
        return current_user

    # Check if user has any approval permission
    has_access = (
        current_user.can_access_approval or
        current_user.can_access_triggering or
        current_user.can_access_logistics
    )

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You need approval, triggering, or logistics access to view PO Report data."
        )

    return current_user


# --- CRUD ENDPOINTS ---

@POReportRouter.get("/reports")
def list_reports(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        search: Optional[str] = Query(None, description="Search across all fields"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    List all PO reports with optional filtering and pagination.
    """
    # Base query
    q = db.query(POReport)

    # Apply search filter
    if search:
        s = f"%{search.strip().lower()}%"
        q = q.filter(or_(
            func.lower(func.coalesce(POReport.pur_doc, "")).like(s),
            func.lower(func.coalesce(POReport.customer_site_ref, "")).like(s),
            func.lower(func.coalesce(POReport.project, "")).like(s),
            func.lower(func.coalesce(POReport.so_number, "")).like(s),
            func.lower(func.coalesce(POReport.material_des, "")).like(s),
            func.lower(func.coalesce(POReport.site_name, "")).like(s),
            func.lower(func.coalesce(POReport.supplier, "")).like(s),
            func.lower(func.coalesce(POReport.name_1, "")).like(s),
            func.lower(func.coalesce(POReport.header_text, "")).like(s),
            func.lower(func.coalesce(POReport.remarks, "")).like(s),
        ))

    total = q.count()
    rows = q.order_by(POReport.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [POReportOut.model_validate(r).model_dump(by_alias=True) for r in rows]
    }


@POReportRouter.post("/report", response_model=POReportOut, status_code=status.HTTP_201_CREATED)
def create_report(
        payload: POReportCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Create a new PO report.
    """
    # Create Object
    new_report = POReport(**payload.model_dump())
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="POReport",
        resource_id=str(new_report.id),
        resource_name=new_report.project or "PO Report",
        details=json.dumps({"so_number": new_report.so_number, "project": new_report.project}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return POReportOut.model_validate(new_report).model_dump(by_alias=True)


@POReportRouter.get("/report/{id}", response_model=POReportOut)
def get_report(
        id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Get a specific PO report by ID.
    """
    report = db.query(POReport).filter(POReport.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{id}' not found"
        )

    return POReportOut.model_validate(report).model_dump(by_alias=True)


@POReportRouter.put("/report/{id}", response_model=POReportOut)
def update_report(
        id: str,
        payload: POReportUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Update an existing PO report.
    """
    report = db.query(POReport).filter(POReport.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{id}' not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(report, key):
            setattr(report, key, value)

    db.add(report)
    db.commit()
    db.refresh(report)

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="POReport",
        resource_id=str(id),
        resource_name=report.project or "PO Report",
        details=json.dumps(update_data),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return POReportOut.model_validate(report).model_dump(by_alias=True)


@POReportRouter.delete("/report/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
        id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Delete a PO report.
    """
    report = db.query(POReport).filter(POReport.id == id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with id '{id}' not found"
        )

    # Store for audit
    report_project = report.project

    db.delete(report)
    db.commit()

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="POReport",
        resource_id=str(id),
        resource_name=report_project or "PO Report",
        details=None,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return


@POReportRouter.post("/upload-csv", response_model=POReportUploadResponse)
async def upload_csv(
        request: Request,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Upload a CSV file to bulk import PO reports.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed."
        )

    try:
        # Read CSV file with multiple encoding attempts
        contents = await file.read()

        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']
        decoded = None

        for encoding in encodings:
            try:
                decoded = contents.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file. Please ensure it's properly encoded."
            )

        csv_reader = csv.DictReader(io.StringIO(decoded))

        total_rows = 0
        successful_rows = 0
        failed_rows = 0
        errors = []

        # CSV column mapping to database fields
        # Note: CSV headers may have leading/trailing spaces, so we'll normalize them
        csv_to_db_mapping = {
            'Pur. Doc.': 'pur_doc',
            'Customer Site Ref': 'customer_site_ref',
            'Project': 'project',
            'SO#': 'so_number',
            'Material DES': 'material_des',
            'RR Date': 'rr_date',
            'Site name': 'site_name',
            'WBS Element': 'wbs_element',
            'Supplier': 'supplier',
            'Name 1': 'name_1',
            'Order date': 'order_date',
            'GR date': 'gr_date',
            'Supplier Invoice': 'supplier_invoice',
            'IR Docdate': 'ir_docdate',
            'Pstng Date': 'pstng_date',
            'PO Value SAR': 'po_value_sar',
            'Invoiced Value SAR': 'invoiced_value_sar',
            '% Invoiced': 'percent_invoiced',
            'Balance Value SAR': 'balance_value_sar',
            'SVO Number': 'svo_number',
            'Header text': 'header_text',
            'SMP ID': 'smp_id',
            'Remarks': 'remarks',
            'AInd': 'aind',
            'Accounting indicator desc': 'accounting_indicator_desc'
        }

        # Normalize CSV headers by stripping spaces
        normalized_mapping = {k.strip(): v for k, v in csv_to_db_mapping.items()}

        # Process in batches to avoid timeouts
        BATCH_SIZE = 500
        batch_count = 0

        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
            total_rows += 1

            # Skip empty rows
            if all(not value or not value.strip() for value in row.values()):
                continue

            try:
                # Map CSV columns to database fields
                record_data = {}

                # Normalize row keys (strip spaces from CSV headers)
                normalized_row = {k.strip(): v for k, v in row.items()}

                for csv_col, db_field in normalized_mapping.items():
                    value = normalized_row.get(csv_col, '').strip() if normalized_row.get(csv_col) else None
                    # Convert empty strings to None
                    record_data[db_field] = value if value else None

                # Create new record
                new_record = POReport(**record_data)
                db.add(new_record)
                successful_rows += 1
                batch_count += 1

                # Commit in batches to avoid timeout
                if batch_count >= BATCH_SIZE:
                    db.commit()
                    batch_count = 0

            except Exception as e:
                failed_rows += 1
                errors.append(f"Row {row_num}: {str(e)}")
                # Don't let one bad row stop the whole process
                db.rollback()
                batch_count = 0

        # Commit any remaining records
        if batch_count > 0:
            db.commit()

        # Create audit log for upload
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="upload_csv",
            resource_type="POReport",
            resource_id=None,
            resource_name=file.filename,
            details=json.dumps({
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return POReportUploadResponse(
            message=f"CSV upload completed. {successful_rows} records imported successfully.",
            total_rows=total_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            errors=errors[:50]  # Limit errors to first 50
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {str(e)}"
        )


@POReportRouter.delete("/delete-all", status_code=status.HTTP_200_OK)
def delete_all_reports(
        request: Request,
        confirm: bool = Query(False, description="Must be true to confirm deletion"),
        db: Session = Depends(get_db),
        current_user: User = Depends(require_approval_access)
):
    """
    Delete all PO reports. Requires confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required. Set confirm=true to proceed."
        )

    # Check if user is senior admin
    if current_user.role.name != "senior_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only senior admins can delete all reports."
        )

    # Delete all reports
    count = db.query(POReport).delete()

    db.commit()

    # Create audit log
    create_audit_log_sync(
        db=db,
        user_id=current_user.id,
        action="delete_all",
        resource_type="POReport",
        resource_id=None,
        resource_name="All PO Reports",
        details=json.dumps({"deleted_count": count}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return {
        "message": f"Successfully deleted {count} PO report(s).",
        "deleted_count": count
    }
