"""Fusion-packaged entry point for the generic RobotCAD formal batch."""
import os, sys
PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
from FusionAPIBackendBatch import run
