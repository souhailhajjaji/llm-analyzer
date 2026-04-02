import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cahier Charges Analyzer"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    HF_TOKEN: Optional[str] = None

    USE_UNSLOTH: bool = False
    USE_HUGGINGFACE: bool = True
    HF_MODEL_NAME: str = "HuggingFaceTB/SmolLM2-360M-Instruct"
    HF_MAX_SEQ_LENGTH: int = 1024
    HF_TEMPERATURE: float = 0.3
    HF_DEVICE: str = "cpu"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT: int = 120

    UPLOAD_DIR: Path = Path("uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: list = [".docx"]

    RULES_DIR: Path = Path("rules")

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

settings.UPLOAD_DIR.mkdir(exist_ok=True)
settings.RULES_DIR.mkdir(exist_ok=True)
