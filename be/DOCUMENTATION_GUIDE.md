# BOQ Backend Documentation Guide

## Overview

This guide provides comprehensive documentation for the BOQ (Bill of Quantities) management system backend. The system is built with FastAPI and handles three main domains: BOQ projects, RAN (Radio Access Network) projects, and LE/ROP (Latest Estimate/Resource Optimization Planning) projects.

## Architecture Overview

### System Structure
```
be/
├── main.py                 # Main FastAPI application entry point
├── start_be.py            # Alternative server startup script
├── SeedAdmin.py           # Admin user creation script
├── Database/
│   └── session.py         # Database configuration and session management
├── APIs/                  # API route handlers
│   ├── Core.py           # Authentication and utility functions
│   ├── Admin/            # Admin-related routes
│   ├── BOQ/              # BOQ project routes
│   ├── RAN/              # RAN project routes
│   └── LE/               # LE/ROP project routes
├── Models/               # SQLAlchemy ORM models
│   ├── Admin/           # User and role models
│   ├── BOQ/             # BOQ project models
│   ├── RAN/             # RAN project models
│   └── LE/              # LE/ROP project models
├── Schemas/             # Pydantic schemas for API validation
│   ├── Admin/           # Admin schemas
│   ├── BOQ/             # BOQ schemas
│   ├── RAN/             # RAN schemas
│   └── LE/              # LE schemas
└── alembic/             # Database migration files
```

### Core Components

#### 1. Application Entry Point (`main.py`)
- FastAPI application initialization
- CORS middleware configuration
- Database table creation
- API router registration
- Development server configuration

#### 2. Database Layer (`Database/session.py`)
- SQLAlchemy engine configuration
- Session factory setup
- Base model class definition
- Environment variable integration

#### 3. Authentication & Security (`APIs/Core.py`)
- JWT token management
- Password hashing with bcrypt
- User authentication functions
- Utility functions for data processing

#### 4. Admin Setup (`SeedAdmin.py`)
- Initial admin user creation
- Role validation
- Secure password handling

## Documentation Standards

### File Header Template
```python
"""
[Module Name]

[Brief description of the module's purpose and functionality]

[Key features or components list]

Dependencies:
- [List key dependencies]

Environment Variables (if applicable):
- [List required environment variables]

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""
```

### Function Documentation Template
```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of what the function does.

    Detailed explanation of the function's behavior, including
    any important business logic or edge cases.

    Args:
        param1 (type): Description of parameter
        param2 (type): Description of parameter

    Returns:
        return_type: Description of return value

    Raises:
        ExceptionType: When this exception occurs

    Example:
        >>> function_name("example", 123)
        "expected_result"
    """
```

### Model Documentation Template
```python
class ModelName(Base):
    """
    [Model Name] - Brief description of what this model represents.

    Detailed description of the model's purpose, business logic,
    and relationships within the system.

    Attributes:
        field_name (type): Description of field, including constraints
                          and business rules

    Relationships:
        relationship_name: Description of relationship and its purpose

    Business Logic:
        - Key business rules
        - Validation requirements
        - Usage patterns

    Usage Example:
        instance = ModelName(
            field_name="value"
        )
    """
```

## Project Domains

### 1. BOQ (Bill of Quantities)
**Purpose**: Manages telecommunications infrastructure project costs and materials

**Key Models**:
- `Project`: Core project information
- `Inventory`: Material and equipment inventory
- `Levels`: Hierarchical project structure
- `BOQReference`: Reference data for BOQ items
- `LLD`: Low Level Design specifications
- `Dismantling`: Equipment dismantling records

**Key APIs**:
- Project management (CRUD operations)
- Inventory tracking
- Level hierarchy management
- BOQ reference data
- LLD operations

### 2. RAN (Radio Access Network)
**Purpose**: Manages radio network infrastructure projects

**Key Models**:
- `RANProject`: RAN-specific project data
- `RANInventory`: RAN equipment inventory
- `RANLvl3`: Level 3 RAN specifications
- `RAN_LLD`: RAN Low Level Design

**Key APIs**:
- RAN project management
- RAN inventory operations
- Level 3 specifications
- RAN LLD management

### 3. LE/ROP (Latest Estimate/Resource Optimization Planning)
**Purpose**: Resource planning and optimization for projects

**Key Models**:
- `ROPProject`: Resource optimization projects
- `ROPLvl1`, `ROPLvl2`: Multi-level planning structure
- `RopPackages`: Resource packages
- `MonthlyDistribution`: Time-based resource allocation

**Key APIs**:
- ROP project management
- Multi-level planning
- Package management
- Distribution planning

## Environment Variables

### Required Variables
```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/boq_db

# JWT Authentication
SECRET_KEY=your_jwt_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Admin Setup
ADMIN_PASSWORD=your_bcrypt_hashed_admin_password
```

## Database Migration

The system uses Alembic for database migrations:

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Downgrade migrations
alembic downgrade -1
```

## API Documentation

FastAPI automatically generates API documentation:
- Swagger UI: `http://localhost:8003/docs`
- ReDoc: `http://localhost:8003/redoc`

## Security Features

### Authentication
- JWT-based authentication
- Bcrypt password hashing
- Role-based access control
- Project-specific permissions

### Authorization
- Role system (admin, user, viewer)
- Project-level access control
- API endpoint protection
- Audit logging

## Development Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**:
   - Copy `.env.example` to `.env`
   - Configure database and other settings

3. **Database Setup**:
   ```bash
   alembic upgrade head
   python SeedAdmin.py
   ```

4. **Run Development Server**:
   ```bash
   python main.py
   # or
   python start_be.py
   ```

## Remaining Documentation Tasks

To complete the documentation for all files, follow this priority order:

### High Priority
1. **API Route Files**: Document all route handlers with endpoint descriptions
2. **Model Files**: Add comprehensive model documentation
3. **Schema Files**: Document Pydantic schemas for API validation

### Medium Priority
1. **Utility Modules**: Document helper functions and utilities
2. **Migration Files**: Add descriptions to Alembic migration files

### Low Priority
1. **Configuration Files**: Document configuration and setup files

## Documentation Guidelines

### For Each File:
1. **Add module-level docstring** explaining purpose and functionality
2. **Document all classes** with comprehensive descriptions
3. **Document all functions** with parameters, returns, and examples
4. **Include business logic** explanations where relevant
5. **Add usage examples** for complex functionality

### Quality Standards:
- Clear, concise language
- Complete parameter descriptions
- Business context explanation
- Error handling documentation
- Example usage where helpful

## Contact

For questions about the documentation or codebase:
- Review existing documented files for patterns
- Follow the templates provided in this guide
- Maintain consistency with documented examples

---

**Note**: This documentation guide serves as a reference for maintaining and extending the BOQ management system. Keep it updated as the system evolves.