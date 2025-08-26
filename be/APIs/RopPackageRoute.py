# APIs/RopPackageRoute.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from Models.RopPackages import RopPackage, rop_package_lvl1
from Models.ROPLvl1 import ROPLvl1
from Schemas.RopPackageSchema import RopPackageCreate, RopPackageUpdate, RopPackageOut

RopPackageRouter = APIRouter(prefix="/rop-packages", tags=["Rop Packages"])

# CREATE
@RopPackageRouter.post("/create", response_model=RopPackageOut)
def create_package(data: RopPackageCreate, db: Session = Depends(get_db)):
    new_pkg = RopPackage(
        project_id=data.project_id,
        package_name=data.package_name,
        start_date=data.start_date,
        end_date=data.end_date,
        quantity=data.quantity,
    )

    # link Lvl1 items
    if data.lvl1_ids:
        lvl1_objs = db.query(ROPLvl1).filter(ROPLvl1.id.in_(data.lvl1_ids)).all()
        new_pkg.lvl1_items = lvl1_objs

    db.add(new_pkg)
    db.commit()
    db.refresh(new_pkg)
    return RopPackageOut(
        id=new_pkg.id,
        quantity=new_pkg.quantity,
        project_id=new_pkg.project_id,
        package_name=new_pkg.package_name,
        start_date=new_pkg.start_date,
        end_date=new_pkg.end_date,
        lvl1_items=[lvl.item_name for lvl in new_pkg.lvl1_items]
    )

# READ ALL
@RopPackageRouter.get("/", response_model=List[RopPackageOut])
def get_all_packages(db: Session = Depends(get_db)):
    pkgs = db.query(RopPackage).all()
    result = []
    for pkg in pkgs:
        result.append(RopPackageOut(
            id=pkg.id,
            project_id=pkg.project_id,
            package_name=pkg.package_name,
            start_date=pkg.start_date,
            end_date=pkg.end_date,
            lvl1_items=[lvl.item_name for lvl in pkg.lvl1_items],
            quantity=pkg.quantity
        ))
    return result

# READ ONE
@RopPackageRouter.get("/{id}", response_model=RopPackageOut)
def get_package(id: int, db: Session = Depends(get_db)):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return RopPackageOut(
        id=pkg.id,
        project_id=pkg.project_id,
        package_name=pkg.package_name,
        start_date=pkg.start_date,
        end_date=pkg.end_date,
        lvl1_items=[lvl.item_name for lvl in pkg.lvl1_items],
        quantity=pkg.quantity
    )

# UPDATE
@RopPackageRouter.put("/update/{id}", response_model=RopPackageOut)
def update_package(id: int, data: RopPackageUpdate, db: Session = Depends(get_db)):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    if data.package_name is not None:
        pkg.package_name = data.package_name
    if data.start_date is not None:
        pkg.start_date = data.start_date
    if data.end_date is not None:
        pkg.end_date = data.end_date

    if data.lvl1_ids is not None:
        lvl1_objs = db.query(ROPLvl1).filter(ROPLvl1.id.in_(data.lvl1_ids)).all()
        pkg.lvl1_items = lvl1_objs

    db.commit()
    db.refresh(pkg)
    return RopPackageOut(
        id=pkg.id,
        project_id=pkg.project_id,
        package_name=pkg.package_name,
        start_date=pkg.start_date,
        end_date=pkg.end_date,
        lvl1_items=[lvl.item_name for lvl in pkg.lvl1_items],
        quantity=pkg.quantity
    )

# DELETE
@RopPackageRouter.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(id: int, db: Session = Depends(get_db)):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    db.delete(pkg)
    db.commit()
