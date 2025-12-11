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

import os
import logging

# CRITICAL: Disable proxy for localhost connections FIRST
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# CRITICAL: Force offline mode for HuggingFace before ANY imports
# This prevents connection errors when WiFi changes or is unavailable
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
# Disable SSL cert verification for local operations
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
    ]
)

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
from APIs.BOQ.ApprovalRoute import router as approval_router
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

# AI API imports
from APIs.AI import chat_router, document_router

# DU (Digital Transformation) API imports
import importlib
rollout_route_module = importlib.import_module("APIs.DU.5G_Rollout_Sheet_Route")
rolloutSheetRoute = rollout_route_module.rolloutSheetRoute
du_project_route_module = importlib.import_module("APIs.DU.DU_ProjectRoute")
DUProjectRoute = du_project_route_module.DUProjectRoute
from APIs.DU.OD_BOQ_ItemRoute import odBOQItemRoute
from APIs.DU.CustomerPORoute import customerPORoute

# Import AI models so SQLAlchemy recognizes them
from Models.AI import Document, DocumentChunk, ChatHistory, AIAction

# Import Approval model
from Models.BOQ.Approval import Approval

# Import DU models so SQLAlchemy recognizes them
du_project_model = importlib.import_module("Models.DU.DU_Project")
rollout_sheet_model = importlib.import_module("Models.DU.5G_Rollout_Sheet")
from Models.DU.OD_BOQ_Item import ODBOQItem
from Models.DU.CustomerPO import CustomerPO

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
app.include_router(approval_router) # Approval workflow management

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

# AI Assistant
app.include_router(chat_router)         # AI chat and conversation
app.include_router(document_router)     # AI document management and RAG

# DU (Digital Transformation) Management
app.include_router(DUProjectRoute)      # DU Project management
app.include_router(rolloutSheetRoute)   # 5G Rollout Sheet management
app.include_router(odBOQItemRoute)      # OD BOQ Items management
app.include_router(customerPORoute)     # Customer PO management

# app.include_router(pma)    # Project Management Assistant (PMA) routes

# Application entry point
if __name__ == "__main__":
    # Start the development server
    # Host: 127.0.0.1 (localhost only)
    # Port: 8003
    uvicorn.run(app, host="127.0.0.1", port=8003)