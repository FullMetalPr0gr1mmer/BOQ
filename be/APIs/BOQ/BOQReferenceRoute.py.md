# BOQReferenceRoute.py Documentation

## Overview
This module provides FastAPI routing endpoints for managing BOQ (Bill of Quantities) reference data and generating BOQ reports. It handles reference data CRUD operations, CSV uploads, and comprehensive BOQ generation with advanced access control and project-based security.

## File Location
`C:\WORK\BOQ\be\APIs\BOQ\BOQReferenceRoute.py`

## Dependencies
- **FastAPI**: Web framework for API endpoints
- **SQLAlchemy**: Database ORM with advanced query capabilities
- **CSV**: File processing and generation
- **StringIO**: In-memory string operations
- **Datetime**: Timestamp handling

## Key Models
- `BOQReference`: Main entity for BOQ reference data
- `LLD`: Low Level Design data
- `Lvl3`: Level 3 BOQ structure with items
- `Inventory`: Equipment inventory management
- `Site`: Site information and metadata
- `Dismantling`: Dismantling operation records
- `Project`: Project management and association
- `User`: User authentication
- `UserProjectAccess`: Project-based access control

## Constants
- `EXPECTED_HEADERS`: Required CSV headers for reference uploads
  - `["linkid", "InterfaceName", "SiteIPA", "SiteIPB"]`

## Access Control System

### Permission Hierarchy
- **view**: Read-only access to records
- **edit**: Create and modify records
- **all**: Full access including deletion

### Authorization Functions

#### `check_project_access(current_user, project, db, required_permission)`
Validates user permissions for specific project operations.

**Parameters:**
- `current_user`: Authenticated user object
- `project`: Project entity
- `db`: Database session
- `required_permission`: Required permission level

**Logic:**
- Senior admins have unrestricted access
- Other users checked against `UserProjectAccess` table
- Permission hierarchy enforced

#### `get_user_accessible_project_ids(current_user, db)`
Retrieves all project IDs accessible to the current user.

**Returns:**
- All project IDs for senior admins
- User-specific project IDs based on access permissions

## API Endpoints

### POST `/boq/upload-reference`
**Purpose:** Bulk upload BOQ reference data via CSV
**Authorization:** Requires "edit" permission for specified project
**Request Parameters:**
- `project_id`: Project ID to associate references with
- `file`: CSV file upload

**CSV Processing:**
- Automatic dialect detection with TSV fallback
- UTF-8-sig encoding support with BOM handling
- Header validation against `EXPECTED_HEADERS`
- Bulk insert for performance optimization

**Response:** Count of processed and inserted rows

### GET `/boq/references`
**Purpose:** Retrieve paginated list of BOQ references
**Authorization:** Filtered by user's accessible projects
**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Results per page (default: 100, max: 500)
- `search`: Case-insensitive search across linkid, interface_name, site_ip_a, site_ip_b

**Features:**
- Advanced search with `COALESCE` for null-safe operations
- Ordered by creation date (newest first)
- Project-based filtering

### POST `/boq/reference`
**Purpose:** Create single BOQ reference record
**Authorization:** Requires "edit" permission for the project
**Request Body:** `BOQReferenceCreate` schema
**Response:** `BOQReferenceOut` schema

### GET `/boq/reference/{id}`
**Purpose:** Retrieve specific BOQ reference by ID
**Authorization:** Requires "view" permission for associated project
**Response:** `BOQReferenceOut` schema

### PUT `/boq/reference/{id}`
**Purpose:** Update existing BOQ reference
**Authorization:** Requires "edit" permission for associated project
**Request Body:** `BOQReferenceCreate` schema
**Response:** `BOQReferenceOut` schema

### DELETE `/boq/reference/{id}`
**Purpose:** Delete BOQ reference
**Authorization:** Requires "all" permission for associated project
**Response:** 204 No Content

### POST `/boq/generate-boq`
**Purpose:** Generate comprehensive BOQ report
**Authorization:** Requires "view" permission for associated project
**Request Body:**
```json
{
  "siteA": "site_ip_a",
  "siteB": "site_ip_b",
  "linkedIp": "link_identifier"
}
```

## BOQ Generation Logic

### Core Processing Function: `process_boq_data()`
Orchestrates data collection for BOQ generation:

1. **Reference Data Collection**: Fetches BOQ references for site pair
2. **Inventory Processing**:
   - **Outdoor Inventory**: Based on interface parsing (slot/port)
   - **Indoor Inventory**: Fixed slot=0, port=0 criteria
   - **Serial Tracking**: Prevents duplicate serial assignments
3. **LLD Integration**: Links with Low Level Design data
4. **Dismantling Logic**: Handles "swap" actions with dismantling records

### Interface Name Parsing
Uses `_parse_interface_name()` to extract:
- Site A slot/port information
- Site B slot/port information
- Enables precise inventory matching

### CSV Generation Function: `_generate_site_csv_content()`
Creates detailed CSV content for each site:

#### Site A Processing (Full Report)
- **Project Information Header**: Project name, PO number, scope, region
- **CSV Headers**: Comprehensive column structure
- **Parent-Child Hierarchy**: Lvl3 parents with associated items
- **Inventory Integration**:
  - OUTDOOR items matched with slot/port inventory
  - INDOOR items matched with indoor inventory
  - ANTENNA items with placeholder data
- **Antenna Processing**: Single antenna item per site (prevents duplicates)

#### Site B Processing (Items Only)
- **Streamlined Output**: Items without project headers
- **Same Inventory Logic**: Consistent processing as Site A
- **Antenna Handling**: Same single-item logic

### Advanced Features

#### Service Type Mapping
- "1": Software
- "2": Hardware
- "3": Service

#### Inventory Matching Logic
- **OUTDOOR**: Matches based on parsed interface slots/ports
- **INDOOR**: Uses fixed slot=0, port=0 criteria
- **ANTENNA**: Uses placeholder values ("XXXXXXXX")
- **Others**: Default placeholder values

#### Dismantling Integration
- **Swap Action Detection**: Identifies LLD records with "swap" action
- **Dismantling Quantity**: Multiplies dismantling items by specified count
- **Item Integration**: Adds dismantling Lvl3 items to processing queue

## Error Handling

### HTTP Status Codes
- **400 Bad Request**: Invalid CSV format, missing headers, empty files
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Missing projects, references, or LLD data
- **500 Internal Server Error**: Database or processing errors

### Validation Features
- **Project Existence**: Validates project before operations
- **File Format**: CSV validation with proper error messages
- **Data Integrity**: Transaction rollback on errors
- **Permission Verification**: Comprehensive access control

## Security Architecture

### Project-Based Security
- All operations filtered by user's accessible projects
- Senior admin bypass for complete access
- Permission level enforcement per operation type

### Data Protection
- Input sanitization and validation
- SQL injection prevention through ORM
- Transaction safety with rollback capabilities

## Performance Optimizations

### Database Operations
- **Bulk Operations**: `bulk_save_objects()` for CSV uploads
- **Eager Loading**: `joinedload()` for related data
- **Query Optimization**: Efficient filtering and joins
- **Index Usage**: Leverages database indexes for search

### Memory Management
- **StringIO**: In-memory CSV processing
- **Streaming**: Efficient data handling for large files
- **Connection Management**: Proper database session handling

## Output Formats

### BOQ CSV Structure
**Headers:**
- Site_IP, Item Description, L1 Category, Vendor Part Number, Type, Category, UOM, Total Qtts, Discounted unit price, SN, SW Number

**Content:**
- Project metadata and headers (Site A only)
- Parent item records with pricing
- Detailed child items with inventory data
- Combined output for both sites

### Response Format
```json
{
  "status": "success",
  "message": "BOQ data generated successfully.",
  "csv_content": "generated_csv_string",
  "site_a_total_matches": 10,
  "site_b_total_matches": 8
}
```

## Integration Points
- **ProjectRoute**: Uses `get_project_for_boq()` helper
- **Core APIs**: Leverages shared utilities and authentication
- **Database Models**: Comprehensive model integration
- **Schema Validation**: Pydantic schema enforcement