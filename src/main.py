"""
FastAPI application for PDF Bank Statement Parser

Main application entry point that configures FastAPI and includes routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from .api import router

# Create FastAPI app
app = FastAPI(
    title="Bank Statement Parser API",
    description="Parse PDF bank statements and extract transactions for Lederly",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Bank Statement Parser",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Serve the multi-statement upload page"""
    with open("/tmp/multi_statement_review.html", "r") as f:
        return f.read()


@app.get("/debug", response_class=HTMLResponse)
async def debug_page():
    """Serve the debug parser page"""
    with open("/tmp/debug_parser.html", "r") as f:
        return f.read()


@app.get("/statements", response_class=HTMLResponse)
async def view_statements_page():
    """Serve the view saved statements page"""
    with open("/tmp/view_statements.html", "r") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
