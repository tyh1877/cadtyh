"""Resolve the local FreeCAD Python runtime without hard-coding a single install."""
import os
from pathlib import Path


def python_runtime():
    candidates = [
        os.environ.get("FREECAD_PYTHON"),
        r"C:\Users\Lenovo\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe",
        r"D:\software\freeCAD\install\bin\python.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    raise FileNotFoundError("FreeCAD Python runtime not found; set FREECAD_PYTHON")
