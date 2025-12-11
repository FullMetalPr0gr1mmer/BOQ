# routes/5G_Rollout_Sheet_Route.py
"""
5G Rollout Sheet API Routes

This module provides CRUD operations for managing 5G Rollout Sheet data.
It includes pagination, search, admin control, and CSV upload functionality.
"""

import json
import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional

from APIs.Core import get_db, get_current_user
from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Models.DU.OD_BOQ_Item import ODBOQItem, LEVEL1_CATEGORIES, QUANTITY_FIELDS
from Models.DU.CustomerPO import CustomerPO

# Import model using importlib since filename starts with number
import importlib
rollout_model = importlib.import_module("Models.DU.5G_Rollout_Sheet")
_5G_Rollout_Sheet = rollout_model._5G_Rollout_Sheet

# Import DU Project model
du_project_model = importlib.import_module("Models.DU.DU_Project")
DUProject = du_project_model.DUProject

# Import schemas using importlib since filename starts with number
rollout_schema = importlib.import_module("Schemas.DU.5G_Rollout_Sheet_Schema")
Create5GRolloutSheet = rollout_schema.Create5GRolloutSheet
Update5GRolloutSheet = rollout_schema.Update5GRolloutSheet
RolloutSheetOut = rollout_schema.RolloutSheetOut
RolloutSheetPagination = rollout_schema.RolloutSheetPagination
RolloutSheetStatsResponse = rollout_schema.RolloutSheetStatsResponse
UploadResponse = rollout_schema.UploadResponse

rolloutSheetRoute = APIRouter(tags=["5G Rollout Sheet"])


# ===========================
# HELPER FUNCTIONS
# ===========================

async def create_audit_log(
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
):
    """Create an audit log entry."""
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
    return audit_log


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_admin_access(current_user: User, required_permission: str = "view"):
    """
    Check if user has admin access with required permission level.

    Args:
        current_user: The current user
        required_permission: Required permission level ("view", "edit", "all")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # Admin has edit and view permissions
    if current_user.role.name == "admin":
        if required_permission in ["view", "edit"]:
            return True

    # Regular users only have view permission
    if required_permission == "view":
        return True

    return False


def filter_rollout_by_user_access(current_user: User, query, db: Session):
    """
    Filter rollout sheet query based on user's project access.
    Senior admins can see all records.
    """
    if current_user.role.name == "senior_admin":
        return query

    # Get accessible project IDs for non-senior admins
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        # User has no project access, return empty query
        return query.filter(_5G_Rollout_Sheet.id == -1)

    accessible_project_ids = [access.project_id for access in user_accesses]

    # Filter by accessible projects
    return query.filter(_5G_Rollout_Sheet.project_id.in_(accessible_project_ids))


# ===========================
# CRUD OPERATIONS
# ===========================

@rolloutSheetRoute.post("/rollout-sheet", response_model=RolloutSheetOut)
async def create_rollout_sheet(
        data: Create5GRolloutSheet,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new 5G Rollout Sheet entry.
    Requires 'edit' or 'all' permission.
    """
    # Check permission
    if not check_admin_access(current_user, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create rollout sheet entries. Contact the Senior Admin."
        )

    try:
        new_entry = _5G_Rollout_Sheet(**data.dict())
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_rollout_sheet",
            resource_type="rollout_sheet",
            resource_id=str(new_entry.id),
            resource_name=new_entry.site_id,
            details=json.dumps({
                "site_id": data.site_id,
                "partner": data.partner,
                "request_status": data.request_status
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_entry
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating rollout sheet entry: {str(e)}"
        )


@rolloutSheetRoute.get("/rollout-sheet/stats", response_model=RolloutSheetStatsResponse)
def get_rollout_sheet_stats(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get rollout sheet statistics (total items, unique sites, unique partners).
    Optionally filter by project_id.
    """
    try:
        query = db.query(_5G_Rollout_Sheet)

        # Filter by user access
        query = filter_rollout_by_user_access(current_user, query, db)

        # Filter by project if specified
        if project_id:
            query = query.filter(_5G_Rollout_Sheet.project_id == project_id)

        total_items = query.count()

        # Count unique sites
        unique_sites = query.with_entities(
            func.count(func.distinct(_5G_Rollout_Sheet.site_id))
        ).scalar() or 0

        # Count unique partners
        unique_partners = query.with_entities(
            func.count(func.distinct(_5G_Rollout_Sheet.partner))
        ).scalar() or 0

        return RolloutSheetStatsResponse(
            total_items=total_items,
            unique_sites=unique_sites,
            unique_partners=unique_partners
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving rollout sheet stats: {str(e)}"
        )


@rolloutSheetRoute.get("/rollout-sheet", response_model=RolloutSheetPagination)
def get_rollout_sheets(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        search: Optional[str] = Query(None),
        project_id: Optional[str] = Query(None),
        partner: Optional[str] = Query(None),
        request_status: Optional[str] = Query(None),
        integration_status: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get paginated list of 5G Rollout Sheet entries with optional filters.
    Users can only see entries from projects they have access to.
    """
    try:
        query = db.query(_5G_Rollout_Sheet)

        # Filter by user access
        query = filter_rollout_by_user_access(current_user, query, db)

        # Apply filters
        if project_id:
            query = query.filter(_5G_Rollout_Sheet.project_id == project_id)

        if partner:
            query = query.filter(_5G_Rollout_Sheet.partner == partner)

        if request_status:
            query = query.filter(_5G_Rollout_Sheet.request_status == request_status)

        if integration_status:
            query = query.filter(_5G_Rollout_Sheet.integration_status == integration_status)

        # Apply search across multiple fields
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    _5G_Rollout_Sheet.site_id.ilike(search_pattern),
                    _5G_Rollout_Sheet.partner.ilike(search_pattern),
                    _5G_Rollout_Sheet.partner_requester_name.ilike(search_pattern),
                    _5G_Rollout_Sheet.du_po_number.ilike(search_pattern),
                    _5G_Rollout_Sheet.smp_number.ilike(search_pattern),
                    _5G_Rollout_Sheet.wo_number.ilike(search_pattern),
                    _5G_Rollout_Sheet.nokia_rollout_requester.ilike(search_pattern)
                )
            )

        total_count = query.count()
        records = query.order_by(_5G_Rollout_Sheet.id.desc()).offset(skip).limit(limit).all()

        return RolloutSheetPagination(records=records, total=total_count)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving rollout sheets: {str(e)}"
        )


@rolloutSheetRoute.get("/rollout-sheet/filters/options")
def get_filter_options(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get unique values for filter dropdowns (partners, request statuses, integration statuses).
    Must be defined before /{entry_id} to avoid route conflict.
    """
    try:
        query = db.query(_5G_Rollout_Sheet)
        query = filter_rollout_by_user_access(current_user, query, db)

        # Get unique partners
        partners = query.with_entities(
            _5G_Rollout_Sheet.partner
        ).distinct().all()
        partners = [p[0] for p in partners if p[0]]

        # Get unique request statuses
        request_statuses = query.with_entities(
            _5G_Rollout_Sheet.request_status
        ).distinct().all()
        request_statuses = [s[0] for s in request_statuses if s[0]]

        # Get unique integration statuses
        integration_statuses = query.with_entities(
            _5G_Rollout_Sheet.integration_status
        ).distinct().all()
        integration_statuses = [s[0] for s in integration_statuses if s[0]]

        # Get unique year target scopes
        year_scopes = query.with_entities(
            _5G_Rollout_Sheet.year_target_scope
        ).distinct().all()
        year_scopes = [y[0] for y in year_scopes if y[0]]

        return {
            "partners": sorted(partners),
            "request_statuses": sorted(request_statuses),
            "integration_statuses": sorted(integration_statuses),
            "year_target_scopes": sorted(year_scopes)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving filter options: {str(e)}"
        )


@rolloutSheetRoute.get("/rollout-sheet/{entry_id}", response_model=RolloutSheetOut)
def get_rollout_sheet_by_id(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific 5G Rollout Sheet entry by ID.
    """
    entry = db.query(_5G_Rollout_Sheet).filter(_5G_Rollout_Sheet.id == entry_id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Rollout sheet entry not found")

    # Check if user has access to this entry's project
    if current_user.role.name != "senior_admin" and entry.project_id:
        user_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.project_id == entry.project_id
        ).first()

        if not user_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this rollout sheet entry."
            )

    return entry


@rolloutSheetRoute.put("/rollout-sheet/{entry_id}", response_model=RolloutSheetOut)
async def update_rollout_sheet(
        entry_id: int,
        data: Update5GRolloutSheet,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update an existing 5G Rollout Sheet entry.
    Requires 'edit' or 'all' permission.
    """
    # Check permission
    if not check_admin_access(current_user, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update rollout sheet entries. Contact the Senior Admin."
        )

    entry = db.query(_5G_Rollout_Sheet).filter(_5G_Rollout_Sheet.id == entry_id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Rollout sheet entry not found")

    try:
        # Store old data for audit log
        old_data = {
            "site_id": entry.site_id,
            "partner": entry.partner,
            "request_status": entry.request_status
        }

        # Update only provided fields
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(entry, field, value)

        db.commit()
        db.refresh(entry)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_rollout_sheet",
            resource_type="rollout_sheet",
            resource_id=str(entry.id),
            resource_name=entry.site_id,
            details=json.dumps({
                "old_data": old_data,
                "new_data": update_data
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return entry
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating rollout sheet entry: {str(e)}"
        )


@rolloutSheetRoute.delete("/rollout-sheet/{entry_id}")
async def delete_rollout_sheet(
        entry_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete a 5G Rollout Sheet entry.
    Requires 'all' permission (senior_admin only).
    """
    # Check permission - only senior_admin can delete
    if not check_admin_access(current_user, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete rollout sheet entries. Contact the Senior Admin."
        )

    entry = db.query(_5G_Rollout_Sheet).filter(_5G_Rollout_Sheet.id == entry_id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Rollout sheet entry not found")

    try:
        # Store data for audit log before deletion
        entry_data = {
            "site_id": entry.site_id,
            "partner": entry.partner,
            "project_id": entry.project_id,
            "request_status": entry.request_status
        }

        db.delete(entry)
        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_rollout_sheet",
            resource_type="rollout_sheet",
            resource_id=str(entry_id),
            resource_name=entry_data["site_id"],
            details=json.dumps(entry_data),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"Rollout sheet entry {entry_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting rollout sheet entry: {str(e)}"
        )


# ===========================
# BULK OPERATIONS
# ===========================

@rolloutSheetRoute.post("/rollout-sheet/upload-csv", response_model=UploadResponse)
async def upload_rollout_sheet_csv(
        file: UploadFile = File(...),
        project_id: str = Form(None),
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload a CSV file to create/update 5G Rollout Sheet entries.
    Requires 'edit' or 'all' permission.
    """
    # Check permission
    if not check_admin_access(current_user, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload rollout sheet data. Contact the Senior Admin."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()

        # Try multiple encodings to handle different CSV formats
        csv_content = None
        encodings = ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']

        for encoding in encodings:
            try:
                csv_content = StringIO(content.decode(encoding))
                break
            except UnicodeDecodeError:
                continue

        if csv_content is None:
            raise HTTPException(
                status_code=400,
                detail="Unable to decode CSV file. Please ensure it's saved in UTF-8, Windows-1252, or Latin-1 encoding."
            )

        csv_reader = csv.DictReader(csv_content)

        # Define header mapping for CSV columns to model fields
        header_mapping = {
            'SiteID': 'site_id',
            'Scope': 'scope',
            'Year Target Scope': 'year_target_scope',
            'Partner': 'partner',
            'Partner Requester Name': 'partner_requester_name',
            'Date of Partner Request': 'date_of_partner_request',
            'Survey Partner': 'survey_partner',
            'Implementation Partner': 'implementation_partner',
            'Ant Swap': 'ant_swap',
            'Additional Cost': 'additional_cost',
            'WR Transportation': 'wr_transportation',
            'Crane': 'crane',
            'AC Armod Cable New SRAN': 'ac_armod_cable_new_sran',
            'Military Factor': 'military_factor',
            'CICPA Factor': 'cicpa_factor',
            'Nokia Rollout Requester': 'nokia_rollout_requester',
            'Services Validation by Rollout': 'services_validation_by_rollout',
            'Date of Validation by Rollout': 'date_of_validation_by_rollout',
            'Request Status': 'request_status',
            'Du PO#': 'du_po_number',
            'Integration Status': 'integration_status',
            'Integration Date': 'integration_date',
            'DU PO Convention Name': 'du_po_convention_name',
            'PO Year Issuance': 'po_year_issuance',
            'SMP#': 'smp_number',
            'WO#': 'wo_number',
            'SPS Category': 'sps_category',
            'Submission Date': 'submission_date',
            'PO Status': 'po_status',
            'PAC Received': 'pac_received',
            'Date of PAC': 'date_of_pac',
            'Hardware Remark': 'hardware_remark',
            'Project ID': 'project_id'
        }

        inserted_count = 0
        updated_count = 0

        for row in csv_reader:
            # Map CSV columns to model fields
            entry_data = {}
            for csv_header, model_field in header_mapping.items():
                value = row.get(csv_header, '').strip() if row.get(csv_header) else None
                if value:
                    entry_data[model_field] = value

            # Use form project_id if not in CSV
            if not entry_data.get('project_id') and project_id:
                entry_data['project_id'] = project_id

            # Skip rows without site_id
            if not entry_data.get('site_id'):
                continue

            # Check if entry exists (by site_id and project_id)
            existing_entry = db.query(_5G_Rollout_Sheet).filter(
                _5G_Rollout_Sheet.site_id == entry_data['site_id'],
                _5G_Rollout_Sheet.project_id == entry_data.get('project_id')
            ).first()

            if existing_entry:
                # Update existing entry
                for field, value in entry_data.items():
                    if value is not None:
                        setattr(existing_entry, field, value)
                updated_count += 1
            else:
                # Create new entry
                new_entry = _5G_Rollout_Sheet(**entry_data)
                db.add(new_entry)
                inserted_count += 1

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="bulk_upload_rollout_sheet",
            resource_type="rollout_sheet",
            resource_id="bulk",
            resource_name=file.filename,
            details=json.dumps({
                "inserted_count": inserted_count,
                "updated_count": updated_count,
                "filename": file.filename,
                "project_id": project_id
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return UploadResponse(
            inserted=inserted_count,
            updated=updated_count,
            message=f"Successfully processed CSV: {inserted_count} inserted, {updated_count} updated"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV: {str(e)}"
        )


@rolloutSheetRoute.delete("/rollout-sheet/delete-all/{project_id}")
async def delete_all_rollout_sheets_for_project(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete all 5G Rollout Sheet entries for a specific project.
    Requires 'all' permission (senior_admin only).
    """
    # Check permission - only senior_admin can delete
    if not check_admin_access(current_user, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete rollout sheet entries. Contact the Senior Admin."
        )

    try:
        # Count entries to be deleted
        entries_count = db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == project_id
        ).count()

        if entries_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No rollout sheet entries found for this project"
            )

        # Delete all entries for this project
        deleted_count = db.query(_5G_Rollout_Sheet).filter(
            _5G_Rollout_Sheet.project_id == project_id
        ).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_all_rollout_sheets",
            resource_type="rollout_sheet",
            resource_id=project_id,
            resource_name=f"Project {project_id}",
            details=json.dumps({
                "project_id": project_id,
                "deleted_count": deleted_count
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": f"Successfully deleted all rollout sheet entries for project {project_id}",
            "deleted_count": deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting rollout sheet entries: {str(e)}"
        )


# ===========================
# BOQ GENERATION
# ===========================

def get_scope_column(scope: str) -> Optional[str]:
    """
    Map a scope value from the rollout sheet to the corresponding column in OD_BOQ_Item.
    Returns the first matching column field name, or None if no match.
    Handles scopes with newlines and extra whitespace.
    """
    if not scope:
        return None

    # Normalize whitespace: replace all whitespace (including newlines) with single space
    import re
    scope_normalized = re.sub(r'\s+', ' ', scope.strip()).lower()

    # Iterate through LEVEL1_CATEGORIES to find the first matching column
    for field_name, category_name in LEVEL1_CATEGORIES.items():
        category_normalized = re.sub(r'\s+', ' ', category_name.strip()).lower()
        if category_normalized == scope_normalized:
            return field_name

    # Try partial matching if exact match fails
    for field_name, category_name in LEVEL1_CATEGORIES.items():
        category_normalized = re.sub(r'\s+', ' ', category_name.strip()).lower()
        if scope_normalized in category_normalized or category_normalized in scope_normalized:
            return field_name

    return None


@rolloutSheetRoute.get("/rollout-sheet/{entry_id}/generate-boq")
def generate_boq_for_rollout_entry(
        entry_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Generate BOQ for a specific rollout sheet entry.

    Steps:
    1. Get the rollout sheet entry by ID to retrieve the scope
    2. Map scope to the corresponding column in OD_BOQ_Item
    3. Filter OD_BOQ_Item by project_id and get rows where that column value > 0
    4. Match descriptions with CustomerPO (exact match) to get line, item_job, quantity, price
    5. Return CSV-formatted string
    """
    # Get the rollout sheet entry
    entry = db.query(_5G_Rollout_Sheet).filter(_5G_Rollout_Sheet.id == entry_id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Rollout sheet entry not found")

    # Check if user has access to this entry's project
    if current_user.role.name != "senior_admin" and entry.project_id:
        user_access = db.query(UserProjectAccess).filter(
            UserProjectAccess.user_id == current_user.id,
            UserProjectAccess.project_id == entry.project_id
        ).first()

        if not user_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this rollout sheet entry."
            )

    # Get the scope and map it to the column
    scope = entry.scope
    if not scope:
        raise HTTPException(
            status_code=400,
            detail="This rollout entry has no scope defined. Cannot generate BOQ."
        )

    scope_column = get_scope_column(scope)
    if not scope_column:
        raise HTTPException(
            status_code=400,
            detail=f"Could not map scope '{scope}' to any BOQ column. Available scopes: {', '.join(set(LEVEL1_CATEGORIES.values()))}"
        )

    # Query OD_BOQ_Item for items with non-zero values in the scope column
    boq_items = db.query(ODBOQItem).filter(
        ODBOQItem.project_id == entry.project_id
    ).all()

    # Filter items where the scope column value is not null/zero
    filtered_items = []
    for item in boq_items:
        qty_value = getattr(item, scope_column, None)
        if qty_value is not None and qty_value != 0:
            filtered_items.append({
                'description': item.description,
                'uom': item.uom,
                'category': item.category,
                'bu': item.bu,
                'boq_qty': qty_value
            })

    if not filtered_items:
        raise HTTPException(
            status_code=404,
            detail=f"No BOQ items found with non-zero quantities for scope '{scope}' in this project."
        )

    # Get all CustomerPO items for this project for matching
    customer_po_items = db.query(CustomerPO).filter(
        CustomerPO.project_id == entry.project_id
    ).all()

    # Create a lookup dictionary by description (exact match)
    po_lookup = {}
    for po_item in customer_po_items:
        if po_item.description:
            po_lookup[po_item.description.strip()] = {
                'line': po_item.line,
                'item_job': po_item.item_job,
                'po_qty': po_item.quantity,
                'price': po_item.price
            }

    # Helper function to replace null/empty with space
    def safe_value(val):
        if val is None or val == '':
            return ' '
        return val

    # Build the result data by matching descriptions
    result_data = []
    for item in filtered_items:
        desc = item['description'].strip() if item['description'] else ' '
        po_info = po_lookup.get(desc.strip(), {})

        result_data.append({
            'Line': safe_value(po_info.get('line')),
            'Item/Job': safe_value(po_info.get('item_job')),
            'Description': safe_value(desc),
            'Category': safe_value(item['category']),
            'BU': safe_value(item['bu']),
            'UOM': safe_value(item['uom']),
            'BOQ Qty': safe_value(item['boq_qty']),
            'PO Qty': safe_value(po_info.get('po_qty')),
            'Price': safe_value(po_info.get('price'))
        })

    # Get project details for header
    project = db.query(DUProject).filter(DUProject.pid_po == entry.project_id).first()
    project_name = project.project_name if project else entry.project_id
    project_po = project.po if project else entry.project_id

    # Get current date
    from datetime import datetime
    current_date = datetime.now().strftime('%d-%b-%y')

    # Generate CSV string with metadata headers
    csv_lines = []

    # Add metadata header rows (3 rows)
    csv_lines.append(f'" "," "," "," ",DU BOQ," "," "," "," ",')
    csv_lines.append(f'BPO Number:,{project_po}," "," "," ",Date:,{current_date}," "," "')
    csv_lines.append(f'Scope Description:,{scope}," "," "," ",Site Classification,{entry.sps_category or "N/A"}," "," "')
    csv_lines.append(f'Vendor:,Nokia," "," "," ",Site ID:,{entry.site_id}," "," "')
    csv_lines.append(f'" "," "," "," "," "," "," "," "," ",') # Empty row separator

    # Add data table headers
    csv_headers = ['Line', 'Item/Job', 'Description', 'Category', 'BU', 'UOM', 'BOQ Qty', 'PO Qty', 'Price']
    csv_lines.append(','.join(csv_headers))

    # Add data rows
    for row in result_data:
        csv_row = []
        for header in csv_headers:
            value = row.get(header, ' ')
            # Convert to string and replace null/empty with space
            value_str = str(value) if value is not None else ' '
            if value_str == '' or value_str == 'None':
                value_str = ' '
            # Escape commas and quotes in values
            if ',' in value_str or '"' in value_str:
                value_str = f'"{value_str.replace(chr(34), chr(34)+chr(34))}"'
            csv_row.append(value_str)
        csv_lines.append(','.join(csv_row))

    return '\n'.join(csv_lines)
