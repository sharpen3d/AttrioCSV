bl_info = {
    "name": "Attrio CSV",
    "version": (1, 0, 1),
    "blender": (4, 5, 0),
    "description": "Bake and read back Evaluated Dependency Graph Data as CSV",
    "category": "Development",
}

import bpy
from . import ui_panel, csv_exporter, attribute_filter

def register():
    attribute_filter.register()
    csv_exporter.register()
    ui_panel.register()

def unregister():
    ui_panel.unregister()
    csv_exporter.unregister()
    attribute_filter.unregister()
