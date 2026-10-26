import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

from app.config import settings
from app.api.system import router as system_router
from app.api.ai import router as ai_router
from app.api.chat import router as chat_router
from app.api.voice import router as voice_router
from app.api.memory import router as memory_router
from app.api.tools_routes import router as tools_router
from app.api.tasks_routes import tasks_router, executions_router
from app.api.vision_routes import router as vision_router
from app.api.agents_routes import router as agents_router
from app.api.workflow_routes import router as workflow_router
from app.api.automation_routes import router as automation_router
from app.api.personalization_routes import router as personalization_router
from app.brain.state_manager import state_manager
from app.voice.audio_manager import audio_manager
from app.automation import automation_manager
from app.personalization import personalization_manager
from app.reliability.subsystem_supervisor import subsystem_supervisor
from app.tools.permission_manager import SecurityViolationError
from fastapi.responses import JSONResponse
from fastapi import Request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nova.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set running event loop for audio manager WebSocket broadcasts
    loop = asyncio.get_running_loop()
    audio_manager.set_event_loop(loop)
    
    # 1. Startup supervisor (database integrity, backup baseline, stale workflow reconciliation)
    await subsystem_supervisor.on_startup()

    # 2. Initialize v0.7 Automation Engine
    logger.info("Initializing v0.7 Proactive Automation Engine...")
    automation_manager.initialize()

    # 3. Initialize v0.8 Personalization Engine
    logger.info("Initializing v0.8 Adaptive Personalization Engine...")
    personalization_manager.initialize()

    # 4. Auto-start voice loop if enabled
    if settings.VOICE_ENABLED:
        logger.info("Initializing offline voice pipeline in background...")
        audio_manager.start()
        
    yield
    
    # Graceful shutdown supervised
    await subsystem_supervisor.on_shutdown()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="NOVA Personal AI Desktop Assistant Core API",
    lifespan=lifespan
)

# CORS setup for Vite and Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(SecurityViolationError)
async def security_violation_handler(request: Request, exc: SecurityViolationError):
    logger.warning(f"Security violation blocked on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "type": "SecurityViolation"}
    )

# Include API Routers under /api
app.include_router(system_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(executions_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")
app.include_router(automation_router, prefix="/api")
app.include_router(personalization_router, prefix="/api")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat(),
        "state": state_manager.get_state().value,
        "voice_pipeline": audio_manager.is_running
    }

@app.get("/api/activity/recent", tags=["Activity"])
async def get_recent_activity():
    """Retrieve recent assistant activity and telemetry events."""
    return {
        "activities": state_manager.get_activities()
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health": "/api/health",
        "voice_status": "/api/voice/status"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
