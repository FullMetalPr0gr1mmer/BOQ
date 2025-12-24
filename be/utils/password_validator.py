"""
Password Strength Validator

This module provides password validation functionality to enforce strong password
requirements across the BOQ application. It ensures all user passwords meet
security best practices.

Password Requirements:
- Minimum 8 characters
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one number (0-9)
- At least one special character (!@#$%^&*(),.?":{}|<>)

Usage:
    from utils.password_validator import validate_password_strength

    is_valid, message = validate_password_strength("MyP@ssw0rd")
    if not is_valid:
        raise ValueError(message)

Author: Security Hardening Initiative
Created: 2025-12-17
"""

import re
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate that a password meets security requirements.

    Args:
        password (str): The password to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
            - is_valid: True if password meets all requirements, False otherwise
            - error_message: Description of validation result or first failed requirement

    Example:
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")

        >>> validate_password_strength("Strong123!")
        (True, "Password meets all security requirements")
    """
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter (A-Z)"

    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter (a-z)"

    # Check for digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number (0-9)"

    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    # All requirements met
    return True, "Password meets all security requirements"


def get_password_requirements() -> dict:
    """
    Get a dictionary of password requirements for display to users.

    Returns:
        dict: Dictionary with requirement descriptions and regex patterns

    Example:
        >>> requirements = get_password_requirements()
        >>> for req in requirements['requirements']:
        ...     print(f"• {req}")
    """
    return {
        "min_length": 8,
        "requirements": [
            "At least 8 characters long",
            "At least one uppercase letter (A-Z)",
            "At least one lowercase letter (a-z)",
            "At least one number (0-9)",
            "At least one special character (!@#$%^&*(),.?\":{}|<>)"
        ],
        "example": "Example: MyP@ssw0rd2025"
    }


# Convenience function for quick validation (raises exception on failure)
def require_strong_password(password: str) -> None:
    """
    Validate password and raise ValueError if it doesn't meet requirements.

    This is a convenience function for use in API endpoints where you want
    to fail fast with an exception rather than checking the return value.

    Args:
        password (str): The password to validate

    Raises:
        ValueError: If password doesn't meet security requirements

    Example:
        >>> try:
        ...     require_strong_password("weak")
        ... except ValueError as e:
        ...     print(f"Error: {e}")
        Error: Password must be at least 8 characters long
    """
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        raise ValueError(message)


if __name__ == "__main__":
    # Test the validator
    test_passwords = [
        ("weak", False),
        ("weakpassword", False),
        ("WeakPassword", False),
        ("WeakPassword1", False),
        ("WeakP@ssword", False),
        ("Strong123!", True),
        ("MyP@ssw0rd2025", True),
        ("Boq#Secure789", True)
    ]

    print("Testing Password Validator:")
    print("=" * 60)
    for password, expected_valid in test_passwords:
        is_valid, message = validate_password_strength(password)
        status = "[PASS]" if is_valid == expected_valid else "[FAIL]"
        print(f"{status} Password: '{password}'")
        print(f"   Result: {message}")
        print()
