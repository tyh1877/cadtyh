import importlib.util,os
s=os.path.normpath(os.path.join(os.path.dirname(__file__),'..','Try2FusionBatch','Try2FusionBatch.py'));p=importlib.util.spec_from_file_location('try2v8',s);m=importlib.util.module_from_spec(p);p.loader.exec_module(m)
def run(context):m.run(context)
