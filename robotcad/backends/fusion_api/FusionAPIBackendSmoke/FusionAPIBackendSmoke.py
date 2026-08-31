"""Fusion-packaged entry point for the generic RobotCAD skill smoke."""
import importlib
import os
import sys

PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import FusionAPIBackendSmoke as smoke_module

importlib.reload(smoke_module)
run = smoke_module.run
