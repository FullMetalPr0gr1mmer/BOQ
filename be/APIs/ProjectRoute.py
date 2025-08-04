from fastapi import APIRouter, Depends, HTTPException

from APIs.Core import get_db
from Database.session import Session
from Models.Project import Project
from Schemas.ProjectSchema import CreateProject

projectRoute=APIRouter( tags=["Projects"])
@projectRoute.post("/create_project")
def add_project(project_data: CreateProject, db: Session = Depends(get_db)): # Renamed input for clarity
    # Check if a project with this ID already exists
    pid_po = project_data.pid+project_data.po
    existing_project = db.query(Project).filter(pid_po == Project.pid_po).first()

    # If a site was found in the DB, raise an error
    if existing_project:
        raise HTTPException(status_code=400, detail="project already exists")

    # If no project exists, create a new one using the original 'project_data'
    new_project_db = Project(pid_po=pid_po,
                             project_name=project_data.project_name,
                             pid=project_data.pid,
                             po=project_data.po)
    db.add(new_project_db)
    db.commit()
    db.refresh(new_project_db)
    return new_project_db
@projectRoute.get("/get_project")
def get_project( db: Session = Depends(get_db)):
    return db.query(Project).all()