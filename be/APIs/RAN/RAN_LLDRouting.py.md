# RAN_LLDRouting.py Documentation

## Overview
This module provides FastAPI routing endpoints for managing RAN (Radio Access Network) LLD (Low Level Design) site records. It handles CRUD operations, CSV uploads, and BoQ (Bill of Quantities) generation for RAN sites with comprehensive access control and permission management.

## File Location
`C:\WORK\BOQ\be\APIs\RAN\RAN_LLDRouting.py`

## Dependencies
- **FastAPI**: Web framework for API endpoints
- **SQLAlchemy**: Database ORM
- **CSV**: File processing
- **StringIO**: In-memory string operations

## Key Models
- `RAN_LLD`: Main entity for RAN site records
- `RANInventory`: Inventory management for RAN sites
- `RANLvl3`: Level 3 RAN data structure
- `User`: User authentication and authorization
- `UserProjectAccess`: Project-based access control

## Access Control System

### Permission Levels
- **view**: Read-only access to records
- **edit**: Create and modify records
- **all**: Full access including deletion

### Role Hierarchy
- **senior_admin**: Complete access to all projects and operations
- **Other roles**: Project-specific access based on `UserProjectAccess`

## Helper Functions

### `check_ranlld_project_access(current_user, pid_po, db, required_permission)`
Validates user permissions for specific project operations.

**Parameters:**
- `current_user`: Authenticated user object
- `pid_po`: Project identifier
- `db`: Database session
- `required_permission`: Required permission level ("view", "edit", "all")

**Returns:** Boolean indicating access granted/denied

### `get_accessible_projects_for_lld(current_user, db)`
Retrieves all project IDs accessible to the current user.

**Returns:** List of project IDs or None for senior admins

### `get_service_type_name(service_types)`
Converts service type codes to human-readable names.

**Mapping:**
- "1": Software
- "2": Hardware
- "3": Service

## API Endpoints

### POST `/ran-sites/`
**Purpose:** Create new RAN Site record
**Authorization:** Requires "edit" permission for the project
**Restrictions:** Users cannot create records
**Request Body:** `RANSiteCreate` schema
**Response:** `RANSiteOut` schema

### GET `/ran-sites`
**Purpose:** Retrieve paginated list of RAN sites with search
**Authorization:** Filtered by user's accessible projects
**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 50, max: 100)
- `search`: Filter by site_id or technical_boq
**Response:** `PaginatedRANSites` schema

### GET `/ran-sites/{site_id}`
**Purpose:** Retrieve specific RAN site by ID
**Authorization:** Requires "view" permission
**Response:** `RANSiteOut` schema

### PUT `/ran-sites/{site_id}`
**Purpose:** Update existing RAN site
**Authorization:** Requires "edit" permission
**Restrictions:** Users cannot update records
**Request Body:** `RANSiteUpdate` schema
**Response:** `RANSiteOut` schema

### DELETE `/ran-sites/{site_id}`
**Purpose:** Delete RAN site record
**Authorization:** Requires "all" permission
**Restrictions:** Users cannot delete records
**Response:** Success message

### POST `/ran-sites/upload-csv`
**Purpose:** Bulk upload RAN sites via CSV file
**Authorization:** Project-specific access validation per record
**Restrictions:** Users cannot upload CSV files
**File Format:** CSV with columns: Site ID, New Antennas, Total Antennas, Technical BoQ, Technical BoQ Key, pid_po
**Response:** Count of inserted records

### GET `/ran-sites/{site_id}/generate-boq`
**Purpose:** Generate BoQ CSV from RAN site data
**Process:**
1. Validates site existence and key availability
2. Fetches inventory pool for the site
3. Matches RANLvl3 data using site keys
4. Generates CSV with parent-child hierarchy
5. Applies serial number matching logic
6. Includes new antenna specifications

## BoQ Generation Logic

### Serial Number Matching
The `_find_matching_serial()` function implements sophisticated matching logic:

1. **Exact Description Match**: Full child description matches inventory label
2. **First Word to Full Label**: Child's first word matches complete inventory label
3. **First Word to First Word**: Both first words match
4. **Fallback**: Returns "NA" if no match found

### CSV Structure
Generated BoQ CSV includes:
- **Headers**: PO Line -L1, Item Code, L1 Category, Service Type, Seq.-L2, Model Name/Description, Serial number, Quantity, Notes
- **Parent Records**: High-level BoQ items with category information
- **Child Records**: Detailed items with serial numbers and specifications
- **New Antennas**: Additional antenna records based on site specifications

### Key Features
- **Inventory Integration**: Links RAN site data with physical inventory
- **Serial Tracking**: Prevents duplicate serial number assignment
- **Quantity Handling**: Repeats records based on UOM (Unit of Measure) values
- **Antenna Management**: Automatically includes new antenna specifications

## Error Handling
- **Authentication Errors**: 403 Forbidden for insufficient permissions
- **Not Found Errors**: 404 for missing records
- **Validation Errors**: 400 for invalid data or file formats
- **Server Errors**: 500 for database or processing failures

## Security Features
- **Project-based Access Control**: Users can only access authorized projects
- **Role-based Permissions**: Different permission levels for different operations
- **Input Validation**: Comprehensive validation for all endpoints
- **Database Transaction Safety**: Proper rollback on errors

## File Export
Generated BoQ files are returned as streaming CSV responses with appropriate headers for download, named using the pattern `boq_{site_id}.csv`.