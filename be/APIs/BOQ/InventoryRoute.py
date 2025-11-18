# routes/inventoryRoute.py
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status, Request, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
import csv
from io import StringIO

from APIs.Core import get_db, get_current_user
from Models.BOQ.Inventory import Inventory
from Models.BOQ.Site import Site
from Models.BOQ.Project import Project
from Models.Admin.User import User, UserProjectAccess
from Models.Admin.AuditLog import AuditLog
from Schemas.BOQ.InventoySchema import CreateInventory, InventoryOut, InventoryPagination, SitesResponse, \
    UploadResponse, SiteOut, AddSite

inventoryRoute = APIRouter(tags=["Inventory/Sites"])


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


def check_project_access(current_user: User, project: Project, db: Session, required_permission: str = "view"):
    """
    Helper function to check if user has access to a project with required permission level.

    Args:
        current_user: The current user
        project: The project to check access for
        db: Database session
        required_permission: Required permission level ("view", "edit", "all")

    Returns:
        bool: True if user has access, False otherwise
    """
    # Senior admin has all permissions
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.project_id == project.pid_po
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


def get_user_accessible_projects(current_user: User, db: Session):
    """
    Get all projects that the current user has access to.

    Args:
        current_user: The current user
        db: Database session

    Returns:
        List[Project]: List of accessible projects
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return db.query(Project).all()

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.project_id for access in user_accesses]

    # Return projects that match those IDs
    return db.query(Project).filter(Project.pid_po.in_(accessible_project_ids)).all()


def check_site_access(current_user: User, site: Site, db: Session, required_permission: str = "view"):
    """
    Check if user has access to a site based on project access.
    """
    # Get the project for this site
    project = db.query(Project).filter(Project.pid_po == site.project_id).first()
    if not project:
        return False

    return check_project_access(current_user, project, db, required_permission)


def filter_sites_by_user_access(current_user: User, query, db: Session):
    """
    Filter sites query based on user's project access.
    """
    if current_user.role.name == "senior_admin":
        return query

    # Get accessible project IDs
    accessible_projects = get_user_accessible_projects(current_user, db)
    accessible_project_ids = [project.pid_po for project in accessible_projects]

    if not accessible_project_ids:
        # User has no project access, return empty query
        return query.filter(Site.id == -1)  # This will return no results

    # Filter sites by accessible projects
    return query.filter(Site.project_id.in_(accessible_project_ids))


def filter_inventory_by_user_access(current_user: User, query, db: Session):
    """
    Filter inventory query based on user's project access through sites.
    """
    if current_user.role.name == "senior_admin":
        return query

    # Get accessible project IDs
    accessible_projects = get_user_accessible_projects(current_user, db)
    accessible_project_ids = [project.pid_po for project in accessible_projects]

    if not accessible_project_ids:
        # User has no project access, return empty query
        return query.filter(Inventory.id == -1)  # This will return no results


    # Filter inventory by accessible sites
    return query.filter(Inventory.pid_po.in_(accessible_project_ids))


# ----------------------------
# SITE CRUD with Pagination & Search
# ----------------------------

@inventoryRoute.post("/add-site", response_model=AddSite)
async def add_site(
        site_data: AddSite,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Adds a new site to the database.
    Only users with 'edit' or 'all' permission on the project can add sites.
    """
    # Check if project exists
    project = db.query(Project).filter(Project.pid_po == site_data.pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need edit permission to add sites
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to add sites to this project. Contact the Senior Admin."
        )

    existing_site = db.query(Site).filter(Site.site_id == site_data.site_id).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Site with this ID already exists")

    try:
        new_site = Site(
            site_id=site_data.site_id,
            site_name=site_data.site_name,
            project_id=site_data.pid_po
        )
        db.add(new_site)
        db.commit()
        db.refresh(new_site)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_site",
            resource_type="site",
            resource_id=new_site.site_id,
            resource_name=new_site.site_name,
            details=json.dumps({
                "project_id": site_data.pid_po,
                "site_id": site_data.site_id,
                "site_name": site_data.site_name
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return AddSite(
            site_id=new_site.site_id,
            site_name=new_site.site_name,
            pid_po=new_site.project_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating site: {str(e)}"
        )


@inventoryRoute.get("/sites/stats")
def get_sites_stats(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get site statistics (total sites, unique projects count).
    IMPORTANT: This must be defined BEFORE /sites endpoint to avoid route conflicts.
    """
    try:
        from sqlalchemy import func

        query = db.query(Site)

        # Filter by user access
        query = filter_sites_by_user_access(current_user, query, db)

        total_sites = query.count()

        # Count unique projects more efficiently
        unique_projects_query = query.with_entities(func.count(func.distinct(Site.project_id)))
        total_projects = unique_projects_query.scalar()

        return {
            "total_sites": total_sites,
            "total_projects": total_projects
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving site stats: {str(e)}"
        )


@inventoryRoute.get("/sites", response_model=SitesResponse)
def get_sites_paginated(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=500),
        search: Optional[str] = Query(None),
        project_id: Optional[str] = Query(None)
):
    """
    Retrieves a paginated list of sites with optional search functionality.
    Users can only see sites from projects they have access to.
    Optionally filter by project_id.
    """
    try:
        query = db.query(Site)

        # Filter by user access
        query = filter_sites_by_user_access(current_user, query, db)

        # Filter by project if specified
        if project_id:
            query = query.filter(Site.project_id == project_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Site.site_id.ilike(search_pattern),
                    Site.site_name.ilike(search_pattern),
                    Site.project_id.ilike(search_pattern)
                )
            )

        total_count = query.count()
        sites = query.order_by(Site.site_id).offset(skip).limit(limit).all()
        records = [
            SiteOut(
                id=site.id,
                site_id=site.site_id,
                site_name=site.site_name,
                pid_po=site.project_id
            ) for site in sites
        ]

        return SitesResponse(records=records, total=total_count)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sites: {str(e)}"
        )


@inventoryRoute.put("/update-site/{id}", response_model=AddSite)
async def update_site(
        id: int,
        site_data: AddSite,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Updates the details of an existing site.
    Users need 'edit' or 'all' permission on the project.
    Note: site_id cannot be changed.
    """
    site = db.query(Site).filter(Site.id == id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Get the project for this site
    project = db.query(Project).filter(Project.pid_po == site.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Associated project not found")

    # Check project access - need edit permission
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this site. Contact the Senior Admin."
        )

    try:
        old_name = site.site_name
        site.site_name = site_data.site_name
        db.commit()
        db.refresh(site)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_site",
            resource_type="site",
            resource_id=site.site_id,
            resource_name=site.site_name,
            details=json.dumps({
                "old_name": old_name,
                "new_name": site_data.site_name,
                "project_id": site.project_id
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return AddSite(
            site_id=site.site_id,
            site_name=site.site_name,
            pid_po=site.project_id
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating site: {str(e)}"
        )


@inventoryRoute.delete("/delete-site/{site_id}")
async def delete_site(
        site_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes a site from the database.
    Users need 'all' permission on the project to delete sites.
    """
    site = db.query(Site).filter(Site.site_id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # Get the project for this site
    project = db.query(Project).filter(Project.pid_po == site.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Associated project not found")

    # Check project access - need 'all' permission for deletion
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this site. Contact the Senior Admin."
        )

    try:
        # Store data for audit log before deletion
        site_name = site.site_name
        project_id = site.project_id

        db.delete(site)
        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_site",
            resource_type="site",
            resource_id=site_id,
            resource_name=site_name,
            details=json.dumps({
                "project_id": project_id,
                "site_name": site_name
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": f"Site {site_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting site: {str(e)}"
        )


@inventoryRoute.post("/sites/upload-csv", response_model=UploadResponse)
async def upload_sites_csv(
        file: UploadFile = File(...),
        pid_po: str = Form(...),
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Uploads a CSV file and creates sites based on the link data.
    The pid_po parameter will be used for all sites in the CSV.
    Users need 'edit' or 'all' permission on the project to upload sites.
    """
    # Check if project exists
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need edit permission to add sites
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload sites for this project. Contact the Senior Admin."
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()
        csv_content = StringIO(content.decode('utf-8'))
        csv_reader = csv.reader(csv_content)

        # Skip header row if present
        first_row = next(csv_reader, None)
        if first_row and any(header.lower() in ['linkid', 'interfacename', 'siteipa', 'siteipb']
                             for header in first_row):
            # This was a header row, continue processing
            pass
        else:
            # This wasn't a header row, reset reader to include first row
            csv_content.seek(0)
            csv_reader = csv.reader(csv_content)

        inserted_count = 0
        processed_sites = set()  # To avoid duplicates

        for row in csv_reader:
            if len(row) < 4:
                continue  # Skip malformed rows

            linkid = row[0].strip()
            interface_name = row[1].strip()
            site_ipa = row[2].strip()
            site_ipb = row[3].strip()

            # Parse linkid (e.g., "JIZ0243-JIZ0169")
            if '-' not in linkid:
                continue  # Skip if linkid doesn't contain separator

            site_names = linkid.split('-')
            if len(site_names) != 2:
                continue  # Skip if not exactly 2 sites

            site_name_a = site_names[0].strip()
            site_name_b = site_names[1].strip()

            # Create or update site A
            site_a_key = (site_name_a, site_ipa)
            if site_a_key not in processed_sites:
                existing_site_a = db.query(Site).filter(Site.site_id == site_ipa).first()
                if not existing_site_a:
                    new_site_a = Site(
                        site_id=site_ipa,
                        site_name=site_name_a,
                        project_id=pid_po  # Use the form parameter for all sites
                    )
                    db.add(new_site_a)
                    inserted_count += 1
                processed_sites.add(site_a_key)

            # Create or update site B
            site_b_key = (site_name_b, site_ipb)
            if site_b_key not in processed_sites:
                existing_site_b = db.query(Site).filter(Site.site_id == site_ipb).first()
                if not existing_site_b:
                    new_site_b = Site(
                        site_id=site_ipb,
                        site_name=site_name_b,
                        project_id=pid_po  # Use the form parameter for all sites
                    )
                    db.add(new_site_b)
                    inserted_count += 1
                processed_sites.add(site_b_key)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="bulk_upload_sites",
            resource_type="site",
            resource_id="bulk",
            resource_name=file.filename,
            details=json.dumps({
                "inserted_count": inserted_count,
                "filename": file.filename
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return UploadResponse(
            inserted=inserted_count,
            message=f"Successfully processed CSV and inserted {inserted_count} new sites"
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


# Keep the legacy endpoint for backward compatibility
@inventoryRoute.get("/get-site")
def get_all_sites_legacy(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Legacy endpoint - returns all sites without pagination.
    Users can only see sites from projects they have access to.
    Use /sites for paginated results.
    """
    try:
        query = db.query(Site)
        query = filter_sites_by_user_access(current_user, query, db)
        sites = query.all()

        return [
            {
                "site_id": site.site_id,
                "site_name": site.site_name,
                "project_id": site.project_id
            } for site in sites
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sites: {str(e)}"
        )


# ----------------------------
# INVENTORY CRUD - REFACTORED
# ----------------------------

@inventoryRoute.post("/create-inventory", response_model=InventoryOut)
async def create_inventory(
        inventory_data: CreateInventory,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create inventory for a site.
    Users need 'edit' or 'all' permission on the project.
    If the site doesn't exist, it will be created automatically.
    """
    # Check if project exists (using pid_po from inventory_data)
    if not inventory_data.pid_po:
        raise HTTPException(status_code=400, detail="Project ID (pid_po) is required")

    project = db.query(Project).filter(Project.pid_po == inventory_data.pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need edit permission
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create inventory for this project. Contact the Senior Admin."
        )

    # Check if site exists, create it if it doesn't
    site = db.query(Site).filter(Site.site_id == inventory_data.site_id).first()
    if not site:
        # Auto-create the site
        site = Site(
            site_id=inventory_data.site_id,
            site_name=inventory_data.site_name,
            project_id=inventory_data.pid_po
        )
        db.add(site)
        db.flush()  # Flush to get the site ID without committing yet

    try:
        # Set pid_po from inventory data
        inventory_data_dict = inventory_data.dict()
        inventory_data_dict['pid_po'] = inventory_data.pid_po

        new_inventory = Inventory(**inventory_data_dict)
        db.add(new_inventory)
        db.commit()
        db.refresh(new_inventory)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="create_inventory",
            resource_type="inventory",
            resource_id=str(new_inventory.id),
            resource_name=f"{inventory_data.site_name} - Slot {inventory_data.slot_id}",
            details=json.dumps({
                "site_id": inventory_data.site_id,
                "site_name": inventory_data.site_name,
                "slot_id": inventory_data.slot_id,
                "port_id": inventory_data.port_id
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return new_inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating inventory: {str(e)}"
        )


@inventoryRoute.get("/inventory/stats")
def get_inventory_stats(
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get inventory statistics (total items, unique sites count).
    Optionally filter by project_id.
    """
    try:
        from sqlalchemy import func

        query = db.query(Inventory)

        # Filter by user access
        query = filter_inventory_by_user_access(current_user, query, db)

        # Filter by project if specified
        if project_id:
            query = query.filter(Inventory.pid_po == project_id)

        total_items = query.count()

        # Count unique sites more efficiently
        unique_sites_query = query.with_entities(func.count(func.distinct(Inventory.site_id)))
        unique_sites = unique_sites_query.scalar()

        return {
            "total_items": total_items,
            "unique_sites": unique_sites
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving inventory stats: {str(e)}"
        )


@inventoryRoute.get("/inventory", response_model=InventoryPagination)
def get_inventory(
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        project_id: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get inventory with pagination and search.
    Users can only see inventory from sites in projects they have access to.
    Optionally filter by project_id.
    """
    try:
        query = db.query(Inventory)

        # Filter by user access
        query = filter_inventory_by_user_access(current_user, query, db)

        # Filter by project if specified
        if project_id:
            query = query.filter(Inventory.pid_po == project_id)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Inventory.site_id.like(search_pattern),
                    Inventory.site_name.like(search_pattern)
                )
            )
        total_count = query.count()
        records = query.order_by(Inventory.id).offset(skip).limit(limit).all()
        return {"records": records, "total": total_count}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving inventory: {str(e)}"
        )


@inventoryRoute.put("/update-inventory/{inventory_id}", response_model=InventoryOut)
async def update_inventory(
        inventory_id: int,
        inventory_data: CreateInventory,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Update inventory.
    Users need 'edit' or 'all' permission on the project that contains the site.
    """
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # Get the site for this inventory
    site = db.query(Site).filter(Site.site_id == inventory.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Associated site not found")

    # Check site access (which checks project access)
    if not check_site_access(current_user, site, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this inventory. Contact the Senior Admin."
        )

    try:
        old_data = {
            "site_name": inventory.site_name,
            "slot_id": inventory.slot_id,
            "port_id": inventory.port_id,
            "status": inventory.status
        }

        for field, value in inventory_data.dict().items():
            setattr(inventory, field, value)

        # Ensure pid_po is set correctly
        inventory.pid_po = site.project_id

        db.commit()
        db.refresh(inventory)

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="update_inventory",
            resource_type="inventory",
            resource_id=str(inventory.id),
            resource_name=f"{inventory_data.site_name} - Slot {inventory_data.slot_id}",
            details=json.dumps({
                "old_data": old_data,
                "new_data": inventory_data.dict()
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return inventory
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating inventory: {str(e)}"
        )


@inventoryRoute.delete("/delete-inventory/{inventory_id}")
async def delete_inventory(
        inventory_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Delete inventory.
    Users need 'all' permission on the project that contains the site.
    """
    inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # Get the site for this inventory
    site = db.query(Site).filter(Site.site_id == inventory.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Associated site not found")

    # Check site access (which checks project access) - need 'all' permission for deletion
    if not check_site_access(current_user, site, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this inventory. Contact the Senior Admin."
        )

    try:
        # Store data for audit log before deletion
        inventory_data = {
            "site_id": inventory.site_id,
            "site_name": inventory.site_name,
            "slot_id": inventory.slot_id,
            "port_id": inventory.port_id,
            "status": inventory.status
        }

        db.delete(inventory)
        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_inventory",
            resource_type="inventory",
            resource_id=str(inventory_id),
            resource_name=f"{inventory_data['site_name']} - Slot {inventory_data['slot_id']}",
            details=json.dumps(inventory_data),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {"message": "Inventory deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting inventory: {str(e)}"
        )


# ----------------------------
# CSV UPLOAD
# ----------------------------

@inventoryRoute.post("/upload-inventory-csv")
async def upload_inventory_csv(
        file: UploadFile = File(...),
        pid_po: str = Form(...),
        request: Request = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Upload inventory CSV.
    The pid_po parameter will be used for all inventory records in the CSV.
    Users need 'edit' or 'all' permission on the project to upload inventory.
    """
    # Check if project exists
    project = db.query(Project).filter(Project.pid_po == pid_po).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need edit permission to add inventory
    if not check_project_access(current_user, project, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to upload inventory for this project. Contact the Senior Admin."
        )

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")


    content = await file.read()
    csv_reader = csv.DictReader(StringIO(content.decode("utf-8")))

    # Define a consistent mapping for CSV headers to model fields
    header_mapping = {
        'Site Id': 'site_id',
        'Site Name': 'site_name',
        'Slot Id': 'slot_id',
        'Port Id': 'port_id',
        'Status': 'status',
        'Company ID': 'company_id',
        'Mnemonic': 'mnemonic',
        'CLEI Code': 'clei_code',
        'Part No': 'part_no',
        'Software Part No': 'software_no',
        'Factory ID': 'factory_id',
        'Serial No': 'serial_no',
        'Date ID': 'date_id',
        'Manufactured Date': 'manufactured_date',
        'Customer Field': 'customer_field',
        'License Points Consumed': 'license_points_consumed',
        'Alarm Status': 'alarm_status',
        'Aggregated Alarm Status': 'Aggregated_alarm_status'
                }

    inserted_count = 0
    try:
        for row in csv_reader:
            # Prepare data using the mapping
            inventory_data = {}
            for csv_header, model_field in header_mapping.items():
                # Sanitize data and handle missing headers gracefully
                value = row.get(csv_header, '').strip()
                if not value:
                    value = None
                inventory_data[model_field] = value

            # Convert integers
            inventory_data['slot_id'] = int(inventory_data.get('slot_id') or 0)
            inventory_data['port_id'] = int(inventory_data.get('port_id') or 0)

            # Add project ID from form parameter
            inventory_data['pid_po'] = pid_po

            db_obj = Inventory(**inventory_data)
            db.add(db_obj)
            inserted_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error during CSV upload: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during CSV processing: {e}")

    return {"inserted_count": inserted_count}


@inventoryRoute.delete("/delete-all-sites/{project_id}")
async def delete_all_sites_for_project(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all sites related to a project and cascade deletes related data.
    Users need 'all' permission on the project to delete all sites.

    This will also delete data from the following tables:
    - Sites (all sites for the project)
    - Inventory (all inventory items associated with those sites)

    Returns:
    - deleted_sites: Number of sites deleted
    - deleted_inventory: Number of inventory records deleted
    - affected_tables: List of tables that had data deleted
    """
    # Get the project
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need 'all' permission for deletion
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete sites for this project. Contact the Senior Admin."
        )

    try:
        # Get count of sites for this project (for reporting)
        sites_count = db.query(Site).filter(Site.project_id == project_id).count()

        if sites_count == 0:
            raise HTTPException(status_code=404, detail="No sites found for this project")

        # Delete related inventory records by project_id
        # This avoids SQL Server's ~2100 parameter limit when using IN clause
        inventory_deleted = db.query(Inventory).filter(
            Inventory.pid_po == project_id
        ).delete(synchronize_session=False)

        # Delete all sites for this project
        sites_deleted = db.query(Site).filter(Site.project_id == project_id).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_all_sites",
            resource_type="project_sites",
            resource_id=project_id,
            resource_name=project.project_name,
            details=json.dumps({
                "project_id": project_id,
                "sites_deleted": sites_deleted,
                "inventory_deleted": inventory_deleted
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "All sites and related data deleted successfully",
            "deleted_sites": sites_deleted,
            "deleted_inventory": inventory_deleted,
            "affected_tables": ["sites", "inventory"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting sites: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete sites: {str(e)}")


@inventoryRoute.delete("/delete-all-inventory/{project_id}")
async def delete_all_inventory_for_project(
        project_id: str,
        request: Request,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Deletes all inventory records for a project.
    Users need 'all' permission on the project to delete all inventory.

    Returns:
    - deleted_inventory: Number of inventory records deleted
    - affected_tables: List of tables that had data deleted
    """
    # Get the project
    project = db.query(Project).filter(Project.pid_po == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check project access - need 'all' permission for deletion
    if not check_project_access(current_user, project, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete inventory for this project. Contact the Senior Admin."
        )

    try:
        # Get count of inventory for this project (for reporting)
        inventory_count = db.query(Inventory).filter(Inventory.pid_po == project_id).count()

        if inventory_count == 0:
            raise HTTPException(status_code=404, detail="No inventory found for this project")

        # Delete all inventory for this project
        inventory_deleted = db.query(Inventory).filter(Inventory.pid_po == project_id).delete(synchronize_session=False)

        db.commit()

        # Create audit log
        await create_audit_log(
            db=db,
            user_id=current_user.id,
            action="delete_all_inventory",
            resource_type="project_inventory",
            resource_id=project_id,
            resource_name=project.project_name,
            details=json.dumps({
                "project_id": project_id,
                "inventory_deleted": inventory_deleted
            }),
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent")
        )

        return {
            "message": "All inventory deleted successfully",
            "deleted_inventory": inventory_deleted,
            "affected_tables": ["inventory"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting inventory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete inventory: {str(e)}")