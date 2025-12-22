"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import tournament, auth
from app.database import engine, Base

# Tạo database tables
Base.metadata.create_all(bind=engine)

# Tạo FastAPI app
app = FastAPI(
    title="ITISCUP Tournament API",
    description="API cho hệ thống đăng ký giải đấu ITISCUP với thanh toán MoMo",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tournament.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ITISCUP Tournament API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

