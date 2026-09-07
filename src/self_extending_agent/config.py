from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("MODEL", "google_genai:gemini-3.6-flash")
    sandbox_backend: str = os.getenv("SANDBOX_BACKEND", "local")
    max_tool_generation_attempts: int = int(os.getenv("MAX_TOOL_GENERATION_ATTEMPTS", "3"))
    tool_execution_timeout_seconds: int = int(os.getenv("TOOL_EXECUTION_TIMEOUT_SECONDS", "8"))

settings = Settings()
