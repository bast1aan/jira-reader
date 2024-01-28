import asyncio
import importlib.util
import os
import traceback
import types

def _caller_filename() -> str:
    return traceback.extract_stack()[-3].filename

def get_module_from_file(path: str) -> types.ModuleType:
    caller_filename = _caller_filename()
    path = os.path.join(os.path.dirname(caller_filename), path)
    spec = importlib.util.spec_from_file_location(os.path.basename(path)[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def scriptdir(path: str = '') -> str:
    caller_filename = _caller_filename()
    if path:
        return os.path.join(os.path.dirname(caller_filename), path)
    return os.path.dirname(caller_filename)

async def exists(path: str, timeout: float = 1.0) -> None:
    # fine for now, inotify would be neater.
    spent = 0.0
    while spent < timeout:
        if os.path.exists(path):
            return
        await asyncio.sleep(0.01)
        spent += 0.01
    raise TimeoutError(f'Path {path} not found after {timeout} seconds')
