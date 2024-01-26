import os

def __getattr__(name: str) -> str:
    return os.getenv(name)
