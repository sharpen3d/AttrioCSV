import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, BoolProperty, CollectionProperty

class ATTRIO_UL_attribute_item(PropertyGroup):
    name: StringProperty()
    use: BoolProperty(default=True)

class ATTRIO_OT_refresh_attributes(Operator):
    bl_idname = "attrio.refresh_attributes"
    bl_label = "Refresh Attribute List"

    def execute(self, context):
        s = context.scene.attrio_csv_settings
        s.attribute_list.clear()

        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)

        try:
            attrs = eval_obj.data.attributes
        except AttributeError:
            self.report({'WARNING'}, "Selected object type has no attributes")
            return {'CANCELLED'}

        for attr in attrs:
            if attr.name == ".selection":
                continue
            if attr.name == ".select_vert":
                continue
            if attr.domain == s.domain:
                item = s.attribute_list.add()
                item.name = attr.name
                item.use = True

        return {'FINISHED'}

def register():
    bpy.utils.register_class(ATTRIO_UL_attribute_item)
    bpy.utils.register_class(ATTRIO_OT_refresh_attributes)

def unregister():
    bpy.utils.unregister_class(ATTRIO_OT_refresh_attributes)
    bpy.utils.unregister_class(ATTRIO_UL_attribute_item)
