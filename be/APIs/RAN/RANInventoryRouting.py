from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
import json
import logging

from APIs.Core import safe_int, get_db, get_current_user
from utils.file_validation import validate_csv_file  # SECURITY: File upload validation
from Models.Admin.User import UserProjectAccess, User
from Models.Admin.AuditLog import AuditLog

logger = logging.getLogger(__name__)
from Schemas.RAN.RANInventorySchema import (
    RANInventoryCreate,
    RANInventoryInDB,
    RANInventoryUpdate,
    PaginatedRANInventoryResponse
)
from Models.RAN.RANInventory import RANInventory

RANInventoryRouter = APIRouter(
    prefix="/raninventory",
    tags=["RANInventory"]
)


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


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_raninventory_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project for RANInventory operations.
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == pid_po
    ).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_accessible_projects_for_inventory(current_user: User, db: Session):
    """
    Get all project IDs that the current user has access to for inventory operations.
    """
    if current_user.role.name == "senior_admin":
        return None  # Senior admin can access all projects

    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    return [access.Ranproject_id for access in user_accesses]


# --------------------------------------------------------------------------------
# CRUD Methods
# --------------------------------------------------------------------------------

def get_raninventory(db: Session, raninventory_id: int):
    return db.query(RANInventory).filter(RANInventory.id == raninventory_id).first()


def get_all_raninventory(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None,
                         accessible_projects: List[str] = None, project_id: Optional[str] = None):
    query = db.query(RANInventory)

    # Filter by accessible projects if not senior admin
    if accessible_projects is not None:
        if not accessible_projects:  # Empty list means no access
            return {"total": 0, "records": []}
        query = query.filter(RANInventory.pid_po.in_(accessible_projects))

    # Filter by specific project if provided
    if project_id:
        # Also check if user has access to this specific project
        if accessible_projects is not None and project_id not in accessible_projects:
            return {"total": 0, "records": []}
        query = query.filter(RANInventory.pid_po == project_id)

    if search:
        search_pattern = f"%{search}%"
        # Search across multiple fields
        query = query.filter(
            RANInventory.mrbts.ilike(search_pattern) |
            RANInventory.site_id.ilike(search_pattern) |
            RANInventory.identification_code.ilike(search_pattern) |
            RANInventory.user_label.ilike(search_pattern) |
            RANInventory.serial_number.ilike(search_pattern)
        )

    total = query.count()
    records = query.order_by(RANInventory.id).offset(skip).limit(limit).all()
    return {"total": total, "records": records}


def create_raninventory(db: Session, raninventory: RANInventoryCreate):
    db_raninventory = RANInventory(**raninventory.model_dump())
    db.add(db_raninventory)
    db.commit()
    db.refresh(db_raninventory)
    return db_raninventory


def update_raninventory(db: Session, raninventory_id: int, raninventory_data: RANInventoryUpdate):
    db_raninventory = get_raninventory(db, raninventory_id)
    if not db_raninventory:
        return None

    update_data = raninventory_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_raninventory, key, value)

    db.commit()
    db.refresh(db_raninventory)
    return db_raninventory


def delete_raninventory(db: Session, raninventory_id: int):
    db_raninventory = db.query(RANInventory).filter(RANInventory.id == raninventory_id).first()
    if not db_raninventory:
        return False
    db.delete(db_raninventory)
    db.commit()
    return True


# --------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------

@RANInventoryRouter.post("/", response_model=RANInventoryInDB, status_code=status.HTTP_201_CREATED)
def create_ran_inventory(
        raninventory_data: RANInventoryCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN Inventory record.
    """
    # Check if user has edit permission for the project (if pid_po is provided)
    if raninventory_data.pid_po:
        if not check_raninventory_project_access(current_user, raninventory_data.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create RAN Inventory records for this project. Contact the Senior Admin."
            )

    try:
        db_raninventory = create_raninventory(db=db, raninventory=raninventory_data)
        if not db_raninventory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating RAN Inventory record"
            )

        # Create audit log
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="create",
            resource_type="RANInventory",
            resource_id=str(db_raninventory.id),
            resource_name=db_raninventory.serial_number,
            details=json.dumps({"pid_po": raninventory_data.pid_po}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return db_raninventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.get("", response_model=PaginatedRANInventoryResponse)
def get_all_ran_inventory_records(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        search: Optional[str] = Query(None),
        project_id: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve all RAN Inventory records with pagination and optional search.
    Users can only see records from projects they have access to.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        search: Search term to filter by MRBTS, Site ID, Serial Number, etc.
        project_id: Filter by specific project ID (pid_po)
    """
    try:
        accessible_projects = get_accessible_projects_for_inventory(current_user, db)
        result = get_all_raninventory(db=db, skip=skip, limit=limit, search=search,
                                      accessible_projects=accessible_projects, project_id=project_id)
        return PaginatedRANInventoryResponse(total=result["total"], records=result["records"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN Inventory records: {str(e)}"
        )


@RANInventoryRouter.get("/stats")
def get_ran_inventory_stats(
        project_id: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get statistics for RAN Inventory records.

    Args:
        project_id: Optional project ID to filter statistics
    """
    try:
        accessible_projects = get_accessible_projects_for_inventory(current_user, db)
        query = db.query(RANInventory)

        # Filter by accessible projects if not senior admin
        if accessible_projects is not None:
            if not accessible_projects:
                return {"total_items": 0, "unique_sites": 0}
            query = query.filter(RANInventory.pid_po.in_(accessible_projects))

        # Filter by specific project if provided
        if project_id:
            if accessible_projects is not None and project_id not in accessible_projects:
                return {"total_items": 0, "unique_sites": 0}
            query = query.filter(RANInventory.pid_po == project_id)

        total_items = query.count()
        unique_sites = query.distinct(RANInventory.site_id).count()

        return {
            "total_items": total_items,
            "unique_sites": unique_sites
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving RAN Inventory stats: {str(e)}"
        )


@RANInventoryRouter.get("/{raninventory_id}", response_model=RANInventoryInDB)
def get_ran_inventory_by_id(
        raninventory_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve a single RAN Inventory record by its ID.
    """
    db_raninventory = get_raninventory(db=db, raninventory_id=raninventory_id)
    if db_raninventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has view permission for the project (if pid_po exists)
    if db_raninventory.pid_po:
        if not check_raninventory_project_access(current_user, db_raninventory.pid_po, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this RAN Inventory record. Contact the Senior Admin."
            )

    return db_raninventory


@RANInventoryRouter.put("/{raninventory_id}", response_model=RANInventoryInDB)
def update_ran_inventory_record(
        raninventory_id: int,
        raninventory_data: RANInventoryUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing RAN Inventory record.
    """
    # First check if record exists
    existing_record = get_raninventory(db, raninventory_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has edit permission for the project (if pid_po exists)
    if existing_record.pid_po:
        if not check_raninventory_project_access(current_user, existing_record.pid_po, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this RAN Inventory record. Contact the Senior Admin."
            )

    try:
        db_raninventory = update_raninventory(db=db, raninventory_id=raninventory_id,
                                              raninventory_data=raninventory_data)

        # Create audit log
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="update",
            resource_type="RANInventory",
            resource_id=str(raninventory_id),
            resource_name=db_raninventory.serial_number,
            details=json.dumps({"pid_po": db_raninventory.pid_po}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return db_raninventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.delete("/{raninventory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_inventory_record(
        raninventory_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN Inventory record by its ID.
    """
    # First check if record exists
    existing_record = get_raninventory(db, raninventory_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

    # Check if user has all permission for the project (required for deletion)
    if existing_record.pid_po:
        if not check_raninventory_project_access(current_user, existing_record.pid_po, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this RAN Inventory record. Contact the Senior Admin."
            )

    # Store for audit
    serial_number = existing_record.serial_number
    pid_po = existing_record.pid_po

    try:
        success = delete_raninventory(db=db, raninventory_id=raninventory_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAN Inventory record not found")

        # Create audit log
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="delete",
            resource_type="RANInventory",
            resource_id=str(raninventory_id),
            resource_name=serial_number,
            details=json.dumps({"pid_po": pid_po}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "RAN Inventory record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting RAN Inventory record: {str(e)}"
        )


@RANInventoryRouter.post("/upload-csv", response_model=dict)
async def upload_ran_inventory_csv(
        request: Request,
        file: UploadFile = File(...),
        pid_po: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file to bulk-add RAN Inventory records.
    The CSV must have headers matching the RANInventory schema fields.
    The pid_po parameter will be used for all records in the CSV.
    OPTIMIZED: Uses bulk insert operations for better performance.
    """
    # Check access for the provided project
    if not check_raninventory_project_access(current_user, pid_po, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files for this project. Contact the Senior Admin."
        )

    # SECURITY: Validate file size and type
    await validate_csv_file(file, max_size=50 * 1024 * 1024)  # 50 MB limit

    try:
        contents = await file.read()
        csv_reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))

        # OPTIMIZED: Build list of dictionaries for bulk insert
        bulk_data = []
        for row in csv_reader:
            # Try different possible column names for flexibility
            mrbts = row.get('MRBTS') or row.get('mrbts') or row.get('Mrbts')
            site_id = row.get('Site ID') or row.get('site_id') or row.get('SiteID') or row.get('Site_ID')
            identification_code = row.get('identificationCode') or row.get('identification_code') or row.get('IdentificationCode') or row.get('Identification Code')
            user_label = row.get('userLabel') or row.get('user_label') or row.get('UserLabel') or row.get('User Label')
            serial_number = row.get('serialNumber') or row.get('serial_number') or row.get('SerialNumber') or row.get('Serial Number')
            duplicate = row.get('Duplicate') or row.get('duplicate')
            duplicate_remarks = row.get('Duplicate remarks') or row.get('duplicate_remarks') or row.get('Duplicate_remarks') or row.get('DuplicateRemarks')

            # OPTIMIZED: Append dictionary instead of object
            bulk_data.append({
                'mrbts': mrbts,
                'site_id': site_id,
                'identification_code': identification_code,
                'user_label': user_label,
                'serial_number': serial_number,
                'duplicate': True if duplicate and str(duplicate).lower() in ['true', '1', 'yes', 'y'] else False,
                'duplicate_remarks': duplicate_remarks,
                'pid_po': pid_po,  # Use the form parameter for all records
            })

        # OPTIMIZED: Single bulk insert instead of add_all
        if bulk_data:
            db.bulk_insert_mappings(RANInventory, bulk_data)
            db.commit()

        # Create audit log
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="upload_csv",
            resource_type="RANInventory",
            resource_id=pid_po,
            resource_name=file.filename,
            details=json.dumps({"pid_po": pid_po, "rows_inserted": len(bulk_data)}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"Successfully added {len(bulk_data)} records from CSV with pid_po: {pid_po}"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV file: {str(e)}"
        )


@RANInventoryRouter.delete("/delete-all-inventory/{pid_po}")
def delete_all_ran_inventory_for_project(
        pid_po: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all RAN Inventory records for a project.
    Users need 'all' permission on the project to delete all inventory.

    Returns:
    - deleted_inventory: Number of RAN inventory records deleted
    - affected_tables: List of tables that had data deleted
    """
    # Check user has 'all' permission
    if not check_raninventory_project_access(current_user, pid_po, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete RAN inventory for this project."
        )

    try:
        # Get count of inventory for this project
        inventory_count = db.query(RANInventory).filter(RANInventory.pid_po == pid_po).count()

        if inventory_count == 0:
            raise HTTPException(status_code=404, detail="No RAN inventory found for this project")

        # Delete all RAN inventory for this project
        inventory_deleted = db.query(RANInventory).filter(RANInventory.pid_po == pid_po).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        create_audit_log_sync(
            db=db,
            user_id=current_user.id,
            action="delete_all",
            resource_type="RANInventory",
            resource_id=pid_po,
            resource_name=f"All inventory for {pid_po}",
            details=json.dumps({"pid_po": pid_po, "deleted_count": inventory_deleted}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "All RAN inventory deleted successfully",
            "deleted_inventory": inventory_deleted,
            "affected_tables": ["ran_inventory"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete RAN inventory: {str(e)}")