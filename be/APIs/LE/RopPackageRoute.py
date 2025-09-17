from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert, delete, select, and_
from typing import List

# --- Core Imports for Security and DB ---
from APIs.Core import get_db, get_current_user
from Models.Admin.User import User, UserProjectAccess
from Models.LE.ROPProject import ROPProject

# --- Model and Schema Imports ---
from Models.LE.RopPackages import RopPackage, rop_package_lvl1
from Models.LE.ROPLvl1 import ROPLvl1
from Schemas.LE.RopPackageSchema import RopPackageCreate, RopPackageUpdate, RopPackageOut

# --- Security and Logging Helper Imports ---


RopPackageRouter = APIRouter(prefix="/rop-package", tags=["Rop Packages"])
def check_rop_project_access(
        current_user: User,
        project: str,
        db: Session, required_permission: str = "view"):


    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(and_(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ropproject_id == project
    )).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_rop_projects(current_user: User, db: Session) -> List[str]:
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
        return [p.pid_po for p in db.query(ROPProject).all()]  # or p.id if project_id stores id

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.Ropproject_id for access in user_accesses]


    return accessible_project_ids


# CREATE
@RopPackageRouter.post("/create", response_model=RopPackageOut)
def create_package(
        data: RopPackageCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Permission Check: User must have 'edit' rights on the project
    if not check_rop_project_access(current_user,data.project_id, db, "edit") :
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create packages for this project."
        )

    new_pkg = RopPackage(
        project_id=data.project_id,
        package_name=data.package_name,
        start_date=data.start_date,
        end_date=data.end_date,
        quantity=data.quantity,
        price=data.price,
        lead_time=data.lead_time,
    )
    db.add(new_pkg)
    db.commit()
    db.refresh(new_pkg)

    # Insert lvl1 links
    if data.lvl1_ids:
        for item in data.lvl1_ids:
            db.execute(insert(rop_package_lvl1).values(
                package_id=new_pkg.id,
                lvl1_id=item["id"],
                quantity=item.get("quantity")
            ))
        db.commit()

    # Fetch linked items to build the response
    rows = db.execute(select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
                      .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
                      .where(rop_package_lvl1.c.package_id == new_pkg.id)).all()

    return RopPackageOut(
        **new_pkg.__dict__,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
    )


# READ ALL (Filtered by user's project access)
@RopPackageRouter.get("/", response_model=List[RopPackageOut])
def get_all_packages(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Get IDs of projects the user can access
    accessible_pids = get_user_accessible_rop_projects(current_user, db)
    if not accessible_pids:
        return []

    # 2. Query only for packages within those projects
    pkgs = db.query(RopPackage).filter(RopPackage.project_id.in_(accessible_pids)).all()

    result = []
    for pkg in pkgs:
        rows = db.execute(select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
                          .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
                          .where(rop_package_lvl1.c.package_id == pkg.id)).all()

        result.append(RopPackageOut(
            **pkg.__dict__,
            lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
        ))
    return result


# READ ONE
@RopPackageRouter.get("/{id}", response_model=RopPackageOut)
def get_package(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # 1. Permission Check: User must have 'view' rights on the package's project
    if not check_rop_project_access(pkg.project_id, current_user, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this package."
        )

    rows = db.execute(select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
                      .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
                      .where(rop_package_lvl1.c.package_id == pkg.id)).all()

    return RopPackageOut(
        **pkg.__dict__,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
    )


# UPDATE
@RopPackageRouter.put("/update/{id}", response_model=RopPackageOut)
def update_package(
        id: int,
        data: RopPackageUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # 1. Permission Check: User must have 'edit' rights on the package's project
    if not check_rop_project_access( current_user,pkg.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this package."
        )

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key != "lvl1_ids":
            setattr(pkg, key, value)

    if data.lvl1_ids is not None:
        db.execute(delete(rop_package_lvl1).where(rop_package_lvl1.c.package_id == id))
        for item in data.lvl1_ids:
            db.execute(insert(rop_package_lvl1).values(
                package_id=id, lvl1_id=item["id"], quantity=item.get("quantity")
            ))

    # 2. Logging
    db.commit()
    db.refresh(pkg)

    # Re-fetch linked items for the response
    rows = db.execute(select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
                      .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
                      .where(rop_package_lvl1.c.package_id == id)).all()

    return RopPackageOut(
        **pkg.__dict__,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
    )


# DELETE
@RopPackageRouter.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # 1. Permission Check: User must have 'all' rights on the package's project to delete
    if not check_rop_project_access(current_user,pkg.project_id,  db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this package."
        )

    db.delete(pkg)
    db.commit()