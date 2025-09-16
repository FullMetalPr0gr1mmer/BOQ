from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from io import StringIO
import csv
import json

from APIs.Admin.AdminRoute import create_audit_log, get_client_ip
from APIs.BOQ.ProjectRoute import get_user_accessible_projects, get_project_for_boq, check_project_access
from APIs.Core import get_db, get_current_user
from Models.Admin.User import User
from Models.BOQ.Dismantling import Dismantling

from Schemas.BOQ.DismantlingSchema import DismantlingCreate, DismantlingUpdate, DismantlingOut, DismantlingPagination


DismantlingRouter = APIRouter(prefix="/dismantling", tags=["Dismantling"])


# ---------- CRUD with Routers and Access Control ----------

@DismantlingRouter.get("", response_model=DismantlingPagination)
def get_all(
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieves a paginated and searchable list of dismantling records accessible to the current user.
    """
    # Get all projects the user has access to
    accessible_projects = get_user_accessible_projects(current_user, db)
    if not accessible_projects:
        return {"records": [], "total": 0}

    # Filter dismantling records by the user's accessible projects (using pid_po)
    accessible_pids_po = [p.pid_po for p in accessible_projects]
    query = db.query(Dismantling).filter(Dismantling.pid_po.in_(accessible_pids_po))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Dismantling.nokia_link_id.like(search_pattern),
                Dismantling.nec_dismantling_link_id.like(search_pattern),
                Dismantling.comments.like(search_pattern),
            )
        )

    total_count = query.count()
    records = query.order_by(Dismantling.id).offset(skip).limit(limit).all()

    return {"records": records, "total": total_count}


@DismantlingRouter.post("", response_model=DismantlingOut)
async def create_dismantling(
        obj_in: DismantlingCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new dismantling record with access control and audit logging.
    """
    # Check project access
    project = get_project_for_boq(obj_in.pid_po, db)
    if not project or not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create dismantling records for this project."
        )

    db_obj = Dismantling(**obj_in.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # Create audit log
    await create_audit_log(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="dismantling",
        resource_id=str(db_obj.id),
        resource_name=f"Dismantling Record {db_obj.id}",
        details=json.dumps(obj_in.dict()),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
    return db_obj


@DismantlingRouter.get("/{id}", response_model=DismantlingOut)
def get_by_id(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Retrieves a single dismantling record by ID with access control.
    """
    obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Record not found")

    # Check project access
    project = get_project_for_boq(obj.pid_po, db)
    if not project or not check_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this record."
        )
    return obj


@DismantlingRouter.put("/{id}", response_model=DismantlingOut)
async def update_dismantling(
        id: int,
        obj_in: DismantlingUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Updates a dismantling record with access control and audit logging.
    """
    db_obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")

    # Check project access
    project = get_project_for_boq(db_obj.pid_po, db)
    if not project or not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this record."
        )

    # Get old values for logging
    old_values = {key: getattr(db_obj, key) for key in obj_in.dict(exclude_unset=True).keys()}

    for field, value in obj_in.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)

    db.commit()
    db.refresh(db_obj)

    # Create audit log
    await create_audit_log(
        db=db,
        user_id=current_user.id,
        action="update",
        resource_type="dismantling",
        resource_id=str(db_obj.id),
        resource_name=f"Dismantling Record {db_obj.id}",
        details=json.dumps({"old_values": old_values, "new_values": obj_in.dict(exclude_unset=True)}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
    return db_obj


@DismantlingRouter.delete("/{id}")
async def delete_dismantling(
        id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes a dismantling record with access control and audit logging.
    """
    db_obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")

    # Check project access
    project = get_project_for_boq(db_obj.pid_po, db)
    if not project or not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this record."
        )

    db.delete(db_obj)
    db.commit()

    # Create audit log
    await create_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete",
        resource_type="dismantling",
        resource_id=str(id),
        resource_name=f"Dismantling Record {id}",
        details=json.dumps({"pid_po": db_obj.pid_po}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
    return {"deleted_id": id}


# ---------- CSV Upload with Access Control and Logging ----------
@DismantlingRouter.post("/upload-csv")
async def upload_csv(request: Request,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file, creates dismantling records, and logs the action.
    The CSV should contain a `pid_po` column.
    """
    content = await file.read()
    csv_reader = csv.reader(StringIO(content.decode("utf-8")))

    # Get header row
    header = next(csv_reader, None)
    if not header:
        raise HTTPException(status_code=400, detail="CSV is empty.")

    # Check for required fields and get their indices
    try:
        pid_po_index = header.index("pid_po")
        nokia_link_id_index = header.index("nokia_link_id")
        nec_dismantling_link_id_index = header.index("nec_dismantling_link_id")
        no_of_dismantling_index = header.index("no_of_dismantling")
        comments_index = header.index("comments")
    except ValueError as e:
        raise HTTPException(status_code=400,
                            detail=f"Missing required CSV column: {e}. Required columns are: pid_po, nokia_link_id, nec_dismantling_link_id, no_of_dismantling, comments")

    inserted_count = 0
    # Dictionary to track project access
    project_access_cache = {}

    for row in csv_reader:
        if not row:
            continue

        pid_po = row[pid_po_index].strip() if pid_po_index < len(row) else None
        if not pid_po:
            continue

        # Check project access using a cache to avoid repeated DB calls
        if pid_po not in project_access_cache:
            project = get_project_for_boq(pid_po, db)
            has_access = project and check_project_access(current_user, project, db, "edit")
            project_access_cache[pid_po] = (has_access, project)

        has_access, project = project_access_cache.get(pid_po, (False, None))

        if not has_access:
            print(f"Skipping record for project {pid_po} due to insufficient permissions.")
            continue

        try:
            no_of_dismantling = int(row[no_of_dismantling_index].strip())
        except (ValueError, IndexError):
            continue

        obj_in = DismantlingCreate(
            nokia_link_id=row[nokia_link_id_index].strip(),
            nec_dismantling_link_id=row[nec_dismantling_link_id_index].strip(),
            no_of_dismantling=no_of_dismantling,
            comments=row[comments_index].strip() if comments_index < len(row) else None,
            pid_po=pid_po
        )
        db_obj = Dismantling(**obj_in.dict())
        db.add(db_obj)
        inserted_count += 1

    db.commit()

    # Create a single audit log for the entire upload operation
    await create_audit_log(
        db=db,
        user_id=current_user.id,
        action="upload_csv",
        resource_type="dismantling",
        resource_name=file.filename,
        details=json.dumps({"inserted_count": inserted_count, "filename": file.filename}),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )
    return {"inserted": inserted_count}