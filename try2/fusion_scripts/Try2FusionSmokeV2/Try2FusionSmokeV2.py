"""Fresh Fusion script entry point that loads the current Try2FusionSmoke code."""

import importlib.util
import os


SOURCE = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "Try2FusionSmoke", "Try2FusionSmoke.py"
))
SPEC = importlib.util.spec_from_file_location("try2_fusion_smoke_current", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run(context):
    MODULE.run(context)
