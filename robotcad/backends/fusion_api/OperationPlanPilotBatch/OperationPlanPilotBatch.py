"""Fusion-packaged entry point for Operation-plan Pilot batch."""
import importlib
import os
import sys

PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import OperationPlanPilotBatch as batch_module

importlib.reload(batch_module)
run = batch_module.run
