from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert, delete, select
from typing import List

from APIs.Core import get_db
from Models.RopPackages import RopPackage, rop_package_lvl1
from Models.ROPLvl1 import ROPLvl1
from Schemas.RopPackageSchema import RopPackageCreate, RopPackageUpdate, RopPackageOut

RopPackageRouter = APIRouter(prefix="/rop-package", tags=["Rop Packages"])


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
    db.add(new_pkg)
    db.commit()
    db.refresh(new_pkg)

    # Insert lvl1 links with quantities
    for item in data.lvl1_ids:   # item = {"id": "...", "quantity": ...}
        db.execute(
            insert(rop_package_lvl1).values(
                package_id=new_pkg.id,
                lvl1_id=item["id"],
                quantity=item.get("quantity", None)
            )
        )
    db.commit()

    # Fetch linked items with quantities
    rows = db.execute(
        select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
        .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
        .where(rop_package_lvl1.c.package_id == new_pkg.id)
    ).all()

    return RopPackageOut(
        id=new_pkg.id,
        project_id=new_pkg.project_id,
        package_name=new_pkg.package_name,
        start_date=new_pkg.start_date,
        end_date=new_pkg.end_date,
        quantity=new_pkg.quantity,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
    )


# READ ALL
@RopPackageRouter.get("/", response_model=List[RopPackageOut])
def get_all_packages(db: Session = Depends(get_db)):
    pkgs = db.query(RopPackage).all()
    result = []
    for pkg in pkgs:
        rows = db.execute(
            select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
            .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
            .where(rop_package_lvl1.c.package_id == pkg.id)
        ).all()
        result.append(RopPackageOut(
            id=pkg.id,
            project_id=pkg.project_id,
            package_name=pkg.package_name,
            start_date=pkg.start_date,
            end_date=pkg.end_date,
            quantity=pkg.quantity,
            lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
        ))
    return result


# READ ONE
@RopPackageRouter.get("/{id}", response_model=RopPackageOut)
def get_package(id: int, db: Session = Depends(get_db)):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    rows = db.execute(
        select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
        .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
        .where(rop_package_lvl1.c.package_id == pkg.id)
    ).all()

    return RopPackageOut(
        id=pkg.id,
        project_id=pkg.project_id,
        package_name=pkg.package_name,
        start_date=pkg.start_date,
        end_date=pkg.end_date,
        quantity=pkg.quantity,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
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
    if data.quantity is not None:
        pkg.quantity = data.quantity

    # Replace lvl1 links if provided
    if data.lvl1_ids is not None:
        db.execute(delete(rop_package_lvl1).where(rop_package_lvl1.c.package_id == id))
        for item in data.lvl1_ids:
            db.execute(
                insert(rop_package_lvl1).values(
                    package_id=id,
                    lvl1_id=item["id"],
                    quantity=item.get("quantity", None)
                )
            )

    db.commit()
    db.refresh(pkg)

    rows = db.execute(
        select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
        .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
        .where(rop_package_lvl1.c.package_id == id)
    ).all()

    return RopPackageOut(
        id=pkg.id,
        project_id=pkg.project_id,
        package_name=pkg.package_name,
        start_date=pkg.start_date,
        end_date=pkg.end_date,
        quantity=pkg.quantity,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in rows]
    )


# DELETE
@RopPackageRouter.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(id: int, db: Session = Depends(get_db)):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    db.delete(pkg)
    db.commit()
