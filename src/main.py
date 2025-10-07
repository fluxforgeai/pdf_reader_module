"""
FastAPI application for PDF Bank Statement Parser

Main application entry point that configures FastAPI and includes routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
