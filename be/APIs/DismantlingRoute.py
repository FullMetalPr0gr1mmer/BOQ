from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from io import StringIO
import csv

from APIs.Core import get_db
from Models.Dismantling import Dismantling
from Schemas.DismantlingSchema import DismantlingCreate, DismantlingUpdate, DismantlingOut, DismantlingPagination

DismantlingRouter = APIRouter(prefix="/dismantling", tags=["Dismantling"])

# ---------- CRUD with Routers ----------

# This is the correct endpoint for pagination.
@DismantlingRouter.get("/", response_model=DismantlingPagination)
def get_all(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retrieves a paginated and searchable list of dismantling records.
    """
    query = db.query(Dismantling)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Dismantling.nokia_link_id.like(search_pattern),
                Dismantling.nec_dismantling_link_id.like(search_pattern),
                Dismantling.comments.like(search_pattern),
            )
        )

    # Count the total number of records *before* applying the offset/limit
    total_count = query.count()

    # Get the paginated records
    records = (
        query.order_by(Dismantling.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Return the records and the total count in a single object
    return {"records": records, "total": total_count}


# The other endpoints (get_by_id, update, delete, upload) are correct as they are.
# Just make sure they are in the same file.
@DismantlingRouter.get("/{id}", response_model=DismantlingOut)
def get_by_id(id: int, db: Session = Depends(get_db)):
    obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Record not found")
    return obj


@DismantlingRouter.put("/{id}", response_model=DismantlingOut)
def update_dismantling(id: int, obj_in: DismantlingUpdate, db: Session = Depends(get_db)):
    db_obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    for field, value in obj_in.dict(exclude_unset=True).items():
        setattr(db_obj, field, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@DismantlingRouter.delete("/{id}")
def delete_dismantling(id: int, db: Session = Depends(get_db)):
    db_obj = db.query(Dismantling).filter(Dismantling.id == id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(db_obj)
    db.commit()
    return {"deleted_id": id}


# ---------- CSV Upload ----------
@DismantlingRouter.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    csv_reader = csv.reader(StringIO(content.decode("utf-8")))

    # skip header row
    next(csv_reader, None)

    inserted_count = 0
    for row in csv_reader:
        if len(row) < 4:
            continue

        try:
            no_of_dismantling = int(row[2].strip())
        except (ValueError, IndexError):
            continue

        obj_in = DismantlingCreate(
            nokia_link_id=row[0].strip() if len(row) > 0 else None,
            nec_dismantling_link_id=row[1].strip() if len(row) > 1 else None,
            no_of_dismantling=no_of_dismantling,
            comments=row[3].strip() if len(row) > 3 else None,
        )
        db_obj = Dismantling(**obj_in.dict())
        db.add(db_obj)
        inserted_count += 1

    db.commit()
    return {"inserted": inserted_count}