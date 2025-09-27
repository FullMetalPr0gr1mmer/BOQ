"""
Backend Server Startup Script

This script provides an alternative way to start the FastAPI backend server.
It's configured to run the main application with specific server settings.

Usage:
    python start_be.py

Configuration:
    - Host: 127.0.0.1 (localhost)
    - Port: 8001 (alternative to main.py's port 8003)
    - Reload: Disabled for production use

Note: This script is currently commented out. To use it, uncomment the
if __name__ == "__main__" block and run this file directly.

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

import uvicorn

# Alternative server startup configuration
# Uncomment the following lines to use this script for starting the server
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)