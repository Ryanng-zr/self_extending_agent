from .base import SandboxBackend
from .local import LocalSubprocessSandbox
from .daytona_backend import DaytonaSandbox


def build_sandbox(name: str) -> SandboxBackend:
    name = name.strip().lower()
    if name == "local":
        return LocalSubprocessSandbox()
    if name == "daytona":
        return DaytonaSandbox()
    raise ValueError(f"Unknown sandbox backend: {name}")
