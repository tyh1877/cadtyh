import Part

base = f0_shape.copy()
small_visible_refinement = Part.makeBox(2.0, 2.0, 2.0, FreeCAD.Vector(20.0, -1.0, -1.0))
result_shape = base.fuse(small_visible_refinement).removeSplitter()
