from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from APIs.Core import get_db, get_current_user
from APIs.LE.ROPLvl1Route import get_lvl1_by_id
from Models.LE.ROPLvl2 import ROPLvl2, ROPLvl2Distribution
from Models.Admin.User import User, UserProjectAccess
from Schemas.LE.ROPLvl2Schema import ROPLvl2Create, ROPLvl2Out


ROPLvl2router = APIRouter(prefix="/rop-lvl2", tags=["ROP Lvl2"])


# ----------------------------
# Helpers
# ----------------------------
def check_project_access(current_user: User, pid_po: str, db: Session, required_permission: str = "view"):
    if current_user.role.name == "senior_admin":
        return True
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == pid_po
    ).first()
    if not access:
        return False
    hierarchy = {"view": ["view", "edit", "all"], "edit": ["edit", "all"], "all": ["all"]}
    return access.permission_level in hierarchy.get(required_permission, [])


# ----------------------------
# CRUD with admin controls
# ----------------------------
@ROPLvl2router.post("/create", response_model=ROPLvl2Out)
def create_lvl2(data: ROPLvl2Create, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.name != "senior_admin" and current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Only senior admins can create Lvl1")

    new_lvl2 = ROPLvl2(**data.dict(exclude={"distributions"}))
    db.add(new_lvl2)
    db.commit()
    db.refresh(new_lvl2)

    for dist in data.distributions:
        db.add(ROPLvl2Distribution(
            lvl2_id=new_lvl2.id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        ))
    db.commit()
    db.refresh(new_lvl2)

    roplvl1_data = get_lvl1_by_id(new_lvl2.lvl1_id, db=db, current_user=current_user)
    roplvl1_data.price = (roplvl1_data.price + ((new_lvl2.price * new_lvl2.total_quantity) / roplvl1_data.total_quantity))
    db.commit()
    return new_lvl2


@ROPLvl2router.get("/", response_model=List[ROPLvl2Out])
def get_all_lvl2(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.name == "senior_admin":
        return db.query(ROPLvl2).all()
    accesses = db.query(UserProjectAccess).filter(UserProjectAccess.user_id == current_user.id).all()
    if not accesses:
        return []
    project_ids = [a.project_id for a in accesses]
    return db.query(ROPLvl2).filter(ROPLvl2.project_id.in_(project_ids)).all()


@ROPLvl2router.get("/by-lvl1/{lvl1_id}", response_model=List[ROPLvl2Out])
def get_lvl2_by_lvl1(lvl1_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl1 = get_lvl1_by_id(lvl1_id, db=db, current_user=current_user)
    if not check_project_access(current_user, lvl1.project_id, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view Lvl2 for this Lvl1")
    return db.query(ROPLvl2).filter(ROPLvl2.lvl1_id == lvl1_id).all()


@ROPLvl2router.get("/{id}", response_model=ROPLvl2Out)
def get_lvl2_by_id(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "view"):
        raise HTTPException(status_code=403, detail="Not authorized to view this Lvl2")
    return lvl2


@ROPLvl2router.put("/update/{id}", response_model=ROPLvl2Out)
def update_lvl2(id: str, data: ROPLvl2Create, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "edit"):
        raise HTTPException(status_code=403, detail="Not authorized to update this Lvl2")

    for key, value in data.dict(exclude={"distributions"}).items():
        setattr(lvl2, key, value)

    db.query(ROPLvl2Distribution).filter(ROPLvl2Distribution.lvl2_id == id).delete()
    for dist in data.distributions:
        db.add(ROPLvl2Distribution(
            lvl2_id=id,
            month=dist.month,
            year=dist.year,
            allocated_quantity=dist.allocated_quantity
        ))

    db.commit()
    db.refresh(lvl2)
    return lvl2


@ROPLvl2router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lvl2(id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    lvl2 = db.query(ROPLvl2).filter(ROPLvl2.id == id).first()
    if not lvl2:
        raise HTTPException(status_code=404, detail="Lvl2 entry not found")
    if not check_project_access(current_user, lvl2.project_id, db, "all"):
        raise HTTPException(status_code=403, detail="Not authorized to delete this Lvl2")

    db.delete(lvl2)
    db.commit()
