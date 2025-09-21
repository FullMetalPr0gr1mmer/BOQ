# Utils/monthly_distribution_utils.py
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Tuple
from Schemas.LE.MonthlyDistributionSchema import MonthlyDistributionItem


def generate_monthly_periods(start_date: date, end_date: date) -> List[Tuple[int, int]]:
    """
    Generate list of (year, month) tuples between start_date and end_date (inclusive).

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        List of (year, month) tuples
    """
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")

    periods = []
    current = start_date.replace(day=1)  # Start from first day of start month
    end = end_date.replace(day=1)  # End at first day of end month

    while current <= end:
        periods.append((current.year, current.month))
        current += relativedelta(months=1)

    return periods


def auto_distribute_quantity(total_quantity: int, start_date: date, end_date: date) -> List[MonthlyDistributionItem]:
    """
    Automatically distribute total quantity evenly across months between start and end dates.

    Args:
        total_quantity: Total quantity to distribute
        start_date: Start date
        end_date: End date

    Returns:
        List of MonthlyDistributionItem with evenly distributed quantities
    """
    if total_quantity <= 0:
        return []

    periods = generate_monthly_periods(start_date, end_date)
    if not periods:
        return []

    # Calculate base quantity per month and remainder
    months_count = len(periods)
    base_quantity = total_quantity // months_count
    remainder = total_quantity % months_count

    distributions = []
    for i, (year, month) in enumerate(periods):
        # Distribute remainder across first few months
        quantity = base_quantity + (1 if i < remainder else 0)
        distributions.append(MonthlyDistributionItem(
            year=year,
            month=month,
            quantity=quantity
        ))

    return distributions


def validate_distributions_within_date_range(
        distributions: List[MonthlyDistributionItem],
        start_date: date,
        end_date: date
) -> bool:
    """
    Validate that all distributions fall within the given date range.

    Args:
        distributions: List of monthly distributions
        start_date: Package start date
        end_date: Package end date

    Returns:
        True if all distributions are within range, False otherwise
    """
    if not distributions:
        return True

    valid_periods = set(generate_monthly_periods(start_date, end_date))

    for dist in distributions:
        if (dist.year, dist.month) not in valid_periods:
            return False

    return True


def get_month_name(month: int) -> str:
    """Get month name from month number."""
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    return months[month] if 1 <= month <= 12 else "Invalid"


def format_distribution_summary(distributions: List[MonthlyDistributionItem]) -> Dict:
    """
    Format distributions for easy display.

    Returns:
        Dictionary with formatted distribution info
    """
    if not distributions:
        return {"total": 0, "months": []}

    total = sum(d.quantity for d in distributions)
    months = []

    for dist in sorted(distributions, key=lambda x: (x.year, x.month)):
        months.append({
            "period": f"{get_month_name(dist.month)} {dist.year}",
            "year": dist.year,
            "month": dist.month,
            "quantity": dist.quantity
        })

    return {
        "total": total,
        "months": months,
        "period_count": len(months)
    }