import importlib.util, os
source=os.path.normpath(os.path.join(os.path.dirname(__file__),'..','Try2FusionBatch','Try2FusionBatch.py'))
spec=importlib.util.spec_from_file_location('try2_fusion_batch_v2',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def run(context): module.run(context)
