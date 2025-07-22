import bpy
import os
from bpy.types import Panel
import csv

def files_available_for_import(s):
    folder = bpy.path.abspath(s.export_path)
    subfolder = s.subfolder
    base_name = s.base_filename.strip()

    if not base_name:
        return False

    path = os.path.join(folder, subfolder)
    if not os.path.exists(path):
        return False

    required_headers = {'position_x', 'position_y', 'position_z'}

    for filename in os.listdir(path):
        if not filename.endswith('.csv'):
            continue

        # Enforce exact match before first underscore
        prefix = filename.split('_')[0]
        if prefix != base_name:
            continue

        fullpath = os.path.join(path, filename)
        try:
            with open(fullpath, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                if required_headers.issubset(set(headers)):
                    return True
        except Exception:
            continue

    return False

def files_available_for_import_pointcloud(s):
    base_path = bpy.path.abspath(s.export_path)
    target_dir = os.path.join(base_path, s.subfolder)
    if not os.path.isdir(target_dir):
        return False
    base_name = s.base_filename
    for fname in os.listdir(target_dir):
        if fname.endswith(".csv"):
            name_part = fname.split("_")[0]
            if name_part == base_name:
                return True
    return False

class ATTRIO_PT_setup_panel(Panel):
    bl_label = "Attrio CSV"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Attrio'

    def draw(self, context):
        s = context.scene.attrio_csv_settings
        layout = self.layout
        layout.prop(s, "export_path")
        layout.prop(s, "subfolder")
        layout.prop(s, "base_filename")


class ATTRIO_PT_export_panel(Panel):
    bl_label = "CSV Attribute Export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Attrio'
    bl_parent_id = "ATTRIO_PT_setup_panel"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type in {'MESH', 'POINTCLOUD'}

    def draw(self, context):
        s = context.scene.attrio_csv_settings
        layout = self.layout
        supported_types = {'FLOAT', 'FLOAT_VECTOR', 'FLOAT_COLOR'}
        
        layout.prop(s, "multi_frame")
        if s.multi_frame:
            layout.prop(s, "frame_start")
            layout.prop(s, "frame_end")

        layout.prop(s, "domain")
        layout.operator("attrio.refresh_attributes", text="Refresh Attributes")

        if not s.attribute_list:
            layout.label(text="No attributes found. Click 'Refresh Attributes'.", icon='INFO')
            return

        box = layout.box()
        box.label(text="Attributes to Export:")
        for item in s.attribute_list:
            if not item.name.startswith("."):
                box.prop(item, "use", text=item.name)

        layout.prop(s, "float_precision")
        layout.operator("export.attrio_csv", text="Export CSVs")


class ATTRIO_PT_import_panel(Panel):
    bl_label = "CSV Import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Attrio'
    bl_parent_id = "ATTRIO_PT_setup_panel"

    def draw(self, context):
        s = context.scene.attrio_csv_settings
        layout = self.layout
        
        if files_available_for_import_pointcloud(s):
            layout.operator("attrio.add_csv_pointcloud_object", icon="PARTICLES")

        if not files_available_for_import(s):
            layout.label(text="No importable CSVs found in folder.", icon="INFO")
            return
       

        layout.operator("attrio.add_csv_import_object", text="Import With Position Data", icon="IMPORT")



classes = (
    ATTRIO_PT_setup_panel,
    ATTRIO_PT_export_panel,
    ATTRIO_PT_import_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)