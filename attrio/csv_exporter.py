# csv_exporter.py – sharpen3d / AttrIO CSV
import bpy
import csv
import os
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, EnumProperty, IntProperty, PointerProperty, BoolProperty, CollectionProperty
from .attribute_filter import ATTRIO_UL_attribute_item

# Helper Functions and Append Node_groups

NODE_GROUPS_BLEND_FILE = os.path.join(os.path.dirname(__file__), "attrio_node_groups.blend")

def append_node_group(group_name):
    with bpy.data.libraries.load(NODE_GROUPS_BLEND_FILE, link=False) as (data_from, data_to):
        if group_name in data_from.node_groups:
            data_to.node_groups.append(group_name)

def ensure_node_group(group_name):
    if group_name not in bpy.data.node_groups:
        append_node_group(group_name)
        
def get_object_domains(obj_type):
    if obj_type == 'MESH':
        return [
            ('POINT', "Point", ""),
            ('EDGE', "Edge", ""),
            ('FACE', "Face", ""),
            ('CORNER', "Face Corner", "")
        ]
    elif obj_type == 'POINTCLOUD':
        return [
            ('POINT', "Point", "")
        ]
    return []


def get_dynamic_domains(self, context):
    obj = context.active_object
    if not obj:
        return []
    return get_object_domains(obj.type)


# Properties

class ATTRIO_PG_csv_settings(PropertyGroup):
    export_path: StringProperty(name="Directory", subtype='DIR_PATH')
    subfolder: StringProperty(name="Subfolder", default="csv_export")
    base_filename: StringProperty(name="Name", default="name")
    multi_frame: BoolProperty(name="Export Frame Range", default=True)
    frame_start: IntProperty(name="Start Frame", default=1)
    frame_end: IntProperty(name="End Frame", default=250)
    domain: EnumProperty(
        name="Domain",
        description="Attribute domain to export from",
        items=get_dynamic_domains
    )
    float_precision: EnumProperty(
        name="Float Precision",
        description="Controls numeric precision in CSV output",
        items=[
            ('REDUCED', "Reduced (float32, ~7 digits)", "Faster but may lose detail"),
            ('FULL', "Full (float64, ~15 digits)", "Recommended for simulation/debug pipelines")
        ],
        default='FULL'
    )
    attribute_list: CollectionProperty(type=ATTRIO_UL_attribute_item)


# Attrio Export
    
class EXPORT_OT_attrio_csv(Operator):
    bl_idname = "export.attrio_csv"
    bl_label = "Export AttrIO CSV"

    def format_float(self, value, mode):
        return f"{value:.15g}" if mode == 'FULL' else f"{value:.7g}"

    def execute(self, context):
        s = context.scene.attrio_csv_settings
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        path = os.path.join(bpy.path.abspath(s.export_path), s.subfolder)
        os.makedirs(path, exist_ok=True)

        frame_range = (
            range(s.frame_start, s.frame_end + 1)
            if s.multi_frame else [context.scene.frame_current]
        )

        for frame in frame_range:
            context.scene.frame_set(frame)
            depsgraph = context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)

            try:
                eval_data = eval_obj.data
                attrs = eval_data.attributes
            except AttributeError:
                self.report({'ERROR'}, f"Object '{obj.name}' has no exportable attribute data")
                continue

            selected_names = [a.name for a in s.attribute_list if a.use]
            if not selected_names:
                self.report({'WARNING'}, f"No attributes selected for export at frame {frame}")
                continue

            domain_counts = {
                'POINT': len(getattr(eval_data, 'points', [])) or len(getattr(eval_data, 'vertices', [])),
                'EDGE': len(getattr(eval_data, 'edges', [])),
                'FACE': len(getattr(eval_data, 'polygons', [])),
                'CORNER': len(getattr(eval_data, 'loops', [])),
                'CURVE': len(getattr(eval_data, 'splines', []))
            }

            count = domain_counts.get(s.domain, 0)
            if count == 0:
                self.report({'WARNING'}, f"No data found for domain {s.domain} at frame {frame}")
                continue
            

            data_columns = {}
            domain = s.domain
            base_obj = depsgraph.objects.get(obj.name, obj)
            attrs = base_obj.data.attributes
            selected_names = {a.name for a in s.attribute_list if a.use}
            count = len(base_obj.data.attributes.active.data) if domain == 'CORNER' else len(base_obj.data.vertices)

            for attr in attrs:
                if attr.domain != domain or attr.name not in selected_names or attr.name.startswith("."):
                    continue
                array = attr.data
                name = attr.name

                try:
                    sample = array[0]
                    if hasattr(sample, "vector"):
                        vec = sample.vector
                        if len(vec) == 2:
                            data_columns[f"{name}_x"] = [v.vector[0] for v in array]
                            data_columns[f"{name}_y"] = [v.vector[1] for v in array]
                        elif len(vec) == 3:
                            data_columns[f"{name}_x"] = [v.vector[0] for v in array]
                            data_columns[f"{name}_y"] = [v.vector[1] for v in array]
                            data_columns[f"{name}_z"] = [v.vector[2] for v in array]

                    elif hasattr(sample, "color"):
                        col = sample.color
                        data_columns[f"{name}_r"] = [v.color[0] for v in array]
                        data_columns[f"{name}_g"] = [v.color[1] for v in array]
                        data_columns[f"{name}_b"] = [v.color[2] for v in array]
                        if len(col) == 4:
                            data_columns[f"{name}_a"] = [v.color[3] for v in array]

                    elif hasattr(sample, "value"):
                        data_columns[name] = [v.value for v in array]

                    else:
                        print(f"Skipped unknown attribute type: {name}")

                except Exception as e:
                    print(f"Error processing attribute '{name}': {e}")

            # Handle all UV maps explicitly
            if domain == 'CORNER' and obj.type == 'MESH':
                for uv_layer in base_obj.data.uv_layers:
                    if uv_layer.name.startswith(".") or uv_layer.name not in selected_names:
                        continue
                    if uv_layer.name in selected_names:
                        uvs = uv_layer.data
                        data_columns[f"{uv_layer.name}_x"] = [uv.uv[0] for uv in uvs]
                        data_columns[f"{uv_layer.name}_y"] = [uv.uv[1] for uv in uvs]

            # CSV Writer
            header = list(data_columns.keys())
            rows = [
                [self.format_float(data_columns[k][i], s.float_precision)
                    if isinstance(data_columns[k][i], float) else data_columns[k][i]
                    for k in header]
                for i in range(count)
            ]

            outfile = os.path.join(path, f"{s.base_filename}_{frame:04d}.csv")
            with open(outfile, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)
    
        self.report({'INFO'}, f"CSV Export complete: {len(frame_range)} frame(s)")
        return {'FINISHED'}

# Attrio Import
    
class ATTRIO_OT_add_csv_import_object(Operator):
    bl_idname = "attrio.add_csv_import_object"
    bl_label = "Add CSV Import Object"
    bl_description = "Add object with AttrIO CSV Geometry Node Modifier"

    def execute(self, context):
        s = context.scene.attrio_csv_settings
        base_path = bpy.path.abspath(s.export_path)
        subfolder = s.subfolder
        file_name = s.base_filename
        target_dir = os.path.join(base_path, subfolder)

        # Check if any CSV files exist
        if not os.path.isdir(target_dir):
            self.report({'ERROR'}, f"Directory does not exist: {target_dir}")
            return {'CANCELLED'}

        found_csv = any(f.startswith(file_name) and f.endswith(".csv") for f in os.listdir(target_dir))
        if not found_csv:
            self.report({'ERROR'}, f"No CSV files named {file_name}_####.csv found in {subfolder}")
            return {'CANCELLED'}

        # Create new mesh object to hold data
        mesh = bpy.data.meshes.new("AttrioCSVMesh")
        obj = bpy.data.objects.new("AttrioCSVObject", mesh)
        context.collection.objects.link(obj)

        mod = obj.modifiers.new(name="AttrioCSV", type='NODES')

        # Load GN group if not already present
        gn_name = "AttrioPositionFromCSV"
        ensure_node_group(gn_name)
        if gn_name not in bpy.data.node_groups:
            # Assume a helper function exists to append from bundled .blend
            bpy.ops.attrio.append_gn_tree(name=gn_name)

        mod.node_group = bpy.data.node_groups.get(gn_name)

        # Set node group inputs if available
        try:
            mod["Socket_3"] = base_path
            mod["Socket_4"] = subfolder
            mod["Socket_5"] = file_name
        except KeyError:
            self.report({'WARNING'}, "Failed to set some GN inputs, verify naming")

        self.report({'INFO'}, f"Added object with {gn_name} node group modifier.")
        return {'FINISHED'}
    
class ATTRIO_OT_add_csv_pointcloud_object(bpy.types.Operator):
    bl_idname = "attrio.add_csv_pointcloud_object"
    bl_label = "Import Data as Point Cloud"
    bl_description = "Add object with AttrIO CSV Geometry Node Modifier (PointCloud mode)"

    def execute(self, context):
        s = context.scene.attrio_csv_settings
        base_path = bpy.path.abspath(s.export_path)
        subfolder = s.subfolder
        base_name = s.base_filename
        target_dir = os.path.join(base_path, subfolder)

        if not os.path.isdir(target_dir):
            self.report({'ERROR'}, f"Directory does not exist: {target_dir}")
            return {'CANCELLED'}

        found_valid = False
        for fname in os.listdir(target_dir):
            if fname.endswith(".csv"):
                name_part = fname.split("_")[0]
                if name_part == base_name:
                    found_valid = True
                    break

        if not found_valid:
            self.report({'ERROR'}, f"No valid CSV files found starting with '{base_name}_####.csv'")
            return {'CANCELLED'}

        # Create new mesh object
        mesh = bpy.data.meshes.new("AttrioDataMesh")
        obj = bpy.data.objects.new("AttrioDataObject", mesh)
        context.collection.objects.link(obj)

        # Add Geometry Nodes modifier
        ensure_node_group("AttrioPointData")
        mod = obj.modifiers.new(name="AttrioPointData", type='NODES')

        gn_name = "AttrioPointData"
        if gn_name not in bpy.data.node_groups:
            bpy.ops.attrio.append_gn_tree(name=gn_name)

        mod.node_group = bpy.data.node_groups.get(gn_name)

        try:
            mod["Socket_3"] = base_path
            mod["Socket_4"] = subfolder
            mod["Socket_5"] = base_name
        except KeyError:
            self.report({'WARNING'}, "Failed to set GN group inputs")

        self.report({'INFO'}, f"Added point cloud object using {gn_name} node group")
        return {'FINISHED'}

    
def register():
    bpy.utils.register_class(ATTRIO_PG_csv_settings)
    bpy.utils.register_class(EXPORT_OT_attrio_csv)
    bpy.utils.register_class(ATTRIO_OT_add_csv_import_object)
    bpy.utils.register_class(ATTRIO_OT_add_csv_pointcloud_object)
    bpy.types.Scene.attrio_csv_settings = PointerProperty(type=ATTRIO_PG_csv_settings)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_attrio_csv)
    bpy.utils.unregister_class(ATTRIO_PG_csv_settings)
    bpy.utils.unregister_class(ATTRIO_OT_add_csv_import_object)
    bpy.utils.unregister_class(ATTRIO_OT_add_csv_pointcloud_object)
    del bpy.types.Scene.attrio_csv_settings
