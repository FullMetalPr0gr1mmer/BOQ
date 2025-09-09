import csv
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File,Form
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from APIs.LE.ROPLvl1Route import create_lvl1
from APIs.LE.ROPLvl2Route import create_lvl2
from Models.LE.ROPProject import ROPProject
from Schemas.LE.ROPLvl1Schema import ROPLvl1Create
from Schemas.LE.ROPLvl2Schema import ROPLvl2DistributionCreate, ROPLvl2Create
from Schemas.LE.ROPProjectSchema import ROPProjectCreate, ROPProjectOut

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
    try:
        content = await file.read()
        decoded = content.decode("utf-8")
        csv_reader = csv.reader(io.StringIO(decoded))

        rows = list(csv_reader)

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty.")

        # Validate that all rows have exactly 11 columns
        # expected_columns = 11
        # for i, row in enumerate(rows, start=1):
        #     if len(row) != expected_columns:
        #         raise HTTPException(
        #             status_code=400,
        #             detail=f"Row {i} has {len(row)} columns, expected {expected_columns}. "
        #                    f"Row content: {row}"
        #         )

        # Check if there's a level 0 in the first 5 rows
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
        project_currency=None
        level1_id= None
        for row in rows:
            try:
                level = int(row[0])  # level is column 0
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid level value: {row[0]}")

            if level == 0:
                project_id = row[1] + row[5]  # id + customer material number
                project_name = row[4]         # Product Description
                rop_project_data = ROPProjectCreate(
                    pid=row[1],  # id
                    po=row[5],   # customer material number
                    project_name=project_name,
                    wbs=row[1],
                    country=None,
                    product_number=row[3],  # Product Number
                    pid_po=project_id
                )
                create_project(rop_project_data, db=db)
                print(f"Creating ROPProject: {rop_project_data.dict()}")

            elif level == 1:
                rop_lvl1_data = ROPLvl1Create(
                    id=row[1]+project_id,  # id
                    project_id=project_id,
                    project_name=project_name,
                    product_number=row[3],
                    item_name=row[4],  # Product Description
                    region=None,
                    total_quantity=safe_int(row[6]),  # Target Quantity
                    price=safe_int(row[7]),           # unit price
                    start_date=None,
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date()  # end date
                )
                create_lvl1(rop_lvl1_data, db=db)

            elif level == 2:
                distributions = generate_distributions(
                    row[9],   # start date
                    row[10],  # end date
                    safe_int(row[6])  # Target Quantity
                )
                if project_currency==None:
                    project_currency = row[8]
                    project = get_project(project_id, db=db)
                    project.currency = project_currency

                lvl2_data = ROPLvl2Create(
                    project_id=project_id,
                    id=row[1]+project_id,   # id
                    lvl1_id=row[2]+project_id,        # parent id
                    lvl1_item_name="...",  # if available
                    item_name=row[4],      # Product Description
                    product_number=row[3],
                    region="...",          # placeholder
                    total_quantity=safe_int(row[6]),
                    price=float(row[7]),
                    start_date=datetime.strptime(row[9], "%d.%m.%Y").date(),
                    end_date=datetime.strptime(row[10], "%d.%m.%Y").date(),
                    distributions=distributions
                )
                create_lvl2(lvl2_data, db=db)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown level: {level}")

        return {"message": "CSV processed successfully (simulation mode for now)"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    db: Session = Depends(get_db)
):
    project_id = pid+po
    project_name = project_name
    """
    Called when CSV upload failed due to missing Level 0
    and FE provided corrected project data.
    """
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
    create_project(project,db=db)

    try:

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
                create_lvl1(rop_lvl1_data, db=db)

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
                create_lvl2(lvl2_data, db=db)

            else:
                raise HTTPException(status_code=400, detail=f"Unknown level: {level}")

        return {"message": "CSV processed successfully (simulation mode for now)"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV fix failed: {str(e)}")
