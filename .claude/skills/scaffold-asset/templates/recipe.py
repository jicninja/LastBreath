# Recipe for {{ART_ID}} ({{name_kebab}})
#
# Executed inside Blender via blender-mcp's execute_blender_code verb.
# The asset-designer fills in the body. Keep it idempotent — running this
# script on an empty scene should produce the asset deterministically.

import bpy

def build():
    # TODO: write the asset-construction code here.
    # Example: bpy.ops.mesh.primitive_cube_add(size=1.0)
    raise NotImplementedError("Implement the recipe for {{ART_ID}}.")

if __name__ == "__main__":
    build()
