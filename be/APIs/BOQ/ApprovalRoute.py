"""
Approval Workflow API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
import logging

from Schemas.BOQ.ApprovalSchema import (
    ApprovalResponse,
    ApprovalListResponse,
    ApprovalReject,
    ApprovalApprove,
    BulkLogisticsDownload,
    BulkApprove
)
from APIs.Core import get_current_user, get_db
from Models.Admin.User import User
from Models.Admin.AuditLog import AuditLog
from utils.file_validation import validate_csv_file, validate_document_file
from Models.BOQ.Approval import Approval

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: str = None,
    resource_name: str = None,
    details: str = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Create an audit log entry."""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")

router = APIRouter(prefix="/approvals", tags=["Approvals"])

# Use absolute path based on the backend directory location
# Go up from APIs/BOQ/ApprovalRoute.py to the be/ directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "approvals"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def resolve_file_path(file_path_str: str) -> Path:
    """
    Resolve file path, handling both absolute and relative paths.
    For backward compatibility with old relative paths stored in database.
    """
    file_path = Path(file_path_str)

    # If path doesn't exist and is relative, try making it relative to BASE_DIR
    if not file_path.exists() and not file_path.is_absolute():
        file_path = BASE_DIR / file_path_str

    return file_path


@router.post("/upload", response_model=ApprovalResponse)
async def upload_approval(
    request: Request,
    csv_file: UploadFile = File(..., description="PAC CSV data file"),
    template_file: UploadFile = File(..., description="PAC Word template file"),
    project_id: str = Form(...),
    project_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload PAC files (CSV + Word template) for approval workflow.

    OPTIMIZED: Added file size validation (50MB for CSV, 10MB for template) to prevent DoS attacks.
    """
    if project_type not in ["Zain MW BOQ", "Zain Ran BOQ"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_type must be 'Zain MW BOQ' or 'Zain Ran BOQ'"
        )

    # OPTIMIZED: Validate CSV file size and extension
    await validate_csv_file(csv_file, max_size=50 * 1024 * 1024)  # 50 MB limit

    # OPTIMIZED: Validate Word template file size and extension
    await validate_document_file(template_file, allowed_extensions=['.doc', '.docx'], max_size=10 * 1024 * 1024)  # 10 MB limit

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

        # Create audit log for upload
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="upload",
            resource_type="Approval",
            resource_id=str(approval.id),
            resource_name=approval.filename,
            details=json.dumps({
                "project_id": project_id,
                "project_type": project_type,
                "csv_file": csv_file.filename,
                "template_file": template_file.filename
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

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
            triggering_file_path=approval.triggering_file_path,
            logistics_file_path=approval.logistics_file_path,
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

    # Check stage access permissions (senior_admin bypasses checks)
    if current_user.role.name != "senior_admin":
        if stage == 'approval' and not current_user.can_access_approval:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access the approval stage"
            )
        elif stage == 'triggering' and not current_user.can_access_triggering:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access the triggering stage"
            )
        elif stage == 'logistics' and not current_user.can_access_logistics:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access the logistics stage"
            )

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

    # OPTIMIZED: Eager load uploader relationship to prevent N+1 queries
    items = query.options(joinedload(Approval.uploader)).order_by(Approval.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    response_items = []
    for item in items:
        # OPTIMIZED: Use preloaded relationship instead of querying database
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
            smp_id=item.smp_id,
            so_number=item.so_number,
            planning_smp_id=item.planning_smp_id,
            planning_so_number=item.planning_so_number,
            implementation_smp_id=item.implementation_smp_id,
            implementation_so_number=item.implementation_so_number,
            dismantling_smp_id=item.dismantling_smp_id,
            dismantling_so_number=item.dismantling_so_number,
            epac_req=item.epac_req,
            inservice_date=item.inservice_date,
            triggering_file_path=item.triggering_file_path,
            logistics_file_path=item.logistics_file_path,
            uploaded_by=item.uploaded_by,
            uploader_name=item.uploader.username if item.uploader else None,  # OPTIMIZED: Use preloaded relationship
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
    """
    Get single approval by ID.

    OPTIMIZED: Uses eager loading to prevent N+1 query (2 queries → 1 query).
    """
    # OPTIMIZED: Eager load uploader to prevent separate query
    approval = db.query(Approval).options(
        joinedload(Approval.uploader)
    ).filter(Approval.id == approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    uploader = approval.uploader  # Already loaded via joinedload

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
        smp_id=approval.smp_id,
        so_number=approval.so_number,
        planning_smp_id=approval.planning_smp_id,
        planning_so_number=approval.planning_so_number,
        implementation_smp_id=approval.implementation_smp_id,
        implementation_so_number=approval.implementation_so_number,
        dismantling_smp_id=approval.dismantling_smp_id,
        dismantling_so_number=approval.dismantling_so_number,
        epac_req=approval.epac_req,
        inservice_date=approval.inservice_date,
        triggering_file_path=approval.triggering_file_path,
        logistics_file_path=approval.logistics_file_path,
        uploaded_by=approval.uploaded_by,
        uploader_name=uploader.username if uploader else None,
        created_at=approval.created_at,
        updated_at=approval.updated_at
    )


@router.post("/{approval_id}/approve")
async def approve_item(
    approval_id: int,
    approval_data: ApprovalApprove,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve an item - moves it to next stage or completes workflow"""
    from Models.BOQ.POReport import POReport
    import csv

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.stage == 'approval':
        # Determine if RAN or MW BOQ
        is_ran = 'Ran' in approval.project_type or 'RAN' in approval.project_type
        is_mw = 'MW' in approval.project_type or 'Mw' in approval.project_type

        # Validate that required SMP IDs are provided
        if not approval_data.planning_smp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Planning services SMP ID is required"
            )

        if not approval_data.implementation_smp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Implementation services SMP ID is required"
            )

        # For MW, dismantling SMP is also required
        if is_mw and not approval_data.dismantling_smp_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dismantling services SMP ID is required for MW BOQ"
            )

        # Validate EPAC Req and InService Date are provided
        if not approval_data.epac_req:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-PAC Req is required"
            )

        if not approval_data.inservice_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="InService Date is required"
            )

        # OPTIMIZED: Batch query for all SMP IDs to prevent N+1 queries (3 queries → 1 query)
        # Collect all SMP IDs that need to be looked up
        smp_ids_to_lookup = [approval_data.planning_smp_id, approval_data.implementation_smp_id]
        if is_mw and approval_data.dismantling_smp_id:
            smp_ids_to_lookup.append(approval_data.dismantling_smp_id)

        # Single batch query for all SMPs
        po_records = db.query(POReport).filter(POReport.smp_id.in_(smp_ids_to_lookup)).all()

        # Build lookup map: SMP ID -> list of PO records
        smp_po_map = {}
        for record in po_records:
            if record.smp_id not in smp_po_map:
                smp_po_map[record.smp_id] = []
            smp_po_map[record.smp_id].append(record)

        # Helper function to extract SO# from cached records
        def lookup_smp_so_number_from_cache(smp_id: str, description_keyword: str) -> str:
            """Lookup SO# from pre-fetched PO records"""
            records = smp_po_map.get(smp_id, [])

            if not records:
                return "N/A"

            # First, try to find a record with matching description keyword
            for record in records:
                if record.material_des and description_keyword.lower() in record.material_des.lower():
                    return record.so_number or "N/A"

            # If no match found by description, return SO# from first record with that SMP ID
            for record in records:
                if record.so_number:
                    return record.so_number

            return "N/A"

        # Lookup all SMPs using the cached data
        planning_so = lookup_smp_so_number_from_cache(approval_data.planning_smp_id, "Planning services")
        implementation_so = lookup_smp_so_number_from_cache(approval_data.implementation_smp_id, "Implementation services")

        # Lookup Dismantling services SMP (MW only)
        dismantling_so = "N/A"
        if is_mw and approval_data.dismantling_smp_id:
            dismantling_so = lookup_smp_so_number_from_cache(approval_data.dismantling_smp_id, "Dismantling")

        # Save all SMP IDs and SO# values to approval record
        approval.planning_smp_id = approval_data.planning_smp_id
        approval.planning_so_number = planning_so
        approval.implementation_smp_id = approval_data.implementation_smp_id
        approval.implementation_so_number = implementation_so
        approval.dismantling_smp_id = approval_data.dismantling_smp_id if is_mw else None
        approval.dismantling_so_number = dismantling_so if is_mw else None
        approval.epac_req = approval_data.epac_req
        approval.inservice_date = approval_data.inservice_date

        # For backward compatibility, store implementation SMP in old fields
        approval.smp_id = approval_data.implementation_smp_id
        approval.so_number = implementation_so

        # Generate triggering CSV from BOQ data
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            triggering_filename = f"{timestamp}_triggering_{approval.filename}"
            triggering_file_path = UPLOAD_DIR / triggering_filename

            # Resolve file path (handles both absolute and relative paths)
            source_path = resolve_file_path(approval.file_path)

            # Final check
            if not source_path.exists():
                logger.error(f"Source BOQ file not found: {approval.file_path} -> {source_path}")
                raise Exception(f"Source BOQ file not found. Please ensure the file exists at: {approval.file_path}")

            # Read BOQ CSV data and extract metadata
            boq_data = []
            boq_headers = None
            project_name = None
            po_number = None
            site_ip_index = None
            po_number_col_index = None  # For RAN BOQ PO# column
            po_line_index = None
            description_index = None
            quantity_index = None
            serial_num_index = None
            item_code_index = None
            merge_index = None

            # MW-specific columns
            vendor_part_number_index = None  # For MW Item Code
            l1_category_index = None  # For MW Activity
            upl_line_index = None  # For MW Merge POLine#UPLLine#

            # Sequence column (both RAN and MW)
            sequence_index = None

            # Determine project type (RAN or MW)
            is_ran = 'Ran' in approval.project_type or 'RAN' in approval.project_type

            # Try multiple encodings
            for encoding in ['utf-8', 'latin-1', 'windows-1252']:
                try:
                    with open(source_path, 'r', encoding=encoding, newline='') as f:
                        csv_reader = csv.reader(f)
                        all_rows = list(csv_reader)

                        # Search for Project Name and PO Number in first few rows
                        for row in all_rows[:10]:  # Check first 10 rows for metadata
                            for i, cell in enumerate(row):
                                if cell and 'Project Name:' in cell and i + 1 < len(row):
                                    project_name = row[i + 1].strip()
                                if cell and 'PO Number:' in cell and i + 1 < len(row):
                                    po_number = row[i + 1].strip()

                        # Find the header row (contains "Site_IP", "Site IP", or "Site ID")
                        for row_idx, row in enumerate(all_rows):
                            if any('Site_IP' in str(cell) or 'Site IP' in str(cell) or 'Site ID' in str(cell) for cell in row):
                                boq_headers = row

                                # Find column indices based on project type
                                for idx, header in enumerate(boq_headers):
                                    header_str = str(header).strip()

                                    # Site location column (Site_IP for MW, Site ID for RAN)
                                    if 'Site_IP' in header_str or 'Site IP' in header_str or 'Site ID' in header_str:
                                        site_ip_index = idx

                                    # PO# column (for RAN BOQ)
                                    if is_ran and (header_str == 'PO#' or header_str == 'PO #'):
                                        po_number_col_index = idx

                                    # PO Line column (RAN only)
                                    if is_ran and ('PO Line -L1' in header_str or 'PO Line-L1' in header_str):
                                        po_line_index = idx

                                    # Description column
                                    if is_ran and ('Model Name / Description' in header_str or 'Model Name/Description' in header_str):
                                        description_index = idx
                                    elif not is_ran and 'Item Name' in header_str:
                                        description_index = idx

                                    # Quantity column
                                    if is_ran and header_str == 'Quantity':
                                        quantity_index = idx
                                    elif not is_ran and 'Total Qtts' in header_str:
                                        quantity_index = idx

                                    # Serial Number column
                                    if is_ran and ('Serial number' in header_str or 'Serial Number' in header_str):
                                        serial_num_index = idx
                                    elif not is_ran and header_str == 'SN':
                                        serial_num_index = idx

                                    # Item Code column (RAN only)
                                    if is_ran and 'Item Code' in header_str:
                                        item_code_index = idx

                                    # Merge POLine# UPLLine# column (RAN only)
                                    if is_ran and ('Merge POLine# UPLLine#' in header_str or 'Merge POLine#UPLLine#' in header_str):
                                        merge_index = idx

                                    # L1 Category column (both RAN and MW for Activity)
                                    if 'L1 Category' in header_str or 'L1 category' in header_str:
                                        l1_category_index = idx

                                    # MW-specific columns
                                    if not is_ran:
                                        # Vendor Part Number (for MW Item Code)
                                        if 'Vendor Part Number' in header_str or 'Vendor part number' in header_str:
                                            vendor_part_number_index = idx

                                        # UPL Line (for MW Merge)
                                        if 'UPL Line' in header_str or 'UPL line' in header_str:
                                            upl_line_index = idx

                                    # Sequence column (both RAN and MW)
                                    if 'Sequence' in header_str or 'sequence' in header_str:
                                        sequence_index = idx

                                # Extract data rows after this header row
                                boq_data = all_rows[row_idx + 1:]
                                break

                        # If no header found, treat first non-empty row as header
                        if boq_headers is None:
                            for row_idx, row in enumerate(all_rows):
                                if any(cell.strip() for cell in row if cell):
                                    boq_headers = row
                                    boq_data = all_rows[row_idx + 1:]
                                    break

                    break  # Successfully read the file
                except UnicodeDecodeError:
                    continue

            # Extract PO number from PO# column if not found in metadata (RAN BOQ)
            if not po_number and po_number_col_index is not None and boq_data:
                for row in boq_data:
                    if row and len(row) > po_number_col_index and row[po_number_col_index].strip():
                        po_number = row[po_number_col_index].strip()
                        break

            # For RAN BOQ, look up project details from database
            if is_ran:
                from Models.RAN.RANProject import RanProject
                ran_project = db.query(RanProject).filter(RanProject.pid_po == approval.project_id).first()
                if ran_project:
                    project_name = ran_project.project_name
                    po_number = ran_project.pid_po

            # Fallback: use project_id if PO not found
            if not po_number:
                po_number = approval.project_id

            # Create triggering CSV with proper headers (removed final SO# column)
            triggering_headers = [
                'Project Name', 'Activity', 'Location ID', 'E-PAC Req', 'PO LINE',
                'Description', 'Delivered Quantity', 'Seq', 'Serial Num', 'Service Date',
                'Item Code', 'Merge POLine#UPLLine#', 'Service #SO', 'NPO #SO'
            ]

            with open(triggering_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(triggering_headers)

                # Write data rows from BOQ with proper mapping
                for boq_row in boq_data:
                    # Skip empty rows
                    if not any(cell.strip() for cell in boq_row if cell):
                        continue

                    # Build triggering row
                    triggering_row = [''] * len(triggering_headers)

                    # Column 0: Project Name - format as "ProjectName PO:Number"
                    if project_name and po_number:
                        triggering_row[0] = f"{project_name} PO:{po_number}"
                    elif project_name:
                        triggering_row[0] = project_name
                    else:
                        triggering_row[0] = ''

                    # Column 1: Activity - Both RAN and MW: L1 Category
                    if l1_category_index is not None and l1_category_index < len(boq_row):
                        triggering_row[1] = boq_row[l1_category_index].strip()
                    else:
                        triggering_row[1] = ''

                    # Column 2: Location ID - extract from Site_IP column in BOQ
                    if site_ip_index is not None and site_ip_index < len(boq_row):
                        triggering_row[2] = boq_row[site_ip_index].strip()
                    else:
                        triggering_row[2] = ''

                    # Column 3: E-PAC Req - fill with epac_req value
                    triggering_row[3] = approval.epac_req or ''

                    # Column 4: PO LINE - RAN: from "PO Line -L1", MW: always "6"
                    if is_ran:
                        if po_line_index is not None and po_line_index < len(boq_row):
                            triggering_row[4] = boq_row[po_line_index].strip()
                        else:
                            triggering_row[4] = ''
                    else:
                        # MW always uses PO LINE 6
                        triggering_row[4] = '6'

                    # Column 5: Description - MW: "Item Name", RAN: "Model Name / Description"
                    if description_index is not None and description_index < len(boq_row):
                        triggering_row[5] = boq_row[description_index].strip()
                    else:
                        triggering_row[5] = ''

                    # Column 6: Delivered Quantity - MW: "Total Qtts", RAN: "Quantity"
                    if quantity_index is not None and quantity_index < len(boq_row):
                        triggering_row[6] = boq_row[quantity_index].strip()
                    else:
                        triggering_row[6] = ''

                    # Column 7: Seq - extract from Sequence column in BOQ
                    if sequence_index is not None and sequence_index < len(boq_row):
                        triggering_row[7] = boq_row[sequence_index].strip()
                    else:
                        triggering_row[7] = ''

                    # Column 8: Serial Num - MW: "SN", RAN: "Serial number"
                    if serial_num_index is not None and serial_num_index < len(boq_row):
                        triggering_row[8] = boq_row[serial_num_index].strip()
                    else:
                        triggering_row[8] = ''

                    # Column 9: Service Date - fill with inservice_date value
                    triggering_row[9] = approval.inservice_date or ''

                    # Column 10: Item Code - RAN: "Item Code", MW: "Vendor Part Number"
                    if is_ran:
                        if item_code_index is not None and item_code_index < len(boq_row):
                            triggering_row[10] = boq_row[item_code_index].strip()
                        else:
                            triggering_row[10] = ''
                    else:
                        # MW uses Vendor Part Number
                        if vendor_part_number_index is not None and vendor_part_number_index < len(boq_row):
                            triggering_row[10] = boq_row[vendor_part_number_index].strip()
                        else:
                            triggering_row[10] = ''

                    # Column 11: Merge POLine#UPLLine# - RAN: "Merge POLine# UPLLine#", MW: "6\{UPL_LINE}"
                    if is_ran:
                        if merge_index is not None and merge_index < len(boq_row):
                            triggering_row[11] = boq_row[merge_index].strip()
                        else:
                            triggering_row[11] = ''
                    else:
                        # MW uses format "6\{UPL_LINE}"
                        if upl_line_index is not None and upl_line_index < len(boq_row):
                            upl_line_value = boq_row[upl_line_index].strip()
                            triggering_row[11] = f"6\\{upl_line_value}" if upl_line_value else ''
                        else:
                            triggering_row[11] = ''

                    # Column 12: Service #SO - map based on description column
                    row_description = ''
                    if description_index is not None and description_index < len(boq_row):
                        # Normalize whitespace: replace multiple spaces with single space
                        row_description = ' '.join(boq_row[description_index].strip().lower().split())

                    so_value = ''
                    if 'planning' in row_description and 'service' in row_description:
                        so_value = approval.planning_so_number or 'N/A'
                    elif 'implementation' in row_description and 'service' in row_description:
                        so_value = approval.implementation_so_number or 'N/A'
                    elif is_mw and ('dismantling' in row_description):
                        so_value = approval.dismantling_so_number or 'N/A'
                    else:
                        so_value = 'N/A'

                    triggering_row[12] = so_value

                    # Column 13: NPO #SO - empty for now
                    triggering_row[13] = ''

                    writer.writerow(triggering_row)

            approval.triggering_file_path = str(triggering_file_path)
            logger.info(f"Generated triggering CSV for approval {approval_id}. Rows: {len(boq_data)}, SO#: {approval.so_number}")

        except Exception as e:
            logger.error(f"Error generating triggering CSV for approval {approval_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating triggering CSV: {str(e)}"
            )

        # Move from approval to triggering stage
        approval.stage = 'triggering'
        approval.status = 'pending_triggering'
        approval.notes = None  # Clear any previous rejection notes
        db.commit()
        logger.info(f"Approval {approval_id} moved to triggering stage by user {current_user.id}")

        # Create audit log for approval stage advancement
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="approve_to_triggering",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "previous_stage": "approval",
                "new_stage": "triggering",
                "planning_smp_id": approval.planning_smp_id,
                "implementation_smp_id": approval.implementation_smp_id
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "Moved to triggering stage with multi-SMP mapping",
            "stage": "triggering",
            "planning_smp_id": approval.planning_smp_id,
            "planning_so_number": approval.planning_so_number,
            "implementation_smp_id": approval.implementation_smp_id,
            "implementation_so_number": approval.implementation_so_number,
            "dismantling_smp_id": approval.dismantling_smp_id,
            "dismantling_so_number": approval.dismantling_so_number,
            "epac_req": approval.epac_req,
            "inservice_date": approval.inservice_date
        }

    elif approval.stage == 'triggering':
        # Generate logistics CSV from triggering CSV + PriceBook lookups
        from Models.BOQ.PriceBook import PriceBook

        try:
            if not approval.triggering_file_path:
                raise Exception("Triggering file path not set on approval record")

            triggering_path = resolve_file_path(approval.triggering_file_path)
            if not triggering_path.exists():
                raise Exception(f"Triggering file not found at: {approval.triggering_file_path}")

            with open(triggering_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                triggering_rows = list(reader)

            if len(triggering_rows) < 2:
                raise Exception("Triggering CSV has no data rows")

            headers = triggering_rows[0]
            data_rows = triggering_rows[1:]

            # Get actual PO number from the Project/RanProject model
            # pid_po is a combined key — PriceBook.po_number stores only the PO part
            po_number = None
            is_ran = 'Ran' in approval.project_type or 'RAN' in approval.project_type
            if is_ran:
                from Models.RAN.RANProject import RanProject
                project = db.query(RanProject).filter(RanProject.pid_po == approval.project_id).first()
                if project:
                    po_number = project.po
            else:
                from Models.BOQ.Project import Project
                project = db.query(Project).filter(Project.pid_po == approval.project_id).first()
                if project:
                    po_number = project.po

            # Fallback: extract from triggering CSV "Project Name" column → "{name} PO:{po}"
            if not po_number:
                first_project_name = data_rows[0][0].strip() if data_rows[0] else ''
                if ' PO:' in first_project_name:
                    po_number = first_project_name.split(' PO:', 1)[1].strip()

            logger.info(f"Logistics CSV generation: approval={approval_id}, project_id={approval.project_id}, po_number={po_number}")

            # Query PriceBook by PO, build lookup: normalized merge key → (unit_price, fv_unit_price)
            price_lookup = {}
            if po_number:
                pb_records = db.query(
                    PriceBook.merge_poline_uplline,
                    PriceBook.unit_price_sar_after_special_discount,
                    PriceBook.fv_unit_price_after_descope
                ).filter(PriceBook.po_number == po_number).all()

                for rec in pb_records:
                    if rec.merge_poline_uplline:
                        price_lookup[rec.merge_poline_uplline.strip()] = (
                            rec.unit_price_sar_after_special_discount or '',
                            rec.fv_unit_price_after_descope or ''
                        )

            # Find "Merge POLine#UPLLine#" column index in triggering CSV
            merge_col_idx = None
            for i, h in enumerate(headers):
                if 'Merge POLine#UPLLine#' in h:
                    merge_col_idx = i
                    break

            # Write logistics CSV: triggering columns + 2 price columns
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            logistics_filename = f"{timestamp}_logistics_{approval.filename}"
            logistics_file_path = UPLOAD_DIR / logistics_filename

            logistics_headers = headers + [
                'Unit Price(SAR) after Special Discount for this project only (% on), not applicable for future reference',
                'FV Unit Price after Descope'
            ]

            with open(logistics_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(logistics_headers)

                for row in data_rows:
                    unit_price_val = ''
                    fv_price_val = ''
                    if merge_col_idx is not None and merge_col_idx < len(row):
                        # Normalize: triggering uses "x\y", PriceBook uses "x_y"
                        normalized_key = row[merge_col_idx].strip().replace('\\', '_')
                        if normalized_key in price_lookup:
                            unit_price_val, fv_price_val = price_lookup[normalized_key]
                    writer.writerow(row + [unit_price_val, fv_price_val])

            approval.logistics_file_path = str(logistics_file_path)
            logger.info(f"Generated logistics CSV for approval {approval_id}, PO={po_number}, PriceBook matches={len(price_lookup)}")

        except Exception as e:
            logger.error(f"Error generating logistics CSV for approval {approval_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating logistics CSV: {str(e)}"
            )

        # Move from triggering to logistics stage
        approval.stage = 'logistics'
        approval.status = 'pending_logistics'
        approval.notes = None  # Clear any previous rejection notes
        db.commit()
        logger.info(f"Approval {approval_id} moved to logistics stage by user {current_user.id}")

        # Create audit log for triggering stage advancement
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="approve_to_logistics",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "previous_stage": "triggering",
                "new_stage": "logistics"
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "Moved to logistics stage",
            "stage": "logistics"
        }

    elif approval.stage == 'logistics':
        # Final approval - workflow complete
        approval.status = 'approved'
        db.commit()
        logger.info(f"Approval {approval_id} fully approved by user {current_user.id}")

        # Create audit log for final approval
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="approve_complete",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "previous_stage": "logistics",
                "final_status": "approved"
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "Workflow completed - fully approved", "stage": "completed"}

    return {"message": "No action taken"}


@router.post("/{approval_id}/reject")
async def reject_item(
    approval_id: int,
    rejection: ApprovalReject,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject an item - sends back to previous stage with notes"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.stage == 'logistics':
        # Send back to triggering stage with notes
        previous_stage = approval.stage
        approval.stage = 'triggering'
        approval.status = 'rejected'
        approval.notes = rejection.notes
        db.commit()
        logger.info(f"Approval {approval_id} rejected by logistics team, sent back to triggering by user {current_user.id}")

        # Create audit log for rejection
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="reject",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "previous_stage": previous_stage,
                "new_stage": "triggering",
                "rejection_notes": rejection.notes
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "Sent back to triggering stage", "stage": "triggering"}

    elif approval.stage == 'triggering':
        # Send back to approval stage with notes
        previous_stage = approval.stage
        approval.stage = 'approval'
        approval.status = 'rejected'
        approval.notes = rejection.notes
        db.commit()
        logger.info(f"Approval {approval_id} rejected by triggering team, sent back to approval by user {current_user.id}")

        # Create audit log for rejection
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="reject",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "previous_stage": previous_stage,
                "new_stage": "approval",
                "rejection_notes": rejection.notes
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "Sent back to approval stage", "stage": "approval"}

    elif approval.stage == 'approval':
        # Reject at approval stage
        approval.status = 'rejected'
        approval.notes = rejection.notes
        db.commit()
        logger.info(f"Approval {approval_id} rejected at approval stage by user {current_user.id}")

        # Create audit log for rejection
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="reject",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval.filename,
            details=json.dumps({
                "stage": "approval",
                "rejection_notes": rejection.notes
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "Rejected at approval stage", "stage": "approval"}

    return {"message": "No action taken"}


@router.delete("/{approval_id}")
async def delete_approval(
    approval_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an approval and its file"""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Store data for audit log before deletion
    approval_filename = approval.filename
    approval_project_id = approval.project_id

    try:
        # Delete CSV file
        csv_file_path = resolve_file_path(approval.file_path)
        if csv_file_path.exists():
            csv_file_path.unlink()

        # Delete template file
        template_file_path = resolve_file_path(approval.template_file_path)
        if template_file_path.exists():
            template_file_path.unlink()

        # Delete triggering file if it exists
        if approval.triggering_file_path:
            triggering_file_path = resolve_file_path(approval.triggering_file_path)
            if triggering_file_path.exists():
                triggering_file_path.unlink()

        # Delete logistics file if it exists
        if approval.logistics_file_path:
            logistics_file_path = resolve_file_path(approval.logistics_file_path)
            if logistics_file_path.exists():
                logistics_file_path.unlink()

        db.delete(approval)
        db.commit()

        logger.info(f"Approval {approval_id} deleted by user {current_user.id}")

        # Create audit log for deletion
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete",
            resource_type="Approval",
            resource_id=str(approval_id),
            resource_name=approval_filename,
            details=json.dumps({
                "project_id": approval_project_id
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"success": True, "message": f"Approval '{approval_filename}' deleted"}

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

    file_path = resolve_file_path(approval.file_path)
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

    template_path = resolve_file_path(approval.template_file_path)
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


@router.get("/download-triggering/{approval_id}")
async def download_triggering_csv(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download triggering CSV file"""
    from fastapi.responses import FileResponse

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if not approval.triggering_file_path:
        raise HTTPException(
            status_code=404,
            detail="Triggering file not yet generated. Approve the item first."
        )

    triggering_path = resolve_file_path(approval.triggering_file_path)
    if not triggering_path.exists():
        raise HTTPException(status_code=404, detail="Triggering file not found")

    # Extract filename from path
    filename = triggering_path.name

    return FileResponse(
        path=str(triggering_path),
        filename=filename,
        media_type='text/csv'
    )


@router.get("/download-logistics/{approval_id}")
async def download_logistics_csv(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download logistics CSV file"""
    from fastapi.responses import FileResponse

    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if not approval.logistics_file_path:
        raise HTTPException(
            status_code=404,
            detail="Logistics file not yet generated. Approve the triggering item first."
        )

    logistics_path = resolve_file_path(approval.logistics_file_path)
    if not logistics_path.exists():
        raise HTTPException(status_code=404, detail="Logistics file not found")

    return FileResponse(
        path=str(logistics_path),
        filename=logistics_path.name,
        media_type='text/csv'
    )


@router.post("/bulk-download-logistics")
async def bulk_download_logistics(
    body: BulkLogisticsDownload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download multiple logistics CSVs combined into a single CSV"""
    import csv as csv_mod
    import io
    from fastapi.responses import StreamingResponse

    if not body.approval_ids:
        raise HTTPException(status_code=400, detail="No approval IDs provided")

    approvals = db.query(Approval).filter(Approval.id.in_(body.approval_ids)).all()
    if not approvals:
        raise HTTPException(status_code=404, detail="No matching approvals found")

    combined_rows = []
    header = None

    for approval in approvals:
        if not approval.logistics_file_path:
            continue

        logistics_path = resolve_file_path(approval.logistics_file_path)
        if not logistics_path.exists():
            continue

        with open(logistics_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv_mod.reader(f)
            rows = list(reader)

        if len(rows) < 2:
            continue

        if header is None:
            header = rows[0]

        combined_rows.extend(rows[1:])

    if header is None:
        raise HTTPException(status_code=404, detail="No logistics files found for selected approvals")

    # Write combined CSV to in-memory buffer
    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(header)
    writer.writerows(combined_rows)

    output.seek(0)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')

    return StreamingResponse(
        output,
        media_type='text/csv',
        headers={"Content-Disposition": f"attachment; filename={timestamp}_bulk_logistics.csv"}
    )


@router.post("/bulk-approve")
async def bulk_approve(
    body: BulkApprove,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk approve multiple items - moves them to next stage"""
    import csv as csv_mod
    from Models.BOQ.PriceBook import PriceBook

    if not body.approval_ids:
        raise HTTPException(status_code=400, detail="No approval IDs provided")

    approvals = db.query(Approval).filter(Approval.id.in_(body.approval_ids)).all()
    if not approvals:
        raise HTTPException(status_code=404, detail="No matching approvals found")

    success_count = 0
    failed_count = 0
    errors = []

    for approval in approvals:
        try:
            if approval.stage == 'triggering':
                # Generate logistics CSV from triggering CSV + PriceBook lookups
                if not approval.triggering_file_path:
                    errors.append(f"{approval.filename}: Triggering file path not set")
                    failed_count += 1
                    continue

                triggering_path = resolve_file_path(approval.triggering_file_path)
                if not triggering_path.exists():
                    errors.append(f"{approval.filename}: Triggering file not found")
                    failed_count += 1
                    continue

                with open(triggering_path, 'r', encoding='utf-8', newline='') as f:
                    reader = csv_mod.reader(f)
                    triggering_rows = list(reader)

                if len(triggering_rows) < 2:
                    errors.append(f"{approval.filename}: Triggering CSV has no data rows")
                    failed_count += 1
                    continue

                headers = triggering_rows[0]
                data_rows = triggering_rows[1:]

                # Get actual PO number from the Project/RanProject model
                po_number = None
                is_ran = 'Ran' in approval.project_type or 'RAN' in approval.project_type
                if is_ran:
                    from Models.RAN.RANProject import RanProject
                    project = db.query(RanProject).filter(RanProject.pid_po == approval.project_id).first()
                    if project:
                        po_number = project.po
                else:
                    from Models.BOQ.Project import Project
                    project = db.query(Project).filter(Project.pid_po == approval.project_id).first()
                    if project:
                        po_number = project.po

                # Fallback: extract from triggering CSV "Project Name" column
                if not po_number:
                    first_project_name = data_rows[0][0].strip() if data_rows[0] else ''
                    if ' PO:' in first_project_name:
                        po_number = first_project_name.split(' PO:', 1)[1].strip()

                # Query PriceBook by PO, build lookup
                price_lookup = {}
                if po_number:
                    pb_records = db.query(
                        PriceBook.merge_poline_uplline,
                        PriceBook.unit_price_sar_after_special_discount,
                        PriceBook.fv_unit_price_after_descope
                    ).filter(PriceBook.po_number == po_number).all()

                    for rec in pb_records:
                        if rec.merge_poline_uplline:
                            price_lookup[rec.merge_poline_uplline.strip()] = (
                                rec.unit_price_sar_after_special_discount or '',
                                rec.fv_unit_price_after_descope or ''
                            )

                # Find "Merge POLine#UPLLine#" column index
                merge_col_idx = None
                for i, h in enumerate(headers):
                    if 'Merge POLine#UPLLine#' in h:
                        merge_col_idx = i
                        break

                # Write logistics CSV
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                logistics_filename = f"{timestamp}_logistics_{approval.filename}"
                logistics_file_path = UPLOAD_DIR / logistics_filename

                logistics_headers = headers + [
                    'Unit Price(SAR) after Special Discount for this project only (% on), not applicable for future reference',
                    'FV Unit Price after Descope'
                ]

                with open(logistics_file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv_mod.writer(f)
                    writer.writerow(logistics_headers)

                    for row in data_rows:
                        unit_price_val = ''
                        fv_price_val = ''
                        if merge_col_idx is not None and merge_col_idx < len(row):
                            normalized_key = row[merge_col_idx].strip().replace('\\', '_')
                            if normalized_key in price_lookup:
                                unit_price_val, fv_price_val = price_lookup[normalized_key]
                        writer.writerow(row + [unit_price_val, fv_price_val])

                approval.logistics_file_path = str(logistics_file_path)
                approval.stage = 'logistics'
                approval.status = 'pending_logistics'
                approval.notes = None
                success_count += 1
                logger.info(f"Bulk approve: Approval {approval.id} moved to logistics by user {current_user.id}")

            elif approval.stage == 'logistics':
                # Final approval - workflow complete
                approval.status = 'approved'
                success_count += 1
                logger.info(f"Bulk approve: Approval {approval.id} fully approved by user {current_user.id}")

            else:
                # Approval stage requires SMP input, cannot bulk approve
                errors.append(f"{approval.filename}: Cannot bulk approve from approval stage (requires SMP input)")
                failed_count += 1

        except Exception as e:
            logger.error(f"Bulk approve error for approval {approval.id}: {e}")
            errors.append(f"{approval.filename}: {str(e)}")
            failed_count += 1

    db.commit()

    # Create audit log for bulk approval
    await create_audit_log(
        db=db,
        user_id=current_user.id,
        action="bulk_approve",
        resource_type="Approval",
        resource_id=",".join([str(id) for id in body.approval_ids]),
        resource_name=f"Bulk approval of {len(body.approval_ids)} items",
        details=json.dumps({
            "success_count": success_count,
            "failed_count": failed_count,
            "approval_ids": body.approval_ids
        }),
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent")
    )

    return {
        "message": f"Bulk approval completed: {success_count} succeeded, {failed_count} failed",
        "success_count": success_count,
        "failed_count": failed_count,
        "errors": errors if errors else None
    }


@router.get("/projects/{project_type}")
async def get_projects_by_type(
    project_type: str,
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get projects list based on project type (MW or RAN) with pagination.

    OPTIMIZED: Added pagination (skip/limit) to prevent returning thousands of projects at once.
    """
    from Models.BOQ.Project import Project
    from Models.RAN.RANProject import RanProject

    if project_type == "Zain MW BOQ":
        # OPTIMIZED: Added pagination to prevent loading all projects
        # MSSQL requires ORDER BY when using OFFSET/LIMIT
        projects = db.query(Project.pid_po, Project.project_name).order_by(Project.pid_po).offset(skip).limit(limit).all()
        return [{"id": p.pid_po, "name": p.project_name} for p in projects]
    elif project_type == "Zain Ran BOQ":
        # OPTIMIZED: Added pagination to prevent loading all projects
        # MSSQL requires ORDER BY when using OFFSET/LIMIT
        projects = db.query(RanProject.pid_po, RanProject.project_name).order_by(RanProject.pid_po).offset(skip).limit(limit).all()
        return [{"id": p.pid_po, "name": p.project_name} for p in projects]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project_type. Must be 'Zain MW BOQ' or 'Zain Ran BOQ'"
        )


@router.get("/user/permissions")
async def get_user_approval_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's approval workflow stage permissions"""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.name,
        "can_access_approval": current_user.can_access_approval or current_user.role.name == "senior_admin",
        "can_access_triggering": current_user.can_access_triggering or current_user.role.name == "senior_admin",
        "can_access_logistics": current_user.can_access_logistics or current_user.role.name == "senior_admin"
    }
