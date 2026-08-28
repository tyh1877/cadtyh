"""Fresh entry point for the assembly-context joint smoke-test revision."""
import importlib.util
import os

source = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Try2FusionSmoke", "Try2FusionSmoke.py"))
spec = importlib.util.spec_from_file_location("try2_fusion_smoke_v3", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def run(context):
    module.run(context)
