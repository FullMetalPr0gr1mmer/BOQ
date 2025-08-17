import csv
import io
from io import StringIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from APIs.ROPLvl1Route import create_lvl1
from APIs.ROPLvl2Route import create_lvl2
from Models.ROPProject import ROPProject
from Schemas.ROPLvl1Schema import ROPLvl1Create
from Schemas.ROPLvl2Schema import ROPLvl2DistributionCreate, ROPLvl2Create
from Schemas.ROPProjectSchema import ROPProjectCreate, ROPProjectOut

ROPProjectrouter = APIRouter(prefix="/rop-projects", tags=["ROP Projects"])


# CREATE
@ROPProjectrouter.post("/", response_model=ROPProjectOut)
def create_project(project: ROPProjectCreate, db: Session = Depends(get_db)):
    pid_po = project.pid + project.po
    existing = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this pid_po already exists")

    new_project = ROPProject(**project.dict())
    new_project.pid_po = pid_po
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


# READ ALL
@ROPProjectrouter.get("/", response_model=List[ROPProjectOut])
def get_all_projects(db: Session = Depends(get_db)):
    return db.query(ROPProject).all()


# READ ONE
@ROPProjectrouter.get("/{pid_po}", response_model=ROPProjectOut)
def get_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# UPDATE
@ROPProjectrouter.put("/{pid_po}", response_model=ROPProjectOut)
def update_project(pid_po: str, data: ROPProjectCreate, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.pid != project.pid or data.po != project.po:
        raise HTTPException(status_code=400, detail="Cannot change pid or po after creation")

    for key, value in data.dict(exclude={"pid", "po"}).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


# DELETE
@ROPProjectrouter.delete("/{pid_po}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()



    ##############################################################################33
    ############################################################################

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

@ROPProjectrouter.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    expected_headers = [
        "level", "id", "parent id", "Product Number", "Product Description",
        "customer material number", "Target Quantity", "unit price", "currency",
        "start date", "end date"
    ]

    try:
        content = await file.read()
        decoded = content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded))

        # Validate headers
        if csv_reader.fieldnames != expected_headers:
            raise HTTPException(
                status_code=400,
                detail=f"CSV headers do not match expected format. Expected: {expected_headers}, Got: {csv_reader.fieldnames}"
            )
        project_id = None
        for row in csv_reader:
            try:
                level = int(row["level"])
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid level value: {row['level']}")

            if level == 0:
                project_id=row["id"]+row["customer material number"]
                project_name=row["Product Description"]
                rop_project_data = ROPProjectCreate(
                    pid=row["id"],
                    po=row["customer material number"],
                    project_name=project_name,
                    wbs=row["id"],
                    country=None,
                    product_number=row["Product Number"],
                    # currency defaults to Euros
                    pid_po=project_id
                )
                create_project(rop_project_data,db=db)
                print(f"Creating ROPProject: {rop_project_data.dict()}")

            elif level == 1:
                rop_lvl1_data=ROPLvl1Create(
                    id=safe_int(row["id"]),
                    project_id=project_id,
                    project_name=project_name,
                    product_number=row["Product Number"],
                    item_name=row["Product Description"],
                    region=None, ####TO BE ADDED LATER
                    total_quantity=safe_int(row["Target Quantity"]),
                    price=safe_int(row["unit price"]),
                    start_date= None,###WE NEED TO ASK BOUT THIS
                    end_date=datetime.strptime(row["end date"], "%d.%m.%Y").date()
                )
                create_lvl1(rop_lvl1_data,db=db)
            elif level == 2:
                distributions = generate_distributions(
                    row["start date"],
                    row["end date"],
                    safe_int(row["Target Quantity"])
                )

                lvl2_data = ROPLvl2Create(
                    project_id=project_id,  # pid_po
                    id=safe_int(row["id"]),
                    lvl1_id=row["parent id"],
                    lvl1_item_name="...",  # if available in CSV
                    item_name=row["Product Description"],
                    product_number=row["Product Number"],
                    region="...",  # depends if given in CSV
                    total_quantity=safe_int(row["Target Quantity"]),
                    price=float(row["unit price"]),
                    start_date=datetime.strptime(row["start date"], "%d.%m.%Y").date(),
                    end_date=datetime.strptime(row["end date"], "%d.%m.%Y").date(),
                    distributions=distributions
                )

                create_lvl2(lvl2_data,db=db)


            else:
                raise HTTPException(status_code=400, detail=f"Unknown level: {level}")

        return {"message": "CSV processed successfully (simulation mode for now)"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


