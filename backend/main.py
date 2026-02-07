# Backend API for KyungHee-Chatbot Frontend V2
# FastAPI + RAG Pipeline

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

# Add parent directory to path for importing existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers import chat, history, bookmarks

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Set environment variables
    # Load from .streamlit/secrets.toml or environment
    secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
            if "OPENAI_API_KEY" in secrets:
                os.environ["OPENAI_API_KEY"] = secrets["OPENAI_API_KEY"]
            if "LANGCHAIN_API_KEY" in secrets:
                os.environ["LANGCHAIN_API_KEY"] = secrets["LANGCHAIN_API_KEY"]
    yield
    # Shutdown

app = FastAPI(
    title="KHU Regulation Assistant API",
    description="Backend API for KyungHee University Regulation Chatbot",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(bookmarks.router, prefix="/api", tags=["bookmarks"])

@app.get("/")
async def root():
    return {"message": "KHU Regulation Assistant API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
