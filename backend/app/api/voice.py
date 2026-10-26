from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from app.voice.audio_manager import audio_manager
from app.config import settings

logger = logging.getLogger("nova.api.voice")

router = APIRouter(prefix="/voice", tags=["Voice Intelligence"])

class VoiceSettingsRequest(BaseModel):
    wake_word_enabled: Optional[bool] = None
    wake_word_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    input_device: Optional[int] = None
    output_device: Optional[int] = None
    tts_speech_rate: Optional[float] = Field(None, ge=0.5, le=2.0)
    tts_volume: Optional[float] = Field(None, ge=0.0, le=2.0)
    voice_mode: Optional[str] = None

@router.get("/status")
async def get_voice_status():
    """Returns real-time status of wake word, Vosk STT, Piper TTS, and mic pipeline."""
    return audio_manager.get_status()

@router.post("/start")
async def start_voice_pipeline():
    """Start microphone monitoring and wake word detection in background."""
    success = audio_manager.start()
    return {
        "success": success,
        "running": audio_manager.is_running,
        "message": "Voice pipeline running." if success else "Failed to open microphone."
    }

@router.post("/stop")
async def stop_voice_pipeline():
    """Halt microphone capture and voice loops."""
    success = audio_manager.stop()
    return {
        "success": success,
        "running": audio_manager.is_running,
        "message": "Voice pipeline stopped."
    }

@router.post("/trigger-listen")
async def trigger_listen():
    """Manually initiate speech recognition listening (e.g. from UI mic tap)."""
    success = audio_manager.trigger_listening()
    return {
        "success": success,
        "mode": audio_manager.pipeline_mode
    }

@router.post("/stop-listen")
async def stop_listen():
    """Manually conclude speech recognition listening."""
    success = audio_manager.stop_listening()
    return {
        "success": success,
        "mode": audio_manager.pipeline_mode
    }

@router.get("/devices")
async def get_audio_devices():
    """List available physical microphones and speakers."""
    return audio_manager.get_audio_devices()

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak")
async def speak_text(payload: SpeakRequest):
    """Synthesize speech using Piper TTS offline engine."""
    success = audio_manager.tts.speak(payload.text)
    return {"success": success, "text": payload.text}

@router.post("/settings")
async def update_voice_settings(payload: VoiceSettingsRequest):
    """Update runtime voice configuration parameters."""
    if payload.voice_mode is not None:
        mode = payload.voice_mode.strip().lower()
        audio_manager.set_wake_word_enabled(mode == "wake_word")
    if payload.wake_word_enabled is not None:
        audio_manager.set_wake_word_enabled(payload.wake_word_enabled)
        
    if payload.wake_word_threshold is not None:
        audio_manager.wake_word_engine.threshold = payload.wake_word_threshold
        
    if payload.input_device is not None:
        audio_manager.input_device = payload.input_device
        # Restart stream if running to apply device change
        if audio_manager.is_running:
            audio_manager.stop()
            audio_manager.start()
            
    if payload.output_device is not None:
        audio_manager.output_device = payload.output_device
        audio_manager.tts.output_device = payload.output_device
        
    if payload.tts_speech_rate is not None:
        audio_manager.tts.speech_rate = payload.tts_speech_rate
        
    if payload.tts_volume is not None:
        audio_manager.tts.volume = payload.tts_volume

    return {
        "success": True,
        "settings": audio_manager.get_status()
    }

@router.websocket("/ws")
async def voice_websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket event bridge for:
    - wake_word_detected
    - listening_started
    - speech_recognized
    - thinking_started
    - speaking_started
    - speaking_finished
    - listening_stopped
    - voice_error
    - audio_level (live mic RMS)
    """
    await websocket.accept()
    audio_manager.add_ws_subscriber(websocket)
    
    # Send initial status
    try:
        await websocket.send_json({
            "type": "connected",
            "status": audio_manager.get_status()
        })
        
        while True:
            # Receive client commands (e.g. {"action": "trigger_listen"}, {"action": "stop_speaking"})
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "trigger_listen":
                audio_manager.trigger_listening()
            elif action == "stop_listen":
                audio_manager.stop_listening()
            elif action == "stop_speaking":
                audio_manager.cancel_active_turn()
            elif action == "cancel_inference":
                audio_manager.cancel_active_turn()
            elif action == "start":
                audio_manager.start()
            elif action == "stop":
                audio_manager.stop()
                
    except WebSocketDisconnect:
        audio_manager.remove_ws_subscriber(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client error: {e}")
        audio_manager.remove_ws_subscriber(websocket)
