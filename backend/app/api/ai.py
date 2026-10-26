from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.ai.model_manager import model_manager
from app.brain.state_manager import state_manager

router = APIRouter(prefix="/ai", tags=["AI Status"])

class ModelSelectRequest(BaseModel):
    model_name: str

@router.get("/status")
async def get_ai_status():
    """Returns connectivity, available local models, and active model."""
    status = await model_manager.get_status()
    return status

@router.post("/select-model")
async def select_model(payload: ModelSelectRequest):
    """Switch active model name dynamically."""
    model_manager.set_active_model(payload.model_name)
    state_manager.add_activity(
        title="Model Switched",
        category="AI",
        detail=f"Active inference model set to: {payload.model_name}",
        level="INFO"
    )
    return {
        "success": True,
        "active_model": model_manager.active_model
    }
