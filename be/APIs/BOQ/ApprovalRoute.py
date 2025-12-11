"""
Approval Workflow API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
from pathlib import Path
from datetime import datetime
import logging

from Schemas.BOQ.ApprovalSchema import (
    ApprovalResponse,
    ApprovalListResponse,
    ApprovalReject
)
from APIs.Core import get_current_user, get_db
from Models.Admin.User import User
from Models.BOQ.Approval import Approval

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["Approvals"])

UPLOAD_DIR = Path("uploads/approvals")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ApprovalResponse)
async def upload_approval(
    csv_file: UploadFile = File(..., description="PAC CSV data file"),
    template_file: UploadFile = File(..., description="PAC Word template file"),
    project_id: str = Form(...),
    project_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload PAC files (CSV + Word template) for approval workflow"""
    if project_type not in ["Zain MW BOQ", "Zain Ran BOQ"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_type must be 'Zain MW BOQ' or 'Zain Ran BOQ'"
        )

    # Validate CSV file
    csv_ext = Path(csv_file.filename).suffix.lower()
    if csv_ext != '.csv':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PAC data file must be a CSV file (.csv)"
        )

    # Validate Word template file
    template_ext = Path(template_file.filename).suffix.lower()
    if template_ext not in ['.doc', '.docx']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PAC template must be a Word file (.doc or .docx)"
        )

    try:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

        # Save CSV file
        safe_csv_filename = f"{timestamp}_{csv_file.filename}"
        csv_file_path = UPLOAD_DIR / safe_csv_filename
        with open(csv_file_path, "wb") as buffer:
            shutil.copyfileobj(csv_file.file, buffer)

        # Save template file
        safe_template_filename = f"{timestamp}_{template_file.filename}"
        template_file_path = UPLOAD_DIR / safe_template_filename
        with open(template_file_path, "wb") as buffer:
            shutil.copyfileobj(template_file.file, buffer)

        approval = Approval(
            filename=csv_file.filename,
            file_path=str(csv_file_path),
            template_filename=template_file.filename,
            template_file_path=str(template_file_path),
            project_id=project_id,
            project_type=project_type,
            stage='approval',
            status='pending_approval',
            uploaded_by=current_user.id
        )

        db.add(approval)
        db.commit()
        db.refresh(approval)

        logger.info(f"Approval {approval.id} uploaded by user {current_user.id}: CSV={csv_file.filename}, Template={template_file.filename}")

        return ApprovalResponse(
            id=approval.id,
            filename=approval.filename,
            file_path=approval.file_path,
            template_filename=approval.template_filename,
            template_file_path=approval.template_file_path,
            project_id=approval.project_id,
            project_type=approval.project_type,
            stage=approval.stage,
            status=approval.status,
            notes=approval.notes,
            uploaded_by=approval.uploaded_by,
            uploader_name=current_user.username,
            created_at=approval.created_at,
            updated_at=approval.updated_at
        )

    except Exception as e:
        logger.error(f"Approval upload error: {e}")
        # Clean up uploaded files if error occurs
        if 'csv_file_path' in locals() and csv_file_path.exists():
            csv_file_path.unlink()
        if 'template_file_path' in locals() and template_file_path.exists():
            template_file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading files: {str(e)}"
        )


@router.get("/", response_model=ApprovalListResponse)
async def list_approvals(
    stage: Optional[str] = None,
    search: Optional[str] = None,
    project_type: Optional[str] = None,
    project_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List approvals filtered by stage, search term, project type, and project"""
    query = db.query(Approval)

    if stage:
        query = query.filter(Approval.stage == stage)

    if search:
        query = query.filter(Approval.filename.contains(search))

    if project_type:
        query = query.filter(Approval.project_type == project_type)

    if project_id:
        query = query.filter(Approval.project_id == project_id)

    total = query.count()
    items = query.order_by(Approval.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    response_items = []
    for item in items:
        uploader = db.query(User).filter(User.id == item.uploaded_by).first()
        response_items.append(ApprovalResponse(
            id=item.id,
            filename=item.filename,
            file_path=item.file_path,
            template_filename=item.template_filename,
            template_file_path=item.template_file_path,
            project_id=item.project_id,
            project_type=item.project_type,
            stage=item.stage,
            status=item.status,
            notes=item.notes,
            uploaded_by=item.uploaded_by,
            uploader_name=uploader.username if uploader else None,
            created_at=item.created_at,
            updated_at=item.updated_at
        ))

    return ApprovalListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single approval by ID"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    uploader = db.query(User).filter(User.id == approval.uploaded_by).first()

    return ApprovalResponse(
        id=approval.id,
        filename=approval.filename,
        file_path=approval.file_path,
        template_filename=approval.template_filename,
        template_file_path=approval.template_file_path,
        project_id=approval.project_id,
        project_type=approval.project_type,
        stage=approval.stage,
        status=approval.status,
        notes=approval.notes,
        uploaded_by=approval.uploaded_by,
        uploader_name=uploader.username if uploader else None,
        created_at=approval.created_at,
        updated_at=approval.updated_at
    )


@router.post("/{approval_id}/approve")
async def approve_item(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve an item - moves it to next stage or completes workflow"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.stage == 'approval':
        # Move from approval to triggering stage
        approval.stage = 'triggering'
        approval.status = 'pending_triggering'
        approval.notes = None  # Clear any previous rejection notes
        db.commit()
        logger.info(f"Approval {approval_id} moved to triggering stage by user {current_user.id}")
        return {"message": "Moved to triggering stage", "stage": "triggering"}

    elif approval.stage == 'triggering':
        # Final approval - workflow complete
        approval.status = 'approved'
        db.commit()
        logger.info(f"Approval {approval_id} fully approved by user {current_user.id}")
        return {"message": "Workflow completed - fully approved", "stage": "completed"}

    return {"message": "No action taken"}


@router.post("/{approval_id}/reject")
async def reject_item(
    approval_id: int,
    rejection: ApprovalReject,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject an item - in triggering stage, sends back to approval with notes"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.stage == 'triggering':
        # Send back to approval stage with notes
        approval.stage = 'approval'
        approval.status = 'rejected'
        approval.notes = rejection.notes
        db.commit()
        logger.info(f"Approval {approval_id} rejected by triggering team, sent back to approval by user {current_user.id}")
        return {"message": "Sent back to approval stage", "stage": "approval"}

    elif approval.stage == 'approval':
        # Reject at approval stage
        approval.status = 'rejected'
        approval.notes = rejection.notes
        db.commit()
        logger.info(f"Approval {approval_id} rejected at approval stage by user {current_user.id}")
        return {"message": "Rejected at approval stage", "stage": "approval"}

    return {"message": "No action taken"}


@router.delete("/{approval_id}")
async def delete_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an approval and its file"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    try:
        # Delete CSV file
        csv_file_path = Path(approval.file_path)
        if csv_file_path.exists():
            csv_file_path.unlink()

        # Delete template file
        template_file_path = Path(approval.template_file_path)
        if template_file_path.exists():
            template_file_path.unlink()

        db.delete(approval)
        db.commit()

        logger.info(f"Approval {approval_id} deleted by user {current_user.id}")

        return {"success": True, "message": f"Approval '{approval.filename}' deleted"}

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting approval {approval_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting approval: {str(e)}"
        )


@router.get("/download/{approval_id}")
async def download_approval_file(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download CSV file"""
    from fastapi.responses import FileResponse

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    file_path = Path(approval.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=approval.filename,
        media_type='text/csv'
    )


@router.get("/download-template/{approval_id}")
async def download_approval_template(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download Word template file"""
    from fastapi.responses import FileResponse

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    template_path = Path(approval.template_file_path)
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found")

    # Determine media type based on file extension
    media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    if approval.template_filename.endswith('.doc'):
        media_type = 'application/msword'

    return FileResponse(
        path=str(template_path),
        filename=approval.template_filename,
        media_type=media_type
    )


@router.get("/projects/{project_type}")
async def get_projects_by_type(
    project_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get projects list based on project type (MW or RAN)"""
    from Models.BOQ.Project import Project
    from Models.RAN.RANProject import RanProject

    if project_type == "Zain MW BOQ":
        projects = db.query(Project.pid_po, Project.project_name).all()
        return [{"id": p.pid_po, "name": p.project_name} for p in projects]
    elif project_type == "Zain Ran BOQ":
        projects = db.query(RanProject.pid_po, RanProject.project_name).all()
        return [{"id": p.pid_po, "name": p.project_name} for p in projects]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_type. Must be 'Zain MW BOQ' or 'Zain Ran BOQ'"
        )
