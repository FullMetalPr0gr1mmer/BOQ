from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from typing import List
import csv
from io import StringIO

# Core and Schema Imports
from APIs.Core import get_db, get_current_user
from Models.BOQ.LLD import LLD
from Schemas.BOQ.LLDSchema import LLDCreate, LLDOut, LLDListOut

# Model Imports for Authentication & Authorization
from Models.Admin.User import User, UserProjectAccess
from Models.BOQ.Project import Project


lld_router = APIRouter(prefix="/lld", tags=["LLD"])

# --- ADMINISTRATION & ACCESS CONTROL HELPERS ---
# NOTE: For better code organization, these helpers could be moved to a shared 'auth_utils.py' file.

def check_project_access(current_user: User, project: Project, db: Session, required_permission: str = "view"):
    """
    Helper function to check if a user has access to a project with the required permission level.
    """
    if not project:
        return False  # No project, no access.
    if current_user.role.name == "senior_admin":
        return True

    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po
    ).first()

    if not access:
        return False

    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }
    return access.permission_level in permission_hierarchy.get(required_permission, [])

def get_user_accessible_project_ids(current_user: User, db: Session) -> List[str]:
    """
    Returns a list of project IDs (pid_po) that the current user has access to.
    """
    if current_user.role.name == "senior_admin":
        # Return all project IDs if the user is a senior admin
        return [p.pid_po for p in db.query(Project.pid_po).all()]

    # Otherwise, return only the IDs the user has explicit access to
    return [
        access.project_id for access in db.query(UserProjectAccess.project_id).filter(
            UserProjectAccess.user_id == current_user.id
        ).all()
    ]


# ---------------- GET (list with pagination + search) ----------------
@lld_router.get("", response_model=LLDListOut)
def get_lld(
    skip: int = 0,
    limit: int = 100,
    link_id: str = "",
    project_id: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Get projects the user can access
    accessible_project_ids = get_user_accessible_project_ids(current_user, db)
    if not accessible_project_ids:
        return {"total": 0, "items": []} # No access, return empty

    # 2. Base query filtered by accessible projects
    query = db.query(LLD).filter(LLD.pid_po.in_(accessible_project_ids))

    # 3. Apply optional project filter
    if project_id:
        # Ensure the requested project is in the user's accessible projects
        if project_id not in accessible_project_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this project.")
        query = query.filter(LLD.pid_po == project_id)

    # 4. Apply optional search filter
    if link_id:
        query = query.filter(LLD.link_id.contains(link_id))

    total = query.count()
    items = query.order_by(LLD.id).offset(skip).limit(limit).all()
    return {"total": total, "items": items}

# ---------------- POST (create single row) ----------------
@lld_router.post("", response_model=LLDOut)
def create_lld(
    data: LLDCreate, # Assumes LLDCreate schema now includes 'pid_po'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Authorization Check
    project = db.query(Project).filter(Project.pid_po == data.pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID '{data.pid_po}' not found.")

    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to create LLD records for this project."
        )

    # 2. Create Object
    db_obj = LLD(**data.dict())
    db.add(db_obj)
    try:
        db.commit()
        db.refresh(db_obj)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {e}")
    return db_obj

# ---------------- PUT (update row) ----------------
@lld_router.put("/{link_id}", response_model=LLDOut)
def update_lld(
    link_id: str,
    data: LLDCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_obj = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="LLD row not found")

    # 1. Authorization Check based on the existing record's project
    project = db.query(Project).filter(Project.pid_po == db_obj.pid_po).first()
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update LLD records for this project."
        )

    # 2. Update Object
    update_data = data.dict()
    # Prevent changing the project ID during an update
    update_data.pop("pid_po", None)

    for key, value in update_data.items():
        setattr(db_obj, key, value)

    db.commit()
    db.refresh(db_obj)
    return db_obj

# ---------------- DELETE ----------------
@lld_router.delete("/{link_id}")
def delete_lld(
    link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_obj = db.query(LLD).filter(LLD.link_id == link_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="LLD row not found")

    # 1. Authorization Check (requires "all" permission for deletion)
    project = db.query(Project).filter(Project.pid_po == db_obj.pid_po).first()
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to delete LLD records for this project."
        )

    # 2. Delete Object
    db.delete(db_obj)
    db.commit()
    return {"detail": f"LLD record for {link_id} deleted successfully"}

# ---------------- CSV Upload ----------------
@lld_router.post("/upload-csv")
def upload_csv(
    project_id: str = Query(..., description="The Project ID (pid_po) to associate the LLD records with."),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Authorization Check
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Project with ID '{project_id}' not found.")

    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to upload LLD data for this project."
        )

    # 2. Process CSV File
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .csv file.")

    try:
        content = file.file.read().decode("utf-8-sig")
        reader = csv.DictReader(StringIO(content))
        inserted = 0
        to_insert = []
        for row in reader:
            # Skip empty rows
            if not any(row.values()):
                continue

            lld_data = {
                "pid_po": project_id, # Associate with the specified project
                "link_id": row.get("link ID", "").strip(),
                "action": row.get("Action", "").strip(),
                "fon": row.get("FON", "").strip(),
                "item_name": row.get("configuration", "").strip(),
                "distance": row.get("Distance", "").strip(),
                "scope": row.get("Scope", "").strip(),
                "ne": row.get("NE", "").strip(),
                "fe": row.get("FE", "").strip(),
                "link_category": row.get("link catergory", "").strip(),
                "link_status": row.get("Link status", "").strip(),
                "comments": row.get("COMMENTS", "").strip(),
                "dismanting_link_id": row.get("Dismanting link ID", "").strip(),
                "band": row.get("Band", "").strip(),
                "t_band_cs": row.get("T-band CS", "").strip(),
                "ne_ant_size": row.get("NE Ant size", "").strip(),
                "fe_ant_size": row.get("FE Ant Size", "").strip(),
                "sd_ne": row.get("SD NE", "").strip(),
                "sd_fe": row.get("SD FE", "").strip(),
                "odu_type": row.get("ODU TYPE", "").strip(),
                "updated_sb": row.get("Updated SB", "").strip(),
                "region": row.get("Region", "").strip(),
                "losr_approval": row.get("LOSR approval", "").strip(),
                "initial_lb": row.get("initial LB", "").strip(),
                "flb": row.get("FLB", "").strip(),
            }
            # Only add if link_id is present
            if lld_data["link_id"]:
                to_insert.append(LLD(**lld_data))

        if not to_insert:
            raise HTTPException(status_code=400, detail="No valid rows with a 'link ID' found in the CSV.")

        db.bulk_save_objects(to_insert)
        db.commit()
        inserted = len(to_insert)

        return {"rows_inserted": inserted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {e}")



@lld_router.delete("/delete-all-lld/{project_id}")
async def delete_all_lld_for_project(
        project_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all LLD records for a project.
    Users need 'all' permission on the project to delete all LLD records.

    Returns:
    - deleted_lld: Number of LLD records deleted
    - affected_tables: List of tables that had data deleted
    """
    # Check if project exists
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check project access - need 'all' permission
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete LLD records for this project."
        )

    try:
        # Get count of LLD records for this project
        lld_count = db.query(LLD).filter(LLD.pid_po == project_id).count()

        if lld_count == 0:
            raise HTTPException(status_code=404, detail="No LLD records found for this project")

        # Delete all LLD records for this project
        lld_deleted = db.query(LLD).filter(LLD.pid_po == project_id).delete(synchronize_session=False)

        db.commit()

        return {
            "message": "All LLD records deleted successfully",
            "deleted_lld": lld_deleted,
            "affected_tables": ["lld"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete LLD records: {str(e)}")
