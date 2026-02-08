"""
OD BOQ Route - APIs for the new 3-table structure

Tables:
1. OD_BOQ_Site: Parent table (sites/projects)
2. OD_BOQ_Product: Product catalog
3. OD_BOQ_Site_Product: Junction table with quantities

Features:
- Full CRUD for sites, products, and site-products
- CSV upload with automatic population of all 3 tables
- Pagination and filtering
- Admin control and audit logging
- Site with products retrieval (join)
"""

import json
import csv
import logging
import pandas as pd
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

from APIs.Core import get_db, get_current_user
from Models.DU.OD_BOQ_Site import ODBOQSite
from Models.DU.OD_BOQ_Product import ODBOQProduct
from Models.DU.OD_BOQ_Site_Product import ODBOQSiteProduct
import importlib
DU_Project_module = importlib.import_module("Models.DU.DU_Project")
DUProject = DU_Project_module.DUProject

from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.DU.OD_BOQ_Schema import (
    ODBOQSiteCreate, ODBOQSiteUpdate, ODBOQSiteOut, ODBOQSitePagination,
    ODBOQProductCreate, ODBOQProductUpdate, ODBOQProductOut, ODBOQProductPagination,
    ODBOQSiteProductCreate, ODBOQSiteProductUpdate, ODBOQSiteProductOut,
    SiteWithProductsOut, ProductWithQuantity,
    ODBOQStatsResponse, FilterOptions, UploadResponse, BulkDeleteResponse
)

odBOQRoute = APIRouter(prefix="/od-boq", tags=["OD BOQ (New Structure)"])


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
    """
    Helper function to check if user has access to a DU project with required permission level.
    """
    # Senior admin has all permissions to all projects
    if current_user.role.name == "senior_admin":
        return True

    # Admin has all permissions but only to projects they have access to
    # Check UserProjectAccess for both admin and other roles
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id == project.pid_po
    ).first()

    if not access:
        return False

    # Admin with any access level gets full permissions (same as senior_admin) for their projects
    if current_user.role.name == "admin":
        return True

    # For non-admin users, check permission levels
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

    # For admin and other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.DUproject_id.isnot(None)
    ).all()

    if not user_accesses:
        return []

    accessible_project_ids = [access.DUproject_id for access in user_accesses]
    return db.query(DUProject).filter(DUProject.pid_po.in_(accessible_project_ids)).all()


def filter_sites_by_user_access(current_user: User, query, db: Session):
    """Filter sites query based on user's project access."""
    if current_user.role.name == "senior_admin":
        return query

    accessible_projects = get_user_accessible_du_projects(current_user, db)
    accessible_project_ids = [project.pid_po for project in accessible_projects]

    if not accessible_project_ids:
        return query.filter(ODBOQSite.site_id == "___NONE___")  # Return empty

    return query.filter(ODBOQSite.project_id.in_(accessible_project_ids))


# ===========================
# SITE CRUD ENDPOINTS
# ===========================

@odBOQRoute.post("/sites", response_model=ODBOQSiteOut)
async def create_site(
        site_data: ODBOQSiteCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new site."""
    # Check project access if project_id is provided
    if site_data.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == site_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not check_du_project_access(current_user, project, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to add sites to this project."
            )

    # Check if site_id with same subscope already exists (unique constraint)
    existing_site = db.query(ODBOQSite).filter(
        ODBOQSite.site_id == site_data.site_id,
        ODBOQSite.subscope == site_data.subscope
    ).first()
    if existing_site:
        raise HTTPException(status_code=400, detail=f"Site with ID '{site_data.site_id}' and subscope '{site_data.subscope}' already exists")

    try:
        new_site = ODBOQSite(**site_data.dict())
        db.add(new_site)
        db.commit()
        db.refresh(new_site)

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_od_boq_site",
            resource_type="od_boq_site",
            resource_id=new_site.site_id,
            resource_name=new_site.site_id,
            details=json.dumps({"project_id": site_data.project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_site

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating site: {str(e)}"
        )


@odBOQRoute.get("/sites", response_model=ODBOQSitePagination)
def get_sites(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        search: Optional[str] = None,
        project_id: Optional[str] = None,
        scope: Optional[str] = None,
        subscope: Optional[str] = None,
        region: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get sites with pagination and filters."""
    try:
        query = db.query(ODBOQSite)
        query = filter_sites_by_user_access(current_user, query, db)

        # Apply filters
        if project_id:
            query = query.filter(ODBOQSite.project_id == project_id)
        if scope:
            query = query.filter(ODBOQSite.scope == scope)
        if subscope:
            query = query.filter(ODBOQSite.subscope == subscope)
        if region:
            query = query.filter(ODBOQSite.region == region)

        # Search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    ODBOQSite.site_id.ilike(search_pattern),
                    ODBOQSite.scope.ilike(search_pattern),
                    ODBOQSite.subscope.ilike(search_pattern),
                    ODBOQSite.po_model.ilike(search_pattern)
                )
            )

        total_count = query.count()
        records = query.order_by(ODBOQSite.site_id).offset(skip).limit(limit).all()

        return ODBOQSitePagination(records=records, total=total_count)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sites: {str(e)}"
        )


@odBOQRoute.get("/sites/{id}", response_model=ODBOQSiteOut)
def get_site(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a specific site by database ID."""
    site = db.query(ODBOQSite).filter(ODBOQSite.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check access
    if site.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == site.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this site."
            )

    return site


@odBOQRoute.get("/sites/{id}/with-products", response_model=SiteWithProductsOut)
def get_site_with_products(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get a site with all its products and quantities."""
    site = db.query(ODBOQSite).filter(ODBOQSite.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check access
    if site.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == site.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "view"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this site."
            )

    # Get all site-product records for this site with product details
    site_products = db.query(
        ODBOQSiteProduct,
        ODBOQProduct
    ).join(
        ODBOQProduct, ODBOQSiteProduct.product_id == ODBOQProduct.id
    ).filter(
        ODBOQSiteProduct.site_record_id == site.id
    ).all()

    products_list = []
    total_qty_sum = 0.0
    for sp, product in site_products:
        products_list.append({
            "product_id": product.id,
            "description": product.description,
            "line_number": product.line_number,
            "code": product.code,
            "category": product.category,
            "total_po_qty": product.total_po_qty,
            "consumed_in_year": product.consumed_in_year,
            "consumed_year": product.consumed_year,
            "remaining_in_po": product.remaining_in_po,
            "qty_per_site": sp.qty_per_site
        })
        if sp.qty_per_site:
            total_qty_sum += sp.qty_per_site

    return SiteWithProductsOut(
        id=site.id,
        site_id=site.site_id,
        region=site.region,
        distance=site.distance,
        scope=site.scope,
        subscope=site.subscope,
        po_model=site.po_model,
        project_id=site.project_id,
        ac_armod_cable=site.ac_armod_cable,
        additional_cost=site.additional_cost,
        remark=site.remark,
        partner=site.partner,
        request_status=site.request_status,
        requested_date=site.requested_date,
        du_po_number=site.du_po_number,
        smp=site.smp,
        year_scope=site.year_scope,
        integration_status=site.integration_status,
        integration_date=site.integration_date,
        du_po_convention_name=site.du_po_convention_name,
        po_year_issuance=site.po_year_issuance,
        products=products_list,
        total_qty_sum=total_qty_sum
    )


@odBOQRoute.put("/sites/{id}", response_model=ODBOQSiteOut)
async def update_site(
        id: int,
        site_data: ODBOQSiteUpdate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update a site."""
    site = db.query(ODBOQSite).filter(ODBOQSite.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check access
    if site.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == site.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "edit"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to update this site."
            )

    try:
        update_data = site_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(site, field, value)

        db.commit()
        db.refresh(site)

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_od_boq_site",
            resource_type="od_boq_site",
            resource_id=str(site.id),
            resource_name=f"{site.site_id} ({site.subscope})",
            details=json.dumps(update_data),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return site

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating site: {str(e)}"
        )


@odBOQRoute.delete("/sites/{id}")
async def delete_site(
        id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a site and all its site-product records."""
    site = db.query(ODBOQSite).filter(ODBOQSite.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Check access
    if site.project_id:
        project = db.query(DUProject).filter(DUProject.pid_po == site.project_id).first()
        if project and not check_du_project_access(current_user, project, db, "all"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to delete this site."
            )

    try:
        project_id = site.project_id
        site_identifier = f"{site.site_id} ({site.subscope})"

        # Delete all site-product records first
        db.query(ODBOQSiteProduct).filter(ODBOQSiteProduct.site_record_id == site.id).delete(synchronize_session=False)

        # Delete the site
        db.delete(site)
        db.commit()

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_od_boq_site",
            resource_type="od_boq_site",
            resource_id=str(id),
            resource_name=site_identifier,
            details=json.dumps({"project_id": project_id}),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"Site {site_identifier} and all its products deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting site: {str(e)}"
        )


@odBOQRoute.delete("/sites/delete-all/{project_id}", response_model=BulkDeleteResponse)
async def delete_all_sites_by_project(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete all sites and their site-product records for a specific project."""
    # Check if project exists and user has access
    project = db.query(DUProject).filter(DUProject.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_du_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete sites from this project."
        )

    try:
        # Get all sites for this project
        sites = db.query(ODBOQSite).filter(ODBOQSite.project_id == project_id).all()
        site_record_ids = [site.id for site in sites]

        # Count records before deletion
        deleted_sites = len(site_record_ids)
        deleted_site_products = 0

        if site_record_ids:
            # Delete all site-product records for these sites
            deleted_site_products = db.query(ODBOQSiteProduct).filter(
                ODBOQSiteProduct.site_record_id.in_(site_record_ids)
            ).delete(synchronize_session=False)

            # Delete all sites
            db.query(ODBOQSite).filter(ODBOQSite.project_id == project_id).delete(synchronize_session=False)

        db.commit()

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="bulk_delete_od_boq_sites",
            resource_type="od_boq_site",
            resource_id=project_id,
            resource_name=project_id,
            details=json.dumps({
                "project_id": project_id,
                "deleted_sites": deleted_sites,
                "deleted_site_products": deleted_site_products
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return BulkDeleteResponse(
            deleted_sites=deleted_sites,
            deleted_site_products=deleted_site_products,
            message=f"Successfully deleted {deleted_sites} sites and {deleted_site_products} site-product records for project {project_id}"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting sites: {str(e)}"
        )


# ===========================
# PRODUCT CRUD ENDPOINTS
# ===========================

@odBOQRoute.post("/products", response_model=ODBOQProductOut)
async def create_product(
        product_data: ODBOQProductCreate,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Create a new product."""
    try:
        new_product = ODBOQProduct(**product_data.dict())
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_od_boq_product",
            resource_type="od_boq_product",
            resource_id=str(new_product.id),
            resource_name=new_product.description[:100] if new_product.description else None,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_product

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating product: {str(e)}"
        )


@odBOQRoute.get("/products", response_model=ODBOQProductPagination)
def get_products(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        search: Optional[str] = None,
        category: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get products with pagination and filters."""
    try:
        query = db.query(ODBOQProduct)

        # Apply filters
        if category:
            query = query.filter(ODBOQProduct.category == category)

        # Search
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    ODBOQProduct.description.ilike(search_pattern),
                    ODBOQProduct.code.ilike(search_pattern),
                    ODBOQProduct.line_number.ilike(search_pattern)
                )
            )

        total_count = query.count()
        records = query.order_by(ODBOQProduct.id).offset(skip).limit(limit).all()

        return ODBOQProductPagination(records=records, total=total_count)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )


# ===========================
# STATISTICS & FILTER ENDPOINTS
# ===========================

@odBOQRoute.get("/stats", response_model=ODBOQStatsResponse)
def get_stats(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get overall statistics."""
    try:
        site_query = db.query(ODBOQSite)
        site_query = filter_sites_by_user_access(current_user, site_query, db)

        if project_id:
            site_query = site_query.filter(ODBOQSite.project_id == project_id)

        total_sites = site_query.count()
        total_products = db.query(ODBOQProduct).count()
        total_site_products = db.query(ODBOQSiteProduct).count()

        unique_scopes = site_query.with_entities(func.count(func.distinct(ODBOQSite.scope))).scalar() or 0
        unique_subscopes = site_query.with_entities(func.count(func.distinct(ODBOQSite.subscope))).scalar() or 0
        unique_categories = db.query(ODBOQProduct).with_entities(func.count(func.distinct(ODBOQProduct.category))).scalar() or 0

        return ODBOQStatsResponse(
            total_sites=total_sites,
            total_products=total_products,
            total_site_products=total_site_products,
            unique_scopes=unique_scopes,
            unique_subscopes=unique_subscopes,
            unique_categories=unique_categories
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stats: {str(e)}"
        )


@odBOQRoute.get("/filters/options", response_model=FilterOptions)
def get_filter_options(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get available filter options."""
    try:
        site_query = db.query(ODBOQSite)
        site_query = filter_sites_by_user_access(current_user, site_query, db)

        if project_id:
            site_query = site_query.filter(ODBOQSite.project_id == project_id)

        regions = [r[0] for r in site_query.with_entities(ODBOQSite.region).distinct().all() if r[0]]
        scopes = [r[0] for r in site_query.with_entities(ODBOQSite.scope).distinct().all() if r[0]]
        subscopes = [r[0] for r in site_query.with_entities(ODBOQSite.subscope).distinct().all() if r[0]]
        categories = [r[0] for r in db.query(ODBOQProduct).with_entities(ODBOQProduct.category).distinct().all() if r[0]]
        projects = [r[0] for r in site_query.with_entities(ODBOQSite.project_id).distinct().all() if r[0]]

        return FilterOptions(
            regions=sorted(regions),
            scopes=sorted(scopes),
            subscopes=sorted(subscopes),
            categories=sorted(categories),
            projects=sorted(projects)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving filter options: {str(e)}"
        )


# ===========================
# CSV UPLOAD ENDPOINT (Populates all 3 tables)
# ===========================

@odBOQRoute.post("/upload-csv", response_model=UploadResponse)
async def upload_csv(
        file: UploadFile = File(...),
        project_id: str = Form(...),
        consumed_year: int = Form(2026),
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload CSV file and populate all 3 tables:
    - Sites (rows 8+, columns A-F + metadata columns)
    - Products (rows 1-5, columns 7 onwards) - consumed_in_year and remaining_in_po auto-calculated
    - Site-Products (junction with quantities)

    Changes:
    - consumed_in_year: Auto-calculated as SUM of all site quantities for each product
    - remaining_in_po: Auto-calculated as total_po_qty - consumed_in_year
    - Same site_id can exist with different subscope (unique constraint on site_id + subscope)
    - Sum column: Calculated automatically, not read from CSV
    - New site metadata: AC ARMOD Cable, Additional Cost, Remark, Partner, Request Status, etc.
    """
    logger.info(f"User {current_user.username} uploading OD BOQ CSV: {file.filename} for project {project_id}, consumed_year: {consumed_year}")

    # Check project access
    project = db.query(DUProject).filter(DUProject.pid_po == project_id).first()
    if not project:
        logger.warning(f"OD BOQ CSV upload attempted for non-existent project: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_du_project_access(current_user, project, db, "edit"):
        logger.warning(f"User {current_user.username} denied permission to upload OD BOQ for project {project_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload to this project."
        )

    if not file.filename.endswith('.csv'):
        logger.warning(f"Invalid file type uploaded for OD BOQ: {file.filename}")
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()

        # Try different encodings
        csv_content = None
        for encoding in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
            try:
                csv_content = content.decode(encoding)
                csv_content = csv_content.replace('\xa0', ' ')
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if csv_content is None:
            raise HTTPException(status_code=400, detail="Could not decode CSV file")

        # Read CSV
        df = pd.read_csv(StringIO(csv_content), header=None)

        # Extract product headers (rows 1-5, starting from column 7)
        # Row 6 (consumed_in_year) is SKIPPED - will be auto-calculated
        descriptions = df.iloc[0, 7:].tolist()
        line_numbers = df.iloc[1, 7:].tolist()
        codes = df.iloc[2, 7:].tolist()
        categories = df.iloc[3, 7:].tolist()
        total_pos = df.iloc[4, 7:].tolist()
        # Row 5 (index 5) is consumed in year - SKIP
        # Row 6 (index 6) is remaining in PO - SKIP

        # Helper function to safely extract and clean string values from lists
        def clean_value(lst, idx):
            """Extract value from list, return cleaned string or None."""
            if idx < len(lst) and not pd.isna(lst[idx]):
                val = str(lst[idx]).strip()
                return val if val else None
            return None

        # Create/update products (WITHOUT consumed_in_year and remaining_in_po)
        products_inserted = 0
        products_updated = 0
        product_id_map = {}  # Maps column index to product ID

        for idx, desc in enumerate(descriptions):
            # Skip columns without description OR without #Line number (validates product column)
            description = clean_value(descriptions, idx)
            line_number = clean_value(line_numbers, idx)

            if not description or not line_number:
                continue

            # Extract other product fields
            code = clean_value(codes, idx)
            category = clean_value(categories, idx)
            total_po_qty = float(total_pos[idx]) if not pd.isna(total_pos[idx]) and str(total_pos[idx]).strip() else None

            # Check if product exists by code (upsert logic)
            existing_product = db.query(ODBOQProduct).filter(ODBOQProduct.code == code).first() if code else None

            if existing_product:
                # Update existing product (WITHOUT consumed_in_year and remaining_in_po)
                existing_product.description = description
                existing_product.line_number = line_number
                existing_product.category = category
                existing_product.total_po_qty = total_po_qty
                existing_product.consumed_year = consumed_year
                # consumed_in_year and remaining_in_po will be calculated later
                product_id_map[idx] = existing_product.id
                products_updated += 1
            else:
                # Create new product (WITHOUT consumed_in_year and remaining_in_po)
                new_product = ODBOQProduct(
                    description=description,
                    line_number=line_number,
                    code=code,
                    category=category,
                    total_po_qty=total_po_qty,
                    consumed_year=consumed_year,
                    consumed_in_year=0,  # Will be calculated later
                    remaining_in_po=0  # Will be calculated later
                )
                db.add(new_product)
                db.flush()  # Get the ID without committing
                product_id_map[idx] = new_product.id
                products_inserted += 1

        # Determine number of product columns
        num_product_cols = len(product_id_map)

        # Calculate metadata column indices (after products and Sum column)
        # Structure: [Region, Distance, Scope, Subscope, Site ID, Model] + [Products...] + [Sum] + [Metadata...]
        metadata_start_col = 7 + num_product_cols + 1  # +1 for Sum column

        # Process site rows (row 8 onwards, which is index 7)
        sites_inserted = 0
        sites_updated = 0
        site_products_inserted = 0
        skipped = 0
        site_record_id_map = {}  # Maps (site_id, subscope) to database record ID

        # Helper function to safely extract cell value
        def safe_extract(row, col_idx):
            """Extract and clean cell value, return None if empty/invalid."""
            if col_idx < len(row) and not pd.isna(row.iloc[col_idx]):
                val = str(row.iloc[col_idx]).strip()
                return val if val else None
            return None

        for row_idx in range(7, len(df)):
            row = df.iloc[row_idx]

            # Extract site basic data (columns 0-5)
            region = safe_extract(row, 0)
            distance = safe_extract(row, 1)
            scope = safe_extract(row, 2)
            subscope = safe_extract(row, 3)
            site_id = safe_extract(row, 4)
            po_model = safe_extract(row, 5)

            # Skip if no site_id
            if not site_id or site_id == '':
                skipped += 1
                continue

            # Extract metadata columns (after products and Sum column) - 13 fields
            metadata_values = [safe_extract(row, metadata_start_col + i) for i in range(13)]
            (ac_armod_cable, additional_cost, remark, partner, request_status,
             requested_date, du_po_number, smp, year_scope, integration_status,
             integration_date, du_po_convention_name, po_year_issuance) = metadata_values

            # Check for existing site with same site_id and subscope
            existing_site = db.query(ODBOQSite).filter(
                ODBOQSite.site_id == site_id,
                ODBOQSite.subscope == subscope
            ).first()

            if existing_site:
                # Update existing site
                existing_site.region = region
                existing_site.distance = distance
                existing_site.scope = scope
                existing_site.po_model = po_model
                existing_site.project_id = project_id
                existing_site.ac_armod_cable = ac_armod_cable
                existing_site.additional_cost = additional_cost
                existing_site.remark = remark
                existing_site.partner = partner
                existing_site.request_status = request_status
                existing_site.requested_date = requested_date
                existing_site.du_po_number = du_po_number
                existing_site.smp = smp
                existing_site.year_scope = year_scope
                existing_site.integration_status = integration_status
                existing_site.integration_date = integration_date
                existing_site.du_po_convention_name = du_po_convention_name
                existing_site.po_year_issuance = po_year_issuance
                site_record_id_map[(site_id, subscope)] = existing_site.id
                sites_updated += 1
            else:
                # Create new site
                new_site = ODBOQSite(
                    site_id=site_id,
                    region=region,
                    distance=distance,
                    scope=scope,
                    subscope=subscope,
                    po_model=po_model,
                    project_id=project_id,
                    ac_armod_cable=ac_armod_cable,
                    additional_cost=additional_cost,
                    remark=remark,
                    partner=partner,
                    request_status=request_status,
                    requested_date=requested_date,
                    du_po_number=du_po_number,
                    smp=smp,
                    year_scope=year_scope,
                    integration_status=integration_status,
                    integration_date=integration_date,
                    du_po_convention_name=du_po_convention_name,
                    po_year_issuance=po_year_issuance
                )
                db.add(new_site)
                db.flush()  # Get the ID
                site_record_id_map[(site_id, subscope)] = new_site.id
                sites_inserted += 1

            # Get the site record ID for this site
            current_site_record_id = site_record_id_map[(site_id, subscope)]

            # Create site-product records (columns 7 to 7+num_product_cols-1)
            for col_idx, product_id in product_id_map.items():
                qty_value = row.iloc[7 + col_idx]
                qty = float(qty_value) if not pd.isna(qty_value) and str(qty_value).strip() != '' else None

                # Create or update site-product record
                existing_sp = db.query(ODBOQSiteProduct).filter(
                    ODBOQSiteProduct.site_record_id == current_site_record_id,
                    ODBOQSiteProduct.product_id == product_id
                ).first()

                if existing_sp:
                    existing_sp.qty_per_site = qty
                else:
                    new_sp = ODBOQSiteProduct(
                        site_record_id=current_site_record_id,
                        product_id=product_id,
                        qty_per_site=qty
                    )
                    db.add(new_sp)
                    site_products_inserted += 1

        # Flush to ensure all site-products are in the database
        db.flush()

        # Now calculate consumed_in_year and remaining_in_po for each product
        for product_id in set(product_id_map.values()):
            product = db.query(ODBOQProduct).filter(ODBOQProduct.id == product_id).first()
            if product:
                # Calculate consumed_in_year as SUM of all site quantities for this product
                total_consumed = db.query(func.sum(ODBOQSiteProduct.qty_per_site)).filter(
                    ODBOQSiteProduct.product_id == product_id,
                    ODBOQSiteProduct.qty_per_site.isnot(None)
                ).scalar() or 0.0

                product.consumed_in_year = total_consumed

                # Calculate remaining_in_po as total_po_qty - consumed_in_year
                if product.total_po_qty is not None:
                    product.remaining_in_po = product.total_po_qty - total_consumed
                else:
                    product.remaining_in_po = -total_consumed  # Negative if no total_po_qty

        db.commit()

        logger.info(f"OD BOQ CSV upload completed: {sites_inserted} sites inserted, {sites_updated} updated, {products_inserted} products inserted, {products_updated} updated, {site_products_inserted} site-products inserted for project {project_id}")

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="bulk_upload_od_boq",
            resource_type="od_boq_upload",
            resource_id="bulk",
            resource_name=file.filename,
            details=json.dumps({
                "project_id": project_id,
                "sites_inserted": sites_inserted,
                "sites_updated": sites_updated,
                "products_inserted": products_inserted,
                "products_updated": products_updated,
                "site_products_inserted": site_products_inserted
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return UploadResponse(
            sites_inserted=sites_inserted,
            sites_updated=sites_updated,
            products_inserted=products_inserted,
            products_updated=products_updated,
            site_products_inserted=site_products_inserted,
            skipped=skipped,
            message=f"Successfully processed CSV: {sites_inserted} sites inserted, {products_inserted} products inserted"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing OD BOQ CSV for project {project_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV: {str(e)}"
        )
