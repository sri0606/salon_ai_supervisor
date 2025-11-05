from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers.help_request import router as router_help_requests
from src.routers.knowledge_base import router as router_knowledge_base
from src.routers.livekit import router as router_livekit
from fastapi.staticfiles import StaticFiles
import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Silence noisy loggers
for noisy in ["uvicorn.access", "uvicorn.error", "livekit", "asyncio", "httpx","livekit.agents","livekit.plugins"]:
    logging.getLogger(noisy).setLevel(logging.ERROR)

logger = logging.getLogger("fastapi_server")
logger.setLevel(logging.INFO)

app = FastAPI(title="Salon AI Supervisor")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],                      # Allow all HTTP methods
    allow_headers=["*"],                      # Allow all headers
)
# Include routers
app.include_router(router_help_requests)
app.include_router(router_knowledge_base)
app.include_router(router_livekit)

app.mount("/static", StaticFiles(directory="src/static", html=True), name="static")

@app.get("/")
async def root():
    return {"status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}