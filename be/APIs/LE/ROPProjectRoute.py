import csv
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import and_

from APIs.Core import get_db, get_current_user
from Models.Admin.User import UserProjectAccess, User
from APIs.LE.ROPLvl1Route import create_lvl1
from APIs.LE.ROPLvl2Route import create_lvl2
from Models.LE.ROPProject import ROPProject
from Models.LE.ROPLvl1 import ROPLvl1
from Models.LE.ROPLvl2 import ROPLvl2, ROPLvl2Distribution
from Models.LE.RopPackages import RopPackage, rop_package_lvl1
from Models.LE.MonthlyDistribution import MonthlyDistribution
from Models.RAN.RANProject import RanProject
from Schemas.LE.ROPLvl1Schema import ROPLvl1Create
from Schemas.LE.ROPLvl2Schema import ROPLvl2DistributionCreate, ROPLvl2Create
from Schemas.LE.ROPProjectSchema import ROPProjectCreate, ROPProjectOut

ROPProjectrouter = APIRouter(prefix="/rop-projects", tags=["ROP Projects"])


# --------------------------------------------------------------------------------
# Access Control Helper Functions
# --------------------------------------------------------------------------------

def check_rop_project_access(
        current_user: User,
        project: ROPProject,
        db: Session, required_permission: str = "view"):


    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(and_(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ropproject_id == project.pid_po
    )  ).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_rop_projects(current_user: User, db: Session) -> List[ROPProject]:
    """
    Get all ROP projects that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[ROPProject]: List of accessible ROP projects
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(ROPProject).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.Ropproject_id for access in user_accesses]

    # Return projects that match those IDs
    return (
        db.query(ROPProject)
        .filter(
            (ROPProject.pid_po.in_(accessible_project_ids))
        )
        .all()
    )

# --------------------------------------------------------------------------------
# CRUD Endpoints
# --------------------------------------------------------------------------------

@ROPProjectrouter.post("/", response_model=ROPProjectOut)
def create_project(
        project: ROPProjectCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new ROP project. Only senior_admin can create projects.
    """
    # Only senior_admin can create projects
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action. Contact the Senior Admin."
        )

    pid_po = project.pid + project.po + str(current_user.id)
    existing = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this pid_po already exists")

    try:
        new_project = ROPProject(**project.dict())
        new_project.pid_po = pid_po
        new_project.created_by = current_user.id
        db.add(new_project)
        db.flush()
        if current_user.role.name == "admin":
            access = UserProjectAccess(
                user_id=current_user.id,
                Ranproject_id=None,
                project_id=None,
                Ropproject_id=new_project.pid_po,
                permission_level="all"
            )
            db.add(access)
        db.commit()
        db.refresh(new_project)
        return new_project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating ROP project: {str(e)}"
        )


@ROPProjectrouter.get("/", response_model=List[ROPProjectOut])
def get_all_projects(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all ROP projects accessible to the current user.
    - senior_admin: Can see all projects
    - admin: Can see only projects they have access to
    - user: Can see only projects they have access to
    """
    try:
        accessible_projects = get_user_accessible_rop_projects(current_user, db)
        return accessible_projects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ROP projects: {str(e)}"
        )


@ROPProjectrouter.get("/{pid_po}", response_model=ROPProjectOut)
def get_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific ROP project by pid_po.
    Users can only access projects they have permission for.
    """
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="ROP Project not found")

    # Check if user has access to this project
    if not check_rop_project_access(current_user, project, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this ROP project. Contact the Senior Admin."
        )

    return project


@ROPProjectrouter.put("/{pid_po}", response_model=ROPProjectOut)
def update_project(
        pid_po: str,
        data: ROPProjectCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update a ROP project.
    - senior_admin: Can update any project
    - admin: Can update only projects they have "edit" or "all" permission for
    - user: Cannot update projects
    """
    # Users cannot update projects
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to update ROP projects. Contact the Senior Admin."
        )

    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="ROP Project not found")

    # Check if user has edit permission
    if not check_rop_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this ROP project. Contact the Senior Admin."
        )

    if data.pid != project.pid or data.po != project.po:
        raise HTTPException(status_code=400, detail="Cannot change pid or po after creation")

    try:
        for key, value in data.dict(exclude={"pid", "po"}).items():
            setattr(project, key, value)
        db.commit()
        db.refresh(project)
        return project
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating ROP project: {str(e)}"
        )


@ROPProjectrouter.delete("/{pid_po}")
def delete_project(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):


    """
    Delete a ROP project.
    - senior_admin: Can delete any project
    - admin: Can delete only projects they have "all" permission for
    - user: Cannot delete projects
    """
    # Users cannot delete projects
    if current_user.role.name == "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users are not authorized to delete ROP projects. Contact the Senior Admin."
        )

    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="ROP Project not found")

    # Check if user has "all" permission (required for deletion)
    if not check_rop_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this ROP project. Contact the Senior Admin."
        )

    try:
        # 1) Delete association table rows for packages of this project
        pkg_ids_subq = db.query(RopPackage.id).filter(RopPackage.project_id == pid_po).subquery()
        db.execute(rop_package_lvl1.delete().where(rop_package_lvl1.c.package_id.in_(pkg_ids_subq)))
        db.commit()

        # 2) Delete monthly distributions for packages of this project
        db.query(MonthlyDistribution).filter(MonthlyDistribution.package_id.in_(pkg_ids_subq)).delete(synchronize_session=False)
        db.commit()

        # 3) Delete Level 2 distributions via subquery of lvl2 ids
        lvl2_ids_subq = db.query(ROPLvl2.id).filter(ROPLvl2.project_id == pid_po).subquery()
        db.query(ROPLvl2Distribution).filter(ROPLvl2Distribution.lvl2_id.in_(lvl2_ids_subq)).delete(synchronize_session=False)
        db.commit()

        # 4) Delete Level 2 rows
        db.query(ROPLvl2).filter(ROPLvl2.project_id == pid_po).delete(synchronize_session=False)
        db.commit()

        # 5) Delete packages
        db.query(RopPackage).filter(RopPackage.project_id == pid_po).delete(synchronize_session=False)
        db.commit()

        # 6) Delete Level 1 rows
        db.query(ROPLvl1).filter(ROPLvl1.project_id == pid_po).delete(synchronize_session=False)
        db.commit()

        # 7) Remove user access mappings to this project
        db.query(UserProjectAccess).filter(
            UserProjectAccess.Ropproject_id == pid_po
        ).delete(synchronize_session=False)
        db.commit()

        # 8) Finally delete the project
        db.delete(project)
        db.commit()

        return {"detail": "Project and related data deleted successfully"}

    except Exception as e:

        db.rollback()
        print("Commit failed:", type(e), e)
        raise


@ROPProjectrouter.get("/check-permission/{pid_po}")
def check_user_rop_project_permission(
        pid_po: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Check what permissions the current user has for a specific ROP project.
    Returns the permission level and available actions.
    """

    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="ROP Project not found")

    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return {
            "project_id": pid_po,
            "permission_level": "all",
            "can_view": True,
            "can_edit": True,
            "can_delete": True,
            "role": "senior_admin"
        }

    # Check access for other users
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ropproject_id == project.pid_po
    ).first()

    if not access:
        return {
            "project_id": pid_po,
            "permission_level": "none",
            "can_view": False,
            "can_edit": False,
            "can_delete": False,
            "role": current_user.role.name
        }

    # Determine capabilities based on permission level and role
    can_edit = (current_user.role.name == "admin" and
                access.permission_level in ["edit", "all"])
    can_delete = (current_user.role.name == "admin" and
                  access.permission_level == "all")

    return {
        "project_id": pid_po,
        "permission_level": access.permission_level,
        "can_view": True,
        "can_edit": can_edit,
        "can_delete": can_delete,
        "role": current_user.role.name
    }


# --------------------------------------------------------------------------------
# Helper Functions (unchanged)
# --------------------------------------------------------------------------------

def generate_distributions(start_date_str, end_date_str, total_quantity):
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

    # Generate all months
    months = []
    current = start_date
    while current <= end_date:
        months.append((current.year, current.month))
        current += relativedelta(months=1)

    n_months = len(months)

    # Base allocation
    base = total_quantity // n_months
    remainder = total_quantity % n_months

    distributions = []
    for idx, (year, month) in enumerate(months):
        allocated = base + (1 if idx < remainder else 0)
        distributions.append(
            ROPLvl2DistributionCreate(
                year=year,
                month=month,
                allocated_quantity=allocated
            )
        )

    return distributions


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# --------------------------------------------------------------------------------
# CSV Upload Endpoints (with access control)
# --------------------------------------------------------------------------------

@ROPProjectrouter.post("/upload-csv")
async def upload_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload CSV file to create ROP project hierarchy.
    Only senior_admin can upload CSV files.
    """
    # Only senior_admin can upload CSV files
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files. Contact the Senior Admin."
        )

    try:
        content = await file.read()
        decoded = content.decode("utf-8")
        csv_reader = csv.reader(io.StringIO(decoded))

        rows = list(csv_reader)

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty.")

        has_level0 = any(
            safe_int(row[0]) == 0  # level is at index 0
            for row in rows[:5]
        )
        if not has_level0:
            raise HTTPException(
                status_code=400,
                detail="CSV must contain at least one Level 0 entry within the first 5 rows."
            )

        project_id = None
        project_name = None
        project_currency = None

        for row in rows:
            try:
                level = int(row[0])  # level is column 0
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid level value: {row[0]}")

            if level == 0:
                project_id = row[1] + row[5] + str(current_user.id) # id + customer material number
                project_name = row[4]  # Product Description
                rop_project_data = ROPProjectCreate(
                    pid=row[1],  # id
                    po=row[5],  # customer material number
                    project_name=project_name,
                    wbs=row[1],
                    country=None,
                    product_number=row[3],  # Product Number
                )
                create_project(rop_project_data, db=db, current_user=current_user)
                print(f"Creating ROPProject: {rop_project_data.dict()}")

            elif level == 1:
                rop_lvl1_data = ROPLvl1Create(
                    id=row[1] + project_id,  # id
                    project_id=project_id,
                    project_name=project_name,
                    product_number=row[3],
                    item_name=row[4],  # Product Description
                    region=None,
                    total_quantity=safe_int(row[6]),  # Target Quantity
                    price=safe_int(row[7]),  # unit price
                    start_date=None,
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date()  # end date
                )
                create_lvl1(rop_lvl1_data, db=db,current_user=current_user)

            elif level == 2:
                distributions = generate_distributions(
                    row[9],  # start date
                    row[10],  # end date
                    safe_int(row[6])  # Target Quantity
                )
                if project_currency == None:
                    project_currency = row[8]
                    project = get_project(project_id, db=db, current_user=current_user)
                    project.currency = project_currency

                lvl2_data = ROPLvl2Create(
                    project_id=project_id,
                    id=row[1] + project_id,  # id
                    lvl1_id=row[2] + project_id,  # parent id
                    lvl1_item_name="...",  # if available
                    item_name=row[4],  # Product Description
                    product_number=row[3],
                    region="...",  # placeholder
                    total_quantity=safe_int(row[6]),
                    price=float(row[7]),
                    start_date=datetime.strptime(row[9], "%d.%m.%Y").date(),
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date(),
                    distributions=distributions
                )
                create_lvl2(lvl2_data, db=db,current_user=current_user)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown level: {level}")

        return {"message": "CSV processed successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"CSV upload failed: {str(e)}")


@ROPProjectrouter.post("/upload-csv-fix")
async def upload_csv_fix(
        pid: str = Form(...),
        po: str = Form(...),
        project_name: str = Form(...),
        product_number: str = Form(None),
        wbs: str = Form(None),
        country: str = Form(None),
        currency: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Called when CSV upload failed due to missing Level 0
    and FE provided corrected project data.
    Only senior_admin can upload CSV files.
    """
    # Only senior_admin can upload CSV files
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload CSV files. Contact the Senior Admin."
        )

    project_id = pid + po +str(current_user.id)

    # Step 0: Build the project model manually
    project = ROPProjectCreate(
        pid=pid,
        po=po,
        project_name=project_name,
        product_number=product_number,
        wbs=wbs,
        country=country,
        currency=currency
    )

    try:
        create_project(project, db=db, current_user=current_user)

        content = await file.read()
        decoded = content.decode("utf-8")
        csv_reader = csv.reader(io.StringIO(decoded))
        rows = list(csv_reader)

        # Step 3: Process CSV
        for row in rows:
            try:
                level = int(row[0])  # level is column 0
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid level value: {row[0]}")

            if level == 1:
                rop_lvl1_data = ROPLvl1Create(
                    id=row[1] + project_id,  # id
                    project_id=project_id,
                    project_name=project_name,
                    product_number=row[3],
                    item_name=row[4],  # Product Description
                    region=None,
                    total_quantity=safe_int(row[6]),  # Target Quantity
                    price=safe_int(row[7]),  # unit price
                    start_date=None,
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date()  # end date
                )
                create_lvl1(rop_lvl1_data, db=db,current_user=current_user)

            elif level == 2:
                distributions = generate_distributions(
                    row[9],  # start date
                    row[10],  # end date
                    safe_int(row[6])  # Target Quantity
                )

                lvl2_data = ROPLvl2Create(
                    project_id=project_id,
                    id=row[1] + project_id,  # id
                    lvl1_id=row[2] + project_id,  # parent id
                    lvl1_item_name="...",  # if available
                    item_name=row[4],  # Product Description
                    product_number=row[3],
                    region="...",  # placeholder
                    total_quantity=safe_int(row[6]),
                    price=float(row[7]),
                    start_date=datetime.strptime(row[9], "%d.%m.%Y").date(),
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date(),
                    distributions=distributions
                )
                create_lvl2(lvl2_data, db=db,current_user=current_user)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown level: {level}")

        return {"message": "CSV processed successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"CSV fix failed: {str(e)}")