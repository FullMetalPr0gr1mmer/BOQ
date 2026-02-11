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
# NOTE: SSL verification is now handled properly - removed global SSL bypass
# which was a security vulnerability. If you need to disable SSL for specific
# local services, configure it at the client level instead.

# Configure logging to show INFO level messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
    ]
)

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Middleware to add Cache-Control headers to API responses.

    This prevents browsers from caching API responses, which can cause
    stale data issues like API_VALIDATION_ERROR after re-login.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Add no-cache headers to prevent browser caching of API responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

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
from APIs.BOQ.POReportRoute import POReportRouter
from APIs.BOQ.PriceBookRoute import router as price_book_router

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
du_project_route_module = importlib.import_module("APIs.DU.DU_ProjectRoute")
DUProjectRoute = du_project_route_module.DUProjectRoute
from APIs.DU.OD_BOQ_Route import odBOQRoute
from APIs.DU.DU_RPA_Logistics_Route import duRPALogisticsRoute

# NDPD (Network Deployment Planning Data) API imports
from APIs.NDPD.NDPDRoute import NDPDRoute

# Exchange Rate
from APIs.ExchangeRateRoute import exchangeRateRoute

# Import AI models so SQLAlchemy recognizes them
from Models.AI import Document, DocumentChunk, ChatHistory, AIAction

# Import Approval model
from Models.BOQ.Approval import Approval

# Import POReport model
from Models.BOQ.POReport import POReport

# Import PriceBook model
from Models.BOQ.PriceBook import PriceBook

# Import DU models so SQLAlchemy recognizes them
du_project_model = importlib.import_module("Models.DU.DU_Project")
from Models.DU.OD_BOQ_Site import ODBOQSite
from Models.DU.OD_BOQ_Product import ODBOQProduct
from Models.DU.OD_BOQ_Site_Product import ODBOQSiteProduct
from Models.DU.DU_RPA_Logistics import DURPAProject, DURPADescription, DURPAInvoice, DURPAInvoiceItem

# Import NDPD models so SQLAlchemy recognizes them
from Models.NDPD.NDPDData import NDPDData

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

# Add no-cache middleware to prevent browser caching of API responses
# This fixes API_VALIDATION_ERROR issues after re-login
app.add_middleware(NoCacheMiddleware)

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
app.include_router(POReportRouter)  # PO Report management
app.include_router(price_book_router) # Price Book management

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
app.include_router(odBOQRoute)          # OD BOQ management (Sites, Products, Site-Products)
app.include_router(duRPALogisticsRoute) # DU RPA Logistics management

# NDPD (Network Deployment Planning Data) Management
app.include_router(NDPDRoute)           # NDPD data management

# Exchange Rate
app.include_router(exchangeRateRoute)   # USD/AED live exchange rate

# app.include_router(pma)    # Project Management Assistant (PMA) routes

# Application entry point
if __name__ == "__main__":
    # Start the development server
    # Host: 127.0.0.1 (localhost only)
    # Port: 8003
    # Timeout: 600 seconds (10 minutes) for large file uploads
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003,
        timeout_keep_alive=600
    )