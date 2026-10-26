import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "NOVA - Neural Operational Virtual Assistant"
    VERSION: str = "1.0.2"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Ollama Local AI Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "qwen2.5:1.5b"
    FALLBACK_MODELS: List[str] = ["qwen2.5:1.5b", "gemma2:2b", "llama3.2:1b", "qwen3:4b"]
    # CPU inference profile (i3-1115G4 / 12 GB). None num_thread = Ollama auto.
    OLLAMA_NUM_CTX: int = 1024
    OLLAMA_NUM_PREDICT: int = 256
    OLLAMA_NUM_PREDICT_VOICE: int = 96
    OLLAMA_NUM_THREAD: Optional[int] = 2
    OLLAMA_KEEP_ALIVE: str = "10m"
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_HISTORY_TURNS: int = 4
    OLLAMA_MAX_HISTORY_TURNS_VOICE: int = 2
    
    # Root directory of the repository
    ROOT_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    # Database Configuration
    DATABASE_PATH: str = "nova_memory.db"
    BACKUP_DIR: str = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "backups")
    BACKUP_RETENTION_MAX: int = 15
    
    # Persistent Intelligence & Memory (v0.3)
    MEMORY_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    MEMORY_SIMILARITY_THRESHOLD: float = 0.45
    MAX_RELEVANT_MEMORIES: int = 5
    AUTO_EXTRACT_MEMORY: bool = True
    
    # Voice Intelligence Configuration (v0.2)
    VOICE_ENABLED: bool = True
    WAKE_WORD_MODEL: str = "hey_jarvis"  # openWakeWord model: 'hey_jarvis', 'alexa', 'hey_mycroft', or custom path
    CUSTOM_WAKE_WORD_PATH: Optional[str] = "models/wake_words/hey_nova.onnx"
    WAKE_WORD_THRESHOLD: float = 0.5
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_INPUT_DEVICE: Optional[int] = None
    AUDIO_OUTPUT_DEVICE: Optional[int] = None
    
    # Vosk Speech Recognition
    VOSK_MODEL_PATH: str = ""  # auto-load default small en-us model if empty
    SPEECH_SILENCE_TIMEOUT: float = 1.6  # seconds of trailing silence to finalize phrase
    SPEECH_MAX_TIMEOUT: float = 10.0     # max listening window
    
    # Piper TTS
    PIPER_MODEL_PATH: str = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "models", "piper", "en_US-lessac-low.onnx")
    PIPER_CONFIG_PATH: str = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "models", "piper", "en_US-lessac-low.onnx.json")
    TTS_SPEECH_RATE: float = 1.05
    TTS_VOLUME: float = 1.0
    
    # CORS Origins restricted strictly to local desktop application
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost"
    ]
    
    # System Persona
    SYSTEM_PROMPT: str = (
        "You are NOVA (Neural Operational Virtual Assistant), an advanced, intelligent, "
        "and polished JARVIS-inspired AI assistant. You speak with high competence, clarity, "
        "and a calm, futuristic presence. You provide actionable, succinct, and brilliant responses. "
        "You have persistent memory across user preferences, projects, tasks, and previous conversations."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
