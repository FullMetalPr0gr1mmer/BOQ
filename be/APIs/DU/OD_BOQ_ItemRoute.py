"""
OD BOQ Item Route - Full CRUD operations with pagination and admin control

Features:
- Full CRUD operations (Create, Read, Update, Delete)
- Pagination with search
- Admin control (role-based access)
- CSV upload with multi-level header parsing
- Statistics and analytics endpoints
- Category-based operations (sum, compare, filter)
- Bulk operations
"""

import json
import csv
import pandas as pd
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List

from APIs.Core import get_db, get_current_user
from Models.DU.OD_BOQ_Item import (
    ODBOQItem,
    CSV_COLUMN_MAPPING,
    LEVEL1_CATEGORIES,
    LEVEL2_DESCRIPTIONS,
    QUANTITY_FIELDS
)
import importlib
DU_Project_module = importlib.import_module("Models.DU.DU_Project")
DUProject = DU_Project_module.DUProject

from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.DU.OD_BOQ_ItemSchema import (
    CreateODBOQItem,
    UpdateODBOQItem,
    ODBOQItemOut,
    ODBOQItemPagination,
    ODBOQItemStatsResponse,
    UploadResponse,
    FilterOptions,
    CategorySumResponse,
    Level1CategorySummary,
    ColumnHeaderInfo
)

odBOQItemRoute = APIRouter(tags=["OD BOQ Items"])


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


def check_du_project_access(current_user: User, project: DUProject, db: Session, required_permission: str = "view"):
    """Check if user has access to a DU project with required permission level."""
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id == project.pid_po
    ).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_du_projects(current_user: User, db: Session):
    """Get all DU projects that the current user has access to."""
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(DUProject).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id.isnot(None)
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.DUproject_id for access in user_accesses]

    # Return projects that match those IDs
    return db.query(DUProject).filter(DUProject.pid_po.in_(accessible_project_ids)).all()


def filter_boq_by_user_access(current_user: User, query, db: Session):
    """Filter BOQ items query based on user's project access."""
    if current_user.role.name == "senior_admin":
        return query

    # Get accessible project IDs
    accessible_projects = get_user_accessible_du_projects(current_user, db)
    accessible_project_ids = [project.pid_po for project in accessible_projects]

    if not accessible_project_ids:
        # User has no project access, return empty query
        return query.filter(ODBOQItem.id == -1)

    # Filter items by accessible projects
    return query.filter(ODBOQItem.project_id.in_(accessible_project_ids))


# ===========================
# STATISTICS ENDPOINTS (before parameterized routes)
# ===========================

@odBOQItemRoute.get("/boq-items/stats", response_model=ODBOQItemStatsResponse)
def get_boq_items_stats(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get BOQ item statistics."""
    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)

        total_items = query.count()

        # Count unique categories
        unique_categories = query.with_entities(func.count(func.distinct(ODBOQItem.category))).scalar() or 0
        unique_bus = query.with_entities(func.count(func.distinct(ODBOQItem.bu))).scalar() or 0

        # Sum totals for key categories
        total_new_sran = query.with_entities(func.sum(ODBOQItem.new_sran)).scalar() or 0
        total_5g = query.with_entities(
            func.sum(ODBOQItem.new_5g_n78) +
            func.sum(ODBOQItem.exp_5g_3cc) +
            func.sum(ODBOQItem.exp_5g_n41_reuse) +
            func.sum(ODBOQItem.exp_5g_3cc_ontop) +
            func.sum(ODBOQItem.exp_5g_band_swap)
        ).scalar() or 0

        # Sum services (where bu = 'Services')
        services_query = query.filter(ODBOQItem.bu == 'Services')
        total_services = services_query.with_entities(func.sum(ODBOQItem.total_qty)).scalar() or 0

        return ODBOQItemStatsResponse(
            total_items=total_items,
            unique_categories=unique_categories,
            unique_bus=unique_bus,
            total_new_sran=total_new_sran,
            total_5g=total_5g,
            total_services=total_services
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stats: {str(e)}"
        )


@odBOQItemRoute.get("/boq-items/filters/options", response_model=FilterOptions)
def get_filter_options(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get available filter options for BOQ items."""
    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)

        cats = [r[0] for r in query.with_entities(ODBOQItem.cat).distinct().all() if r[0]]
        bus = [r[0] for r in query.with_entities(ODBOQItem.bu).distinct().all() if r[0]]
        categories = [r[0] for r in query.with_entities(ODBOQItem.category).distinct().all() if r[0]]
        uoms = [r[0] for r in query.with_entities(ODBOQItem.uom).distinct().all() if r[0]]
        projects = [r[0] for r in query.with_entities(ODBOQItem.project_id).distinct().all() if r[0]]

        return FilterOptions(
            cats=sorted(cats),
            bus=sorted(bus),
            categories=sorted(categories),
            uoms=sorted(uoms),
            projects=sorted(projects)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving filter options: {str(e)}"
        )


@odBOQItemRoute.get("/boq-items/column-headers", response_model=List[ColumnHeaderInfo])
def get_column_headers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get column header information (Level 1 and Level 2 headers)."""
    headers = []
    for field, level1 in LEVEL1_CATEGORIES.items():
        level2 = LEVEL2_DESCRIPTIONS.get(field, '')
        headers.append(ColumnHeaderInfo(
            field_name=field,
            level1_header=level1,
            level2_header=level2,
            column_index=list(LEVEL1_CATEGORIES.keys()).index(field) + 5  # After fixed columns
        ))
    return headers


@odBOQItemRoute.get("/boq-items/category-summary", response_model=List[Level1CategorySummary])
def get_category_summary(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get summary of all Level 1 categories with totals."""
    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)

        # Get unique level 1 categories and calculate totals
        level1_totals = {}

        # SRAN totals
        sran_total = query.with_entities(func.sum(ODBOQItem.new_sran)).scalar() or 0
        level1_totals['New SRAN'] = {'total': sran_total, 'count': 1}

        # SRAN Expansion totals
        sran_exp_total = query.with_entities(
            func.sum(ODBOQItem.sran_exp_1cc_l800) +
            func.sum(ODBOQItem.sran_exp_1cc_l1800) +
            func.sum(ODBOQItem.sran_exp_2cc_l800_l1800) +
            func.sum(ODBOQItem.sran_exp_2cc_l1800_l2100) +
            func.sum(ODBOQItem.sran_exp_2cc_l800_l2100)
        ).scalar() or 0
        level1_totals['SRAN Expansion'] = {'total': sran_exp_total, 'count': 5}

        # New 5G-n78
        n78_total = query.with_entities(func.sum(ODBOQItem.new_5g_n78)).scalar() or 0
        level1_totals['New 5G -n78'] = {'total': n78_total, 'count': 1}

        # 5G Expansion totals
        exp_5g_total = query.with_entities(
            func.sum(ODBOQItem.exp_5g_3cc) +
            func.sum(ODBOQItem.exp_5g_n41_reuse) +
            func.sum(ODBOQItem.exp_5g_3cc_ontop) +
            func.sum(ODBOQItem.exp_5g_band_swap)
        ).scalar() or 0
        level1_totals['5G Expansion'] = {'total': exp_5g_total, 'count': 4}

        # 5G-NR FDD totals
        fdd_total = query.with_entities(
            func.sum(ODBOQItem.nr_fdd_model1_activation) +
            func.sum(ODBOQItem.nr_fdd_model1_tdra) +
            func.sum(ODBOQItem.nr_fdd_model1_2025)
        ).scalar() or 0
        level1_totals['5G-NR FDD-Model 1'] = {'total': fdd_total, 'count': 3}

        # Antenna Cutover
        ipaa_total = query.with_entities(func.sum(ODBOQItem.antenna_cutover_ipaa)).scalar() or 0
        level1_totals['Antenna Cutover (IPAA+)'] = {'total': ipaa_total, 'count': 1}

        summaries = [
            Level1CategorySummary(
                category=cat,
                total_quantity=data['total'] or 0,
                column_count=data['count']
            )
            for cat, data in level1_totals.items()
        ]

        return sorted(summaries, key=lambda x: x.total_quantity, reverse=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving category summary: {str(e)}"
        )


# ===========================
# CRUD ENDPOINTS
# ===========================

@odBOQItemRoute.post("/boq-items", response_model=ODBOQItemOut)
async def create_boq_item(
        item_data: CreateODBOQItem,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new BOQ item."""
    # Check project access if project_id is provided
    if item_data.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == item_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not check_du_project_access(current_user, project, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to add items to this project."
            )

    try:
        new_item = ODBOQItem(**item_data.dict())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_boq_item",
            resource_type="od_boq_item",
            resource_id=str(new_item.id),
            resource_name=new_item.description[:100] if new_item.description else None,
            details=json.dumps({"project_id": item_data.project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_item

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating BOQ item: {str(e)}"
        )


@odBOQItemRoute.get("/boq-items", response_model=ODBOQItemPagination)
def get_boq_items(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        search: Optional[str] = None,
        project_id: Optional[str] = None,
        cat: Optional[str] = None,
        bu: Optional[str] = None,
        category: Optional[str] = None,
        uom: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get BOQ items with pagination and search."""
    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        # Apply filters
        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)
        if cat:
            query = query.filter(ODBOQItem.cat == cat)
        if bu:
            query = query.filter(ODBOQItem.bu == bu)
        if category:
            query = query.filter(ODBOQItem.category == category)
        if uom:
            query = query.filter(ODBOQItem.uom == uom)

        # Search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    ODBOQItem.description.ilike(search_pattern),
                    ODBOQItem.cat.ilike(search_pattern),
                    ODBOQItem.bu.ilike(search_pattern),
                    ODBOQItem.category.ilike(search_pattern)
                )
            )

        total_count = query.count()
        records = query.order_by(ODBOQItem.id).offset(skip).limit(limit).all()

        return ODBOQItemPagination(records=records, total=total_count)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving BOQ items: {str(e)}"
        )


@odBOQItemRoute.get("/boq-items/{item_id}", response_model=ODBOQItemOut)
def get_boq_item(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific BOQ item by ID."""
    item = db.query(ODBOQItem).filter(ODBOQItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="BOQ item not found")

    # Check access if project is set
    if item.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == item.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this item."
            )

    return item


@odBOQItemRoute.put("/boq-items/{item_id}", response_model=ODBOQItemOut)
async def update_boq_item(
        item_id: int,
        item_data: UpdateODBOQItem,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update an existing BOQ item."""
    item = db.query(ODBOQItem).filter(ODBOQItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="BOQ item not found")

    # Check access
    if item.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == item.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this item."
            )

    try:
        update_data = item_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(item, field, value)

        db.commit()
        db.refresh(item)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_boq_item",
            resource_type="od_boq_item",
            resource_id=str(item.id),
            resource_name=item.description[:100] if item.description else None,
            details=json.dumps(update_data),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return item

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating BOQ item: {str(e)}"
        )


@odBOQItemRoute.delete("/boq-items/{item_id}")
async def delete_boq_item(
        item_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a BOQ item."""
    item = db.query(ODBOQItem).filter(ODBOQItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="BOQ item not found")

    # Check access
    if item.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == item.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this item."
            )

    try:
        item_desc = item.description[:100] if item.description else None
        project_id = item.project_id

        db.delete(item)
        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_boq_item",
            resource_type="od_boq_item",
            resource_id=str(item_id),
            resource_name=item_desc,
            details=json.dumps({"project_id": project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"BOQ item {item_id} deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting BOQ item: {str(e)}"
        )


# ===========================
# CSV UPLOAD ENDPOINT
# ===========================

@odBOQItemRoute.post("/boq-items/upload-csv", response_model=UploadResponse)
async def upload_boq_csv(
        file: UploadFile = File(...),
        project_id: str = Form(...),
        skip_header_rows: int = Form(4),  # Default: skip 4 rows (rows 0-3 are headers)
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload a CSV file with BOQ items.

    The CSV has a complex header structure:
    - Rows 0-2: Header information (categories, descriptions, site qty)
    - Row 3: Main column headers (CAT, BU, Description, etc.)
    - Row 4+: Data rows

    Parameters:
    - file: CSV file to upload
    - project_id: DU Project ID to associate items with
    - skip_header_rows: Number of header rows to skip (default: 4)
    """
    # Check project exists and user has access
    project = db.query(DUProject).filter(DUProject.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_du_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload items to this project."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()

        # Try multiple encodings to handle different CSV sources
        csv_content = None
        encodings_to_try = ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1', 'iso-8859-1']

        for encoding in encodings_to_try:
            try:
                csv_content = content.decode(encoding)
                # Replace non-breaking spaces and other problematic characters
                csv_content = csv_content.replace('\xa0', ' ')  # Non-breaking space
                csv_content = csv_content.replace('\u00a0', ' ')  # Unicode NBSP
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if csv_content is None:
            raise HTTPException(
                status_code=400,
                detail="Could not decode CSV file. Please ensure it's saved with UTF-8 encoding."
            )

        # Use pandas for more robust CSV parsing with multi-level headers
        df = pd.read_csv(StringIO(csv_content), skiprows=skip_header_rows, header=None)

        # Remove empty rows
        df = df.dropna(how='all')

        # Skip rows that look like headers (contain 'CAT', 'Site Qty', etc.)
        df = df[~df.apply(lambda row: any(
            str(val).strip().upper() in ['CAT', 'SITE QTY', 'BU', 'DESCRIPTION']
            for val in row if pd.notna(val)
        ), axis=1)]

        inserted_count = 0
        updated_count = 0
        skipped_count = 0

        for idx, row in df.iterrows():
            try:
                # Map row values to model fields
                item_data = {}

                for col_idx, field_name in CSV_COLUMN_MAPPING.items():
                    if col_idx < len(row):
                        value = row.iloc[col_idx]

                        # Handle empty values
                        if pd.isna(value) or str(value).strip() == '':
                            value = None
                        else:
                            value = str(value).strip()

                            # Convert numeric fields
                            if field_name in QUANTITY_FIELDS:
                                try:
                                    value = float(value) if value else None
                                except (ValueError, TypeError):
                                    value = None

                        item_data[field_name] = value

                # Skip rows without description or all empty
                if not item_data.get('description') and not any(
                    item_data.get(f) for f in QUANTITY_FIELDS
                ):
                    skipped_count += 1
                    continue

                # Add project_id
                item_data['project_id'] = project_id

                # Create new item
                new_item = ODBOQItem(**item_data)
                db.add(new_item)
                inserted_count += 1

            except Exception as row_error:
                print(f"Error processing row {idx}: {row_error}")
                skipped_count += 1
                continue

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="bulk_upload_boq_items",
            resource_type="od_boq_item",
            resource_id="bulk",
            resource_name=file.filename,
            details=json.dumps({
                "project_id": project_id,
                "inserted": inserted_count,
                "updated": updated_count,
                "skipped": skipped_count
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return UploadResponse(
            inserted=inserted_count,
            updated=updated_count,
            skipped=skipped_count,
            message=f"Successfully processed CSV: {inserted_count} inserted, {updated_count} updated, {skipped_count} skipped"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV: {str(e)}"
        )


# ===========================
# BULK OPERATIONS
# ===========================

@odBOQItemRoute.delete("/boq-items/delete-all/{project_id}")
async def delete_all_boq_items(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete all BOQ items for a project."""
    project = db.query(DUProject).filter(DUProject.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_du_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete items for this project."
        )

    try:
        # Count items before deletion
        item_count = db.query(ODBOQItem).filter(ODBOQItem.project_id == project_id).count()

        if item_count == 0:
            raise HTTPException(status_code=404, detail="No BOQ items found for this project")

        # Delete all items
        deleted_count = db.query(ODBOQItem).filter(
            ODBOQItem.project_id == project_id
        ).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_all_boq_items",
            resource_type="od_boq_item",
            resource_id=project_id,
            resource_name=project.project_name,
            details=json.dumps({"deleted_count": deleted_count}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "All BOQ items deleted successfully",
            "deleted_count": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting BOQ items: {str(e)}"
        )


# ===========================
# CATEGORY OPERATIONS (Multi-Level Header Support)
# ===========================

@odBOQItemRoute.get("/boq-items/sum-by-category/{category_field}")
def sum_by_category(
        category_field: str,
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Sum quantities by a specific category field.

    category_field can be one of the quantity fields:
    - new_sran, sran_exp_*, new_5g_n78, exp_5g_*, nr_fdd_*, antenna_cutover_ipaa
    """
    if category_field not in QUANTITY_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category field. Must be one of: {QUANTITY_FIELDS}"
        )

    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)

        # Get the column dynamically
        column = getattr(ODBOQItem, category_field)

        total = query.with_entities(func.sum(column)).scalar() or 0
        non_zero_count = query.filter(column > 0).count()

        return CategorySumResponse(
            category=category_field,
            level1_header=LEVEL1_CATEGORIES.get(category_field, ''),
            total=total,
            non_zero_count=non_zero_count
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating sum: {str(e)}"
        )


@odBOQItemRoute.get("/boq-items/items-with-quantity/{category_field}", response_model=ODBOQItemPagination)
def get_items_with_quantity(
        category_field: str,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all items that have non-zero quantity in a specific category."""
    if category_field not in QUANTITY_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category field. Must be one of: {QUANTITY_FIELDS}"
        )

    try:
        query = db.query(ODBOQItem)
        query = filter_boq_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(ODBOQItem.project_id == project_id)

        # Filter for non-zero values
        column = getattr(ODBOQItem, category_field)
        query = query.filter(column > 0)

        total_count = query.count()
        records = query.order_by(ODBOQItem.id).offset(skip).limit(limit).all()

        return ODBOQItemPagination(records=records, total=total_count)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving items: {str(e)}"
        )
