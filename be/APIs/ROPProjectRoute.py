from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from APIs.Core import get_db
from Models.ROPProject import ROPProject
from Schemas.ROPProjectSchema import ROPProjectCreate, ROPProjectOut

ROPProjectrouter = APIRouter(prefix="/rop-projects", tags=["ROP Projects"])


# Create a new ROP Project
@ROPProjectrouter.post("/", response_model=ROPProjectOut)
def create_rop_project(project: ROPProjectCreate, db: Session = Depends(get_db)):
    pid_po=project.pid+project.po
    db_project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if db_project:
        raise HTTPException(status_code=400, detail="Project with this pid_po already exists")

    new_project = ROPProject(**project.dict())
    new_project.pid_po = pid_po
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


# Get all ROP Projects
@ROPProjectrouter.get("/", response_model=List[ROPProjectOut])
def get_all_rop_projects(db: Session = Depends(get_db)):
    return db.query(ROPProject).all()


# Get a single ROP Project by pid_po
@ROPProjectrouter.get("/{pid_po}", response_model=ROPProjectOut)
def get_rop_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# Update a ROP Project
@ROPProjectrouter.put("/{pid_po}", response_model=ROPProjectOut)
def update_rop_project(pid_po: str, updated_data: ROPProjectCreate, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Prevent pid or po change to keep pid_po consistent
    if updated_data.pid != project.pid or updated_data.po != project.po:
        raise HTTPException(status_code=400, detail="Cannot change pid or po after creation")

    for key, value in updated_data.dict(exclude={"pid", "po"}).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project



# Delete a ROP Project
@ROPProjectrouter.delete("/{pid_po}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rop_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(ROPProject).filter(ROPProject.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
