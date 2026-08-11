"""
run.py
======

Responsibility:  Initializes the Uvicorn ASGI server and runs the FastAPI application.

Pipeline Position: Application Entry Point
"""

import uvicorn
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Runs the Uvicorn server on port 8000
    uvicorn.run("run:app", host="0.0.0.0", port=8000, reload=True)