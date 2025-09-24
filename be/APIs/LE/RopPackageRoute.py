from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert, delete, select, and_, update, func
from typing import List

# --- Core Imports for Security and DB ---
from APIs.Core import get_db, get_current_user
from Models.Admin.User import User, UserProjectAccess
from Models.LE.ROPProject import ROPProject

# --- Model and Schema Imports ---
from Models.LE.RopPackages import RopPackage, rop_package_lvl1
from Models.LE.ROPLvl1 import ROPLvl1
from Models.LE.MonthlyDistribution import MonthlyDistribution
from Schemas.LE.RopPackageSchema import RopPackageCreate, RopPackageUpdate, RopPackageOut
from APIs.LE.SharedMethods import (
    auto_distribute_quantity,
    validate_distributions_within_date_range,
    generate_monthly_periods
)

RopPackageRouter = APIRouter(prefix="/rop-package", tags=["Rop Packages"])


def check_rop_project_access(
        current_user: User,
        project: str,
        db: Session,
        required_permission: str = "view"):
    if current_user.role.name == "senior_admin":
        return True

    # For other roles, check UserProjectAccess
    access = db.query(UserProjectAccess).filter(and_(
        UserProjectAccess.user_id == current_user.id,
        UserProjectAccess.Ropproject_id == project
    )).first()

    if not access:
        return False

    # Check permission levels
    permission_hierarchy = {
        "view": ["view", "edit", "all"],
        "edit": ["edit", "all"],
        "all": ["all"]
    }

    return access.permission_level in permission_hierarchy.get(required_permission, [])


def get_user_accessible_rop_projects(current_user: User, db: Session) -> List[str]:
    """
    Get all ROP projects that the current user has access to.
    """
    # Senior admin can see all projects
    if current_user.role.name == "senior_admin":
        return [p.pid_po for p in db.query(ROPProject).all()]

    # For other users, get projects they have access to
    user_accesses = db.query(UserProjectAccess).filter(
        UserProjectAccess.user_id == current_user.id
    ).all()

    if not user_accesses:
        return []

    # Get project IDs the user has access to
    accessible_project_ids = [access.Ropproject_id for access in user_accesses]
    return accessible_project_ids


def handle_monthly_distributions(package_id: int, data, db: Session):
    """Handle creation/update of monthly distributions for a package."""
    # Delete existing distributions
    db.query(MonthlyDistribution).filter(
        MonthlyDistribution.package_id == package_id
    ).delete()

    distributions_to_create = []

    # If monthly_distributions provided, use them
    if hasattr(data, 'monthly_distributions') and data.monthly_distributions:
        distributions_to_create = data.monthly_distributions
    # Otherwise, auto-distribute if we have dates and quantity
    elif (hasattr(data, 'start_date') and data.start_date and
          hasattr(data, 'end_date') and data.end_date and
          hasattr(data, 'quantity') and data.quantity):
        distributions_to_create = auto_distribute_quantity(
            data.quantity, data.start_date, data.end_date
        )

    # Create new distributions
    for dist in distributions_to_create:
        new_dist = MonthlyDistribution(
            package_id=package_id,
            year=dist.year,
            month=dist.month,
            quantity=dist.quantity
        )
        db.add(new_dist)

    db.commit()


def _to_int(val) -> int:
    try:
        # Accept strings like "3" as 3; treat None/empty as 0
        return int(val) if val is not None and str(val).strip() != "" else 0
    except Exception:
        return 0


def recompute_consumption_for_lvl1_ids(db: Session, lvl1_ids: list[str]):
    """Recalculate ROPLvl1.consumption as sum of rop_package_lvl1.total_quantity."""
    if not lvl1_ids:
        return
    sums = dict(
        db.execute(
            select(
                rop_package_lvl1.c.lvl1_id,
                func.coalesce(func.sum(rop_package_lvl1.c.total_quantity), 0)
            ).where(rop_package_lvl1.c.lvl1_id.in_(lvl1_ids))
             .group_by(rop_package_lvl1.c.lvl1_id)
        ).all()
    )
    # Update each lvl1 row
    lvl1_rows = db.query(ROPLvl1).filter(ROPLvl1.id.in_(lvl1_ids)).all()
    for row in lvl1_rows:
        row.consumption = int(sums.get(row.id, 0) or 0)
    db.commit()

# CREATE
@RopPackageRouter.post("/create", response_model=RopPackageOut)
def create_package(
        data: RopPackageCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Permission Check
    if not check_rop_project_access(current_user, data.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to create packages for this project."
        )

    # 2. Validate monthly distributions if provided
    if data.monthly_distributions and data.start_date and data.end_date:
        if not validate_distributions_within_date_range(
                data.monthly_distributions, data.start_date, data.end_date
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Some monthly distributions fall outside the package date range."
            )

    # 3. Validate Lvl1 remaining quantities before creating package
    pkg_qty = _to_int(data.quantity)
    if data.lvl1_ids and pkg_qty > 0:
        lvl1_ids = [item["id"] for item in data.lvl1_ids]
        lvl1_rows = db.query(ROPLvl1).filter(ROPLvl1.id.in_(lvl1_ids)).all()
        lvl1_by_id = {r.id: r for r in lvl1_rows}

        insufficient = []
        for item in data.lvl1_ids:
            lvl1 = lvl1_by_id.get(item["id"]) if item["id"] in lvl1_by_id else None
            if not lvl1:
                continue
            link_qty = _to_int(item.get("quantity"))
            required_total = link_qty * pkg_qty
            total_qty = _to_int(lvl1.total_quantity)
            current_consumption = _to_int(lvl1.consumption)
            remaining = total_qty - current_consumption
            if required_total > remaining:
                insufficient.append({
                    "id": lvl1.id,
                    "name": lvl1.item_name,
                    "required": required_total,
                    "available": max(0, remaining),
                    "total_quantity": total_qty,
                    "consumption": current_consumption
                })

        if insufficient:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "The Remaining quantities for the following PCIs are not sufficient",
                    "insufficient": insufficient
                }
            )

    # 4. Create package
    new_pkg = RopPackage(
        project_id=data.project_id,
        package_name=data.package_name,
        start_date=data.start_date,
        end_date=data.end_date,
        quantity=data.quantity,
        price=data.price,
        lead_time=data.lead_time,
        currency=data.currency,
    )
    db.add(new_pkg)
    db.commit()
    db.refresh(new_pkg)

    # 5. Handle monthly distributions
    handle_monthly_distributions(new_pkg.id, data, db)

    # 6. Insert lvl1 links
    if data.lvl1_ids:
        affected_lvl1_ids = []
        for item in data.lvl1_ids:
            db.execute(insert(rop_package_lvl1).values(
                package_id=new_pkg.id,
                lvl1_id=item["id"],
                quantity=_to_int(item.get("quantity")),
                total_quantity=_to_int(item.get("quantity")) * _to_int(new_pkg.quantity)
            ))
            affected_lvl1_ids.append(item["id"])
        db.commit()
        # recompute consumption for affected lvl1 ids
        recompute_consumption_for_lvl1_ids(db, affected_lvl1_ids)

    # 7. Build response
    return build_package_response(new_pkg.id, db)


# READ ALL (Filtered by user's project access)
@RopPackageRouter.get("/", response_model=List[RopPackageOut])
def get_all_packages(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Get IDs of projects the user can access
    accessible_pids = get_user_accessible_rop_projects(current_user, db)
    if not accessible_pids:
        return []

    # Query only for packages within those projects
    pkgs = db.query(RopPackage).filter(RopPackage.project_id.in_(accessible_pids)).all()

    result = []
    for pkg in pkgs:
        result.append(build_package_response(pkg.id, db))
    return result


# READ ONE
@RopPackageRouter.get("/{id}", response_model=RopPackageOut)
def get_package(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Permission Check
    if not check_rop_project_access(current_user, pkg.project_id, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this package."
        )

    return build_package_response(id, db)


# UPDATE
@RopPackageRouter.put("/update/{id}", response_model=RopPackageOut)
def update_package(
        id: int,
        data: RopPackageUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Permission Check
    if not check_rop_project_access(current_user, pkg.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this package."
        )

    # Update package fields
    update_data = data.dict(exclude_unset=True, exclude={'lvl1_ids', 'monthly_distributions'})
    for key, value in update_data.items():
        setattr(pkg, key, value)

    # Handle lvl1 updates
    if data.lvl1_ids is not None:
        db.execute(delete(rop_package_lvl1).where(rop_package_lvl1.c.package_id == id))
        affected_lvl1_ids = []
        for item in data.lvl1_ids:
            db.execute(insert(rop_package_lvl1).values(
                package_id=id,
                lvl1_id=item["id"],
                quantity=_to_int(item.get("quantity")),
                total_quantity=_to_int(item.get("quantity")) * _to_int((data.quantity if hasattr(data, 'quantity') and data.quantity is not None else pkg.quantity))
            ))
            affected_lvl1_ids.append(item["id"])
        # after commit below, we'll recompute consumption

    db.commit()
    db.refresh(pkg)

    # Handle monthly distributions if provided
    if data.monthly_distributions is not None:
        # Validate if dates are available
        if data.start_date and data.end_date:
            pkg_start = data.start_date
            pkg_end = data.end_date
        else:
            pkg_start = pkg.start_date
            pkg_end = pkg.end_date

        if data.monthly_distributions and pkg_start and pkg_end:
            if not validate_distributions_within_date_range(
                    data.monthly_distributions, pkg_start, pkg_end
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some monthly distributions fall outside the package date range."
                )

        handle_monthly_distributions(id, data, db)

    # If only package quantity changed (and lvl1 not provided), recompute total_quantity for links
    if ('quantity' in update_data) and (data.lvl1_ids is None):
        # Update using SQL expression but ensure integer math
        db.execute(
            update(rop_package_lvl1)
            .where(rop_package_lvl1.c.package_id == id)
            .values(total_quantity=rop_package_lvl1.c.quantity * _to_int(pkg.quantity))
        )
        db.commit()
        # recompute consumption for all lvl1 linked to this package
        ids = [r[0] for r in db.execute(select(rop_package_lvl1.c.lvl1_id).where(rop_package_lvl1.c.package_id == id)).all()]
        recompute_consumption_for_lvl1_ids(db, ids)

    # If lvl1_ids were updated, recompute their consumption
    if data.lvl1_ids is not None:
        recompute_consumption_for_lvl1_ids(db, affected_lvl1_ids)

    return build_package_response(id, db)


# DELETE
@RopPackageRouter.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Permission Check
    if not check_rop_project_access(current_user, pkg.project_id, db, "all"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this package."
        )

    # Capture affected lvl1 ids before deleting links via cascade
    affected_lvl1_ids = [
        r[0] for r in db.execute(
            select(rop_package_lvl1.c.lvl1_id).where(rop_package_lvl1.c.package_id == id)
        ).all()
    ]

    db.delete(pkg)
    db.commit()

    # Recompute consumption for affected lvl1s
    if affected_lvl1_ids:
        recompute_consumption_for_lvl1_ids(db, affected_lvl1_ids)


# UTILITY ENDPOINTS

@RopPackageRouter.post("/{id}/auto-distribute")
def auto_distribute_package_quantity(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Auto-distribute package quantity evenly across months between start and end dates."""
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Permission Check
    if not check_rop_project_access(current_user, pkg.project_id, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to modify this package."
        )

    if not pkg.start_date or not pkg.end_date or not pkg.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Package must have start_date, end_date, and quantity for auto-distribution."
        )

    # Generate auto-distribution
    distributions = auto_distribute_quantity(pkg.quantity, pkg.start_date, pkg.end_date)

    # Create a temporary data object for handle_monthly_distributions
    class TempData:
        def __init__(self, distributions):
            self.monthly_distributions = distributions

    handle_monthly_distributions(id, TempData(distributions), db)

    return {
        "message": "Quantity auto-distributed successfully",
        "distributions": [
            {
                "year": d.year,
                "month": d.month,
                "quantity": d.quantity
            } for d in distributions
        ]
    }


@RopPackageRouter.get("/{id}/monthly-periods")
def get_package_monthly_periods(
        id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Get all available monthly periods for a package based on its start and end dates."""
    pkg = db.query(RopPackage).filter(RopPackage.id == id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Permission Check
    if not check_rop_project_access(current_user, pkg.project_id, db, "view"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this package."
        )

    if not pkg.start_date or not pkg.end_date:
        return {"periods": [], "message": "Package must have start_date and end_date"}

    periods = generate_monthly_periods(pkg.start_date, pkg.end_date)

    return {
        "periods": [
            {
                "year": year,
                "month": month,
                "display": f"{['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month]} {year}"
            } for year, month in periods
        ],
        "total_months": len(periods)
    }


def build_package_response(package_id: int, db: Session) -> RopPackageOut:
    """Helper function to build complete package response with all relationships."""
    pkg = db.query(RopPackage).filter(RopPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    # Get lvl1 items
    lvl1_rows = db.execute(select(ROPLvl1.id, ROPLvl1.item_name, rop_package_lvl1.c.quantity)
                           .join(rop_package_lvl1, ROPLvl1.id == rop_package_lvl1.c.lvl1_id)
                           .where(rop_package_lvl1.c.package_id == package_id)).all()

    # Get monthly distributions
    monthly_dists = db.query(MonthlyDistribution).filter(
        MonthlyDistribution.package_id == package_id
    ).order_by(MonthlyDistribution.year, MonthlyDistribution.month).all()

    return RopPackageOut(
        **pkg.__dict__,
        lvl1_items=[{"id": r.id, "name": r.item_name, "quantity": r.quantity} for r in lvl1_rows],
        monthly_distributions=[
            {
                "id": d.id,
                "package_id": d.package_id,
                "year": d.year,
                "month": d.month,
                "quantity": d.quantity
            } for d in monthly_dists
        ]
    )