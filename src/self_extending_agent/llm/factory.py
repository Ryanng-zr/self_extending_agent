from __future__ import annotations

import os
from .base import WorkflowModel
from .demo import DemoWorkflowModel


def build_model(mode: str, model_name: str) -> WorkflowModel:
    if mode == "demo":
        return DemoWorkflowModel()
    if mode == "llm":
        from .langchain_model import LangChainWorkflowModel
        if not os.getenv("GOOGLE_API_KEY") and model_name.startswith("google_genai:"):
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Use --mode demo or configure .env."
            )
        return LangChainWorkflowModel(model_name)
    raise ValueError(f"Unknown mode: {mode}")
