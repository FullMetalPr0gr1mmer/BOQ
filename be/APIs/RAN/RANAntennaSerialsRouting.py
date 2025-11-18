from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io

from APIs.Core import get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from Schemas.RAN.RANAntennaSerialsSchema import (
    RANAntennaSerialsCreate,
    RANAntennaSerialsOut,
    RANAntennaSerialsUpdate,
    PaginatedRANAntennaSerials
)
from Models.RAN.RANAntennaSerials import RANAntennaSerials

RANAntennaSerialsRouter = APIRouter(
    prefix="/ran-antenna-serials",
    tags=["RAN Antenna Serials"]
)


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_antenna_serials_project_access(current_user: User, project_id: str, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project for antenna serials operations.
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ranproject_id == project_id
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


def get_accessible_projects_for_antenna_serials(current_user: User, db: Session):
    """
    Get all project IDs that the current user has access to for antenna serials operations.
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

def get_antenna_serial(db: Session, antenna_serial_id: int):
    return db.query(RANAntennaSerials).filter(RANAntennaSerials.id == antenna_serial_id).first()


def get_all_antenna_serials(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None,
                            accessible_projects: List[str] = None, project_id: Optional[str] = None):
    query = db.query(RANAntennaSerials)

    # Filter by accessible projects if not senior admin
    if accessible_projects is not None:
        if not accessible_projects:  # Empty list means no access
            return {"total": 0, "records": []}
        query = query.filter(RANAntennaSerials.project_id.in_(accessible_projects))

    # Filter by specific project if provided
    if project_id:
        # Also check if user has access to this specific project
        if accessible_projects is not None and project_id not in accessible_projects:
            return {"total": 0, "records": []}
        query = query.filter(RANAntennaSerials.project_id == project_id)

    if search:
        search_pattern = f"%{search}%"
        # Search across multiple fields
        query = query.filter(
            RANAntennaSerials.mrbts.ilike(search_pattern) |
            RANAntennaSerials.antenna_model.ilike(search_pattern) |
            RANAntennaSerials.serial_number.ilike(search_pattern)
        )

    total = query.count()
    records = query.order_by(RANAntennaSerials.id).offset(skip).limit(limit).all()
    return {"total": total, "records": records}


def create_antenna_serial(db: Session, antenna_serial: RANAntennaSerialsCreate):
    db_antenna_serial = RANAntennaSerials(**antenna_serial.model_dump())
    db.add(db_antenna_serial)
    db.commit()
    db.refresh(db_antenna_serial)
    return db_antenna_serial


def update_antenna_serial(db: Session, antenna_serial_id: int, antenna_serial_data: RANAntennaSerialsUpdate):
    db_antenna_serial = get_antenna_serial(db, antenna_serial_id)
    if not db_antenna_serial:
        return None

    update_data = antenna_serial_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_antenna_serial, key, value)

    db.commit()
    db.refresh(db_antenna_serial)
    return db_antenna_serial


def delete_antenna_serial(db: Session, antenna_serial_id: int):
    db_antenna_serial = db.query(RANAntennaSerials).filter(RANAntennaSerials.id == antenna_serial_id).first()
    if not db_antenna_serial:
        return False
    db.delete(db_antenna_serial)
    db.commit()
    return True


# --------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------

@RANAntennaSerialsRouter.post("/", response_model=RANAntennaSerialsOut, status_code=status.HTTP_201_CREATED)
def create_ran_antenna_serial(
        antenna_serial_data: RANAntennaSerialsCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new RAN Antenna Serial record.
    """
    # Check if user has edit permission for the project (if project_id is provided)
    if antenna_serial_data.project_id:
        if not check_antenna_serials_project_access(current_user, antenna_serial_data.project_id, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create antenna serial records for this project. Contact the Senior Admin."
            )

    try:
        db_antenna_serial = create_antenna_serial(db=db, antenna_serial=antenna_serial_data)
        if not db_antenna_serial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating antenna serial record"
            )
        return db_antenna_serial
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating antenna serial record: {str(e)}"
        )


@RANAntennaSerialsRouter.get("", response_model=PaginatedRANAntennaSerials)
def get_all_ran_antenna_serials(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        search: Optional[str] = Query(None),
        project_id: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve all RAN Antenna Serial records with pagination and optional search.
    Users can only see records from projects they have access to.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        search: Search term to filter by MRBTS, antenna model, or serial number
        project_id: Filter by specific project ID
    """
    try:
        accessible_projects = get_accessible_projects_for_antenna_serials(current_user, db)
        result = get_all_antenna_serials(db=db, skip=skip, limit=limit, search=search,
                                        accessible_projects=accessible_projects, project_id=project_id)
        return PaginatedRANAntennaSerials(total=result["total"], records=result["records"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving antenna serial records: {str(e)}"
        )


@RANAntennaSerialsRouter.get("/stats")
def get_ran_antenna_serials_stats(
        project_id: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get statistics for RAN Antenna Serial records.

    Args:
        project_id: Optional project ID to filter statistics
    """
    try:
        accessible_projects = get_accessible_projects_for_antenna_serials(current_user, db)
        query = db.query(RANAntennaSerials)

        # Filter by accessible projects if not senior admin
        if accessible_projects is not None:
            if not accessible_projects:
                return {"total_antennas": 0, "unique_mrbts": 0}
            query = query.filter(RANAntennaSerials.project_id.in_(accessible_projects))

        # Filter by specific project if provided
        if project_id:
            if accessible_projects is not None and project_id not in accessible_projects:
                return {"total_antennas": 0, "unique_mrbts": 0}
            query = query.filter(RANAntennaSerials.project_id == project_id)

        total_antennas = query.count()
        unique_mrbts = query.distinct(RANAntennaSerials.mrbts).count()

        return {
            "total_antennas": total_antennas,
            "unique_mrbts": unique_mrbts
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving antenna serial stats: {str(e)}"
        )


@RANAntennaSerialsRouter.get("/{antenna_serial_id}", response_model=RANAntennaSerialsOut)
def get_ran_antenna_serial_by_id(
        antenna_serial_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieve a single RAN Antenna Serial record by its ID.
    """
    db_antenna_serial = get_antenna_serial(db=db, antenna_serial_id=antenna_serial_id)
    if db_antenna_serial is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antenna serial record not found")

    # Check if user has view permission for the project (if project_id exists)
    if db_antenna_serial.project_id:
        if not check_antenna_serials_project_access(current_user, db_antenna_serial.project_id, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this antenna serial record. Contact the Senior Admin."
            )

    return db_antenna_serial


@RANAntennaSerialsRouter.put("/{antenna_serial_id}", response_model=RANAntennaSerialsOut)
def update_ran_antenna_serial(
        antenna_serial_id: int,
        antenna_serial_data: RANAntennaSerialsUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing RAN Antenna Serial record.
    """
    # First check if record exists
    existing_record = get_antenna_serial(db, antenna_serial_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antenna serial record not found")

    # Check if user has edit permission for the project (if project_id exists)
    if existing_record.project_id:
        if not check_antenna_serials_project_access(current_user, existing_record.project_id, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this antenna serial record. Contact the Senior Admin."
            )

    try:
        db_antenna_serial = update_antenna_serial(db=db, antenna_serial_id=antenna_serial_id,
                                                  antenna_serial_data=antenna_serial_data)
        return db_antenna_serial
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating antenna serial record: {str(e)}"
        )


@RANAntennaSerialsRouter.delete("/{antenna_serial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ran_antenna_serial(
        antenna_serial_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a RAN Antenna Serial record by its ID.
    """
    # First check if record exists
    existing_record = get_antenna_serial(db, antenna_serial_id)
    if existing_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antenna serial record not found")

    # Check if user has all permission for the project (required for deletion)
    if existing_record.project_id:
        if not check_antenna_serials_project_access(current_user, existing_record.project_id, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this antenna serial record. Contact the Senior Admin."
            )

    try:
        success = delete_antenna_serial(db=db, antenna_serial_id=antenna_serial_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Antenna serial record not found")
        return {"message": "Antenna serial record deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting antenna serial record: {str(e)}"
        )


@RANAntennaSerialsRouter.post("/upload-csv", response_model=dict)
def upload_antenna_serials_csv(
        file: UploadFile = File(...),
        project_id: str = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file to bulk-add RAN Antenna Serial records.
    The CSV must have 3 columns: MRBTS, Antenna Model, Serial Number.
    The project_id parameter will be used for all records in the CSV.
    """
    # Check access for the provided project
    if not check_antenna_serials_project_access(current_user, project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files for this project. Contact the Senior Admin."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

    try:
        contents = file.file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(contents))

        new_records = []
        for row in csv_reader:
            # Try different possible column names for flexibility
            mrbts = row.get('MRBTS') or row.get('mrbts') or row.get('Mrbts')
            antenna_model = row.get('Antenna Model') or row.get('antenna_model') or row.get('antModel') or row.get('Antenna_Model')
            serial_number = row.get('Serial Number') or row.get('serial_number') or row.get('antSerial') or row.get('Serial_Number')

            new_record = RANAntennaSerials(
                mrbts=mrbts,
                antenna_model=antenna_model,
                serial_number=serial_number,
                project_id=project_id,  # Use the form parameter for all records
            )
            new_records.append(new_record)

        if new_records:
            db.add_all(new_records)
            db.commit()

        return {"message": f"Successfully added {len(new_records)} antenna serial records from CSV with project_id: {project_id}"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV file: {str(e)}"
        )


@RANAntennaSerialsRouter.delete("/delete-all-antenna-serials/{project_id}")
def delete_all_ran_antenna_serials_for_project(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all RAN Antenna Serial records for a project.
    Users need 'all' permission on the project to delete all antenna serials.

    Returns:
    - deleted_antenna_serials: Number of RAN antenna serial records deleted
    - affected_tables: List of tables that had data deleted
    """
    # Check user has 'all' permission
    if not check_antenna_serials_project_access(current_user, project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete RAN antenna serials for this project."
        )

    try:
        # Get count of antenna serials for this project
        antenna_serials_count = db.query(RANAntennaSerials).filter(RANAntennaSerials.project_id == project_id).count()

        if antenna_serials_count == 0:
            raise HTTPException(status_code=404, detail="No RAN antenna serials found for this project")

        # Delete all RAN antenna serials for this project
        antenna_serials_deleted = db.query(RANAntennaSerials).filter(RANAntennaSerials.project_id == project_id).delete(synchronize_session=False)

        db.commit()

        return {
            "message": "All RAN antenna serials deleted successfully",
            "deleted_antenna_serials": antenna_serials_deleted,
            "affected_tables": ["ran_antenna_serials"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete RAN antenna serials: {str(e)}")
