# routes/projectRoute.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from APIs.Core import get_db
from Models.BOQ.Project import Project
from Schemas.BOQ.ProjectSchema import CreateProject, UpdateProject

projectRoute = APIRouter(tags=["Projects"])


@projectRoute.post("/create_project", response_model=CreateProject)
def add_project(project_data: CreateProject, db: Session = Depends(get_db)):
    pid_po = project_data.pid + project_data.po
    existing_project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project already exists")

    new_project_db = Project(
        pid_po=pid_po,
        project_name=project_data.project_name,
        pid=project_data.pid,
        po=project_data.po
    )
    db.add(new_project_db)
    db.commit()
    db.refresh(new_project_db)
    return new_project_db


@projectRoute.get("/get_project")
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()


@projectRoute.get("/get_project/{pid_po}")
def get_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@projectRoute.put("/update_project/{pid_po}")
def update_project(pid_po: str, update_data: UpdateProject, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.project_name = update_data.project_name
    db.commit()
    db.refresh(project)
    return project


@projectRoute.delete("/delete_project/{pid_po}")
def delete_project(pid_po: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": f"Project '{pid_po}' deleted successfully"}
