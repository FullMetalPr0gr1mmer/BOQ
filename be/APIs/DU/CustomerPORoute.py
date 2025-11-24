"""
Customer PO Route - Full CRUD operations with pagination and admin control

Features:
- Full CRUD operations (Create, Read, Update, Delete)
- Pagination with search
- Admin control (role-based access)
- CSV upload with header parsing
- Statistics and analytics endpoints
- Category-based operations
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
from Models.DU.CustomerPO import (
    CustomerPO,
    CSV_COLUMN_MAPPING,
    COLUMN_HEADERS,
    NUMERIC_FIELDS,
    STRING_FIELDS
)
import importlib
DU_Project_module = importlib.import_module("Models.DU.DU_Project")
DUProject = DU_Project_module.DUProject

from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.DU.CustomerPOSchema import (
    CreateCustomerPO,
    UpdateCustomerPO,
    CustomerPOOut,
    CustomerPOPagination,
    CustomerPOStatsResponse,
    UploadResponse,
    FilterOptions,
    ColumnHeaderInfo,
    CategorySummary
)

customerPORoute = APIRouter(tags=["Customer PO"])


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


def filter_customer_po_by_user_access(current_user: User, query, db: Session):
    """Filter Customer PO items query based on user's project access."""
    if current_user.role.name == "senior_admin":
        return query

    # Get accessible project IDs
    accessible_projects = get_user_accessible_du_projects(current_user, db)
    accessible_project_ids = [project.pid_po for project in accessible_projects]

    if not accessible_project_ids:
        # User has no project access, return empty query
        return query.filter(CustomerPO.id == -1)

    # Filter items by accessible projects
    return query.filter(CustomerPO.project_id.in_(accessible_project_ids))


# ===========================
# STATISTICS ENDPOINTS (before parameterized routes)
# ===========================

@customerPORoute.get("/customer-po/stats", response_model=CustomerPOStatsResponse)
def get_customer_po_stats(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get Customer PO item statistics."""
    try:
        query = db.query(CustomerPO)
        query = filter_customer_po_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(CustomerPO.project_id == project_id)

        total_items = query.count()

        # Count unique categories
        unique_categories = query.with_entities(func.count(func.distinct(CustomerPO.cat))).scalar() or 0
        unique_statuses = query.with_entities(func.count(func.distinct(CustomerPO.status))).scalar() or 0

        # Sum totals
        total_quantity = query.with_entities(func.sum(CustomerPO.quantity)).scalar() or 0
        total_amount = query.with_entities(func.sum(CustomerPO.amount)).scalar() or 0

        return CustomerPOStatsResponse(
            total_items=total_items,
            unique_categories=unique_categories,
            total_quantity=total_quantity,
            total_amount=total_amount,
            unique_statuses=unique_statuses
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stats: {str(e)}"
        )


@customerPORoute.get("/customer-po/filters/options", response_model=FilterOptions)
def get_filter_options(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get available filter options for Customer PO items."""
    try:
        query = db.query(CustomerPO)
        query = filter_customer_po_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(CustomerPO.project_id == project_id)

        cats = [r[0] for r in query.with_entities(CustomerPO.cat).distinct().all() if r[0]]
        statuses = [r[0] for r in query.with_entities(CustomerPO.status).distinct().all() if r[0]]
        uoms = [r[0] for r in query.with_entities(CustomerPO.uom).distinct().all() if r[0]]
        projects = [r[0] for r in query.with_entities(CustomerPO.project_id).distinct().all() if r[0]]

        return FilterOptions(
            cats=sorted(cats),
            statuses=sorted(statuses),
            uoms=sorted(uoms),
            projects=sorted(projects)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving filter options: {str(e)}"
        )


@customerPORoute.get("/customer-po/column-headers", response_model=List[ColumnHeaderInfo])
def get_column_headers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get column header information."""
    headers = []
    for field, header in COLUMN_HEADERS.items():
        col_index = next((k for k, v in CSV_COLUMN_MAPPING.items() if v == field), -1)
        headers.append(ColumnHeaderInfo(
            field_name=field,
            header=header,
            column_index=col_index
        ))
    return headers


@customerPORoute.get("/customer-po/category-summary", response_model=List[CategorySummary])
def get_category_summary(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get summary of all categories with totals."""
    try:
        query = db.query(CustomerPO)
        query = filter_customer_po_by_user_access(current_user, query, db)

        if project_id:
            query = query.filter(CustomerPO.project_id == project_id)

        # Group by category
        results = query.with_entities(
            CustomerPO.cat,
            func.count(CustomerPO.id),
            func.sum(CustomerPO.quantity),
            func.sum(CustomerPO.amount)
        ).group_by(CustomerPO.cat).all()

        summaries = [
            CategorySummary(
                category=cat or 'Unknown',
                item_count=count,
                total_quantity=qty,
                total_amount=amt
            )
            for cat, count, qty, amt in results
        ]

        return sorted(summaries, key=lambda x: x.total_amount or 0, reverse=True)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving category summary: {str(e)}"
        )


# ===========================
# CRUD ENDPOINTS
# ===========================

@customerPORoute.post("/customer-po", response_model=CustomerPOOut)
async def create_customer_po(
        item_data: CreateCustomerPO,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new Customer PO item."""
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
        new_item = CustomerPO(**item_data.dict())
        db.add(new_item)
        db.commit()
        db.refresh(new_item)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_customer_po",
            resource_type="customer_po",
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
            detail=f"Error creating Customer PO item: {str(e)}"
        )


@customerPORoute.get("/customer-po", response_model=CustomerPOPagination)
def get_customer_po_items(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        search: Optional[str] = None,
        project_id: Optional[str] = None,
        cat: Optional[str] = None,
        status_filter: Optional[str] = Query(None, alias="status"),
        uom: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get Customer PO items with pagination and search."""
    try:
        query = db.query(CustomerPO)
        query = filter_customer_po_by_user_access(current_user, query, db)

        # Apply filters
        if project_id:
            query = query.filter(CustomerPO.project_id == project_id)
        if cat:
            query = query.filter(CustomerPO.cat == cat)
        if status_filter:
            query = query.filter(CustomerPO.status == status_filter)
        if uom:
            query = query.filter(CustomerPO.uom == uom)

        # Search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    CustomerPO.description.ilike(search_pattern),
                    CustomerPO.cat.ilike(search_pattern),
                    CustomerPO.item_job.ilike(search_pattern),
                    CustomerPO.supplier_item.ilike(search_pattern)
                )
            )

        total_count = query.count()
        records = query.order_by(CustomerPO.line, CustomerPO.id).offset(skip).limit(limit).all()

        return CustomerPOPagination(records=records, total=total_count)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving Customer PO items: {str(e)}"
        )


@customerPORoute.get("/customer-po/{item_id}", response_model=CustomerPOOut)
def get_customer_po_item(
        item_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific Customer PO item by ID."""
    item = db.query(CustomerPO).filter(CustomerPO.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Customer PO item not found")

    # Check access if project is set
    if item.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == item.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this item."
            )

    return item


@customerPORoute.put("/customer-po/{item_id}", response_model=CustomerPOOut)
async def update_customer_po_item(
        item_id: int,
        item_data: UpdateCustomerPO,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update an existing Customer PO item."""
    item = db.query(CustomerPO).filter(CustomerPO.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Customer PO item not found")

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
            action="update_customer_po",
            resource_type="customer_po",
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
            detail=f"Error updating Customer PO item: {str(e)}"
        )


@customerPORoute.delete("/customer-po/{item_id}")
async def delete_customer_po_item(
        item_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a Customer PO item."""
    item = db.query(CustomerPO).filter(CustomerPO.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Customer PO item not found")

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
            action="delete_customer_po",
            resource_type="customer_po",
            resource_id=str(item_id),
            resource_name=item_desc,
            details=json.dumps({"project_id": project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"Customer PO item {item_id} deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting Customer PO item: {str(e)}"
        )


# ===========================
# CSV UPLOAD ENDPOINT
# ===========================

@customerPORoute.post("/customer-po/upload-csv", response_model=UploadResponse)
async def upload_customer_po_csv(
        file: UploadFile = File(...),
        project_id: str = Form(...),
        skip_header_rows: int = Form(4),  # Default: skip 4 rows (rows 0-3 are headers, row 4 is column headers)
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload a CSV file with Customer PO items.

    The CSV has a header structure:
    - Rows 0-1: Header info (Supplier, Order Date, etc.)
    - Row 4: Column headers (Line, CAT, Item/Job, etc.)
    - Row 5+: Data rows

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

        # Use pandas for more robust CSV parsing
        df = pd.read_csv(StringIO(csv_content), skiprows=skip_header_rows, header=None)

        # Remove empty rows
        df = df.dropna(how='all')

        # Skip rows that look like headers (contain 'CAT', 'Line', etc.)
        df = df[~df.apply(lambda row: any(
            str(val).strip().upper() in ['CAT', 'LINE', 'ITEM/JOB', 'DESCRIPTION', 'UOM']
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
                            if field_name in NUMERIC_FIELDS:
                                try:
                                    # Handle line as integer
                                    if field_name == 'line':
                                        value = int(float(value)) if value else None
                                    else:
                                        value = float(value) if value else None
                                except (ValueError, TypeError):
                                    value = None

                        item_data[field_name] = value

                # Skip rows without description or empty line
                if not item_data.get('description') and not item_data.get('line'):
                    skipped_count += 1
                    continue

                # Add project_id
                item_data['project_id'] = project_id

                # Create new item
                new_item = CustomerPO(**item_data)
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
            action="bulk_upload_customer_po",
            resource_type="customer_po",
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

@customerPORoute.delete("/customer-po/delete-all/{project_id}")
async def delete_all_customer_po_items(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete all Customer PO items for a project."""
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
        item_count = db.query(CustomerPO).filter(CustomerPO.project_id == project_id).count()

        if item_count == 0:
            raise HTTPException(status_code=404, detail="No Customer PO items found for this project")

        # Delete all items
        deleted_count = db.query(CustomerPO).filter(
            CustomerPO.project_id == project_id
        ).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_all_customer_po",
            resource_type="customer_po",
            resource_id=project_id,
            resource_name=project.project_name,
            details=json.dumps({"deleted_count": deleted_count}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "All Customer PO items deleted successfully",
            "deleted_count": deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting Customer PO items: {str(e)}"
        )
