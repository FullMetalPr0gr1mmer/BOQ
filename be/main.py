"""
Main FastAPI Application Entry Point

This is the primary application file for the BOQ (Bill of Quantities) management system.
It sets up the FastAPI application, configures middleware, and registers all API routes.

The application handles three main domains:
1. BOQ (Bill of Quantities) - Core project and inventory management
2. RAN (Radio Access Network) - Network infrastructure management
3. LE (Latest Estimate/ROP) - Resource optimization and planning

Key Features:
- CORS middleware for cross-origin requests
- Database initialization and connection
- Comprehensive API routing for all modules
- Admin and user management functionality

Dependencies:
- FastAPI: Web framework for building APIs
- SQLAlchemy: Database ORM (configured in Database.session)
- Uvicorn: ASGI server for running the application

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Admin API imports
from APIs.Admin.AdminRoute import adminRoute
from APIs.Admin.UserRoute import userRoute

# BOQ (Bill of Quantities) API imports
from APIs.BOQ import Level3Route
from APIs.BOQ.BOQReferenceRoute import BOQRouter
from APIs.BOQ.DismantlingRoute import DismantlingRouter
from APIs.BOQ.InventoryRoute import inventoryRoute
from APIs.BOQ.LLDRoute import lld_router
from APIs.BOQ.LevelsRoute import levelsRouter
from APIs.BOQ.ProjectRoute import projectRoute

# LE (Latest Estimate/ROP) API imports
from APIs.LE.ROPLvl1Route import ROPLvl1router
from APIs.LE.ROPLvl2Route import ROPLvl2router
from APIs.LE.ROPProjectRoute import ROPProjectrouter
from APIs.LE.RopPackageRoute import RopPackageRouter

# RAN (Radio Access Network) API imports
from APIs.RAN.RANInventoryRouting import RANInventoryRouter
from APIs.RAN.RANLvl3Routing import RANLvl3Router
from APIs.RAN.RANProjectRouting import RANProjectRoute
from APIs.RAN.RAN_LLDRouting import ran_lld_router
from APIs.RAN.RANAntennaSerialsRouting import RANAntennaSerialsRouter


# # PMA (Project Management Assistant) API import
# from RAG.PMA import pma
# Database configuration
from Database.session import engine, Base

# Initialize FastAPI application
app = FastAPI(
    title="BOQ Management System",
    description="A comprehensive system for managing Bill of Quantities, RAN projects, and resource optimization",
    version="1.0.0"
)

# Create all database tables on startup
Base.metadata.create_all(bind=engine)

# Configure CORS middleware
# Allows requests from frontend applications running on specified origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",     # Local development frontend
        "http://10.183.72.80:5173"   # Production/staging frontend
    ],
    allow_credentials=True,          # Allow cookies and authentication headers
    allow_methods=["*"],             # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],             # Allow all headers
)

# Register API routers
# Admin and User Management
app.include_router(userRoute)       # User authentication and management
app.include_router(adminRoute)      # Admin-specific operations

# BOQ (Bill of Quantities) Management
app.include_router(projectRoute)    # Project CRUD operations
app.include_router(inventoryRoute)  # Inventory management
app.include_router(levelsRouter)    # Hierarchical level management
app.include_router(BOQRouter)       # BOQ reference data
app.include_router(Level3Route.router)  # Level 3 specific operations
app.include_router(DismantlingRouter)    # Dismantling operations
app.include_router(lld_router)      # Low Level Design operations

# RAN (Radio Access Network) Management
app.include_router(RANProjectRoute) # RAN project management
app.include_router(RANInventoryRouter)  # RAN inventory management
app.include_router(RANLvl3Router)   # RAN Level 3 operations
app.include_router(ran_lld_router)  # RAN Low Level Design
app.include_router(RANAntennaSerialsRouter)  # RAN Antenna Serials management

# LE (Latest Estimate/ROP) Management
app.include_router(ROPProjectrouter)    # ROP project management
app.include_router(ROPLvl1router)       # ROP Level 1 operations
app.include_router(ROPLvl2router)       # ROP Level 2 operations
app.include_router(RopPackageRouter)    # ROP package management

# app.include_router(pma)    # Project Management Assistant (PMA) routes

# Application entry point
if __name__ == "__main__":
    # Start the development server
    # Host: 127.0.0.1 (localhost only)
    # Port: 8003
    uvicorn.run(app, host="127.0.0.1", port=8003)