bl_info = {
    "name": "Batch FBX Exporter",
    "blender": (3, 6, 9),  # Ensure this is the correct Blender version
    "version": (1, 0, 0),  # Versioning helps track updates
    "author": "Evilmushroom",  # Replace with your actual name or username
    "description": "Batch export multiple animations and objects to separate FBX files with Unreal-friendly settings.",
    "category": "Object",
    "location": "3D View > Sidebar > Tool Tab",
    "doc_url": "https://github.com/evilmushroom/batch-fbx-exporter"
}


import bpy
import os
import traceback
from bpy.props import StringProperty, BoolProperty, PointerProperty, CollectionProperty, EnumProperty
from bpy.types import PropertyGroup

def export_fbx(filepath, use_selection, bake_anim=False, bake_anim_use_all_actions=False):
    """Common FBX export function with Unreal-friendly settings."""
    # Store original unit settings and time
    original_unit_system = bpy.context.scene.unit_settings.system
    original_scale_length = bpy.context.scene.unit_settings.scale_length
    original_frame = bpy.context.scene.frame_current
    
    # Store original armature transforms
    armature = bpy.context.scene.character_armature
    original_location = None
    original_rotation = None
    original_scale = None
    
    if armature:
        original_location = armature.location.copy()
        original_rotation = armature.rotation_euler.copy()
        original_scale = armature.scale.copy()
        
        # Reset armature transforms for mesh export
        if not bake_anim:
            armature.location = (0, 0, 0)
            armature.rotation_euler = (0, 0, 0)
            # Don't reset scale as it might be intentional

    try:
        # Set unit settings for export
        bpy.context.scene.unit_settings.system = 'METRIC'
        #bpy.context.scene.unit_settings.scale_length = 1

        # If exporting mesh (not animation), ensure we're at frame 0
        if not bake_anim:
            bpy.context.scene.frame_set(0)

        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=use_selection,
            use_active_collection=False,
            use_mesh_modifiers=bpy.context.scene.use_mesh_modifiers,
            mesh_smooth_type=bpy.context.scene.mesh_smooth_type,
            use_mesh_edges=bake_anim,
            use_tspace=bake_anim,
            bake_anim=bake_anim,
            bake_anim_use_all_actions=bake_anim_use_all_actions,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_bones=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=1.0,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            axis_forward='-Z',
            axis_up='Y',
            bake_space_transform=True,
            use_subsurf=False,
            use_armature_deform_only=bpy.context.scene.use_armature_deform_only,
            use_custom_props=True,
            path_mode='COPY',
            embed_textures=True,
            batch_mode='OFF',
            use_batch_own_dir=False,
            use_metadata=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE'
        )
    finally:
        # Restore original settings
        bpy.context.scene.unit_settings.system = original_unit_system
        bpy.context.scene.unit_settings.scale_length = original_scale_length
        bpy.context.scene.frame_set(original_frame)
        
        # Restore armature transforms
        if armature and original_location is not None:
            armature.location = original_location
            armature.rotation_euler = original_rotation
            armature.scale = original_scale

def export_action(obj, action, export_path):
    """Export the given action as an FBX file with scaled animation."""
    original_action = obj.animation_data.action
    original_use_nla = obj.animation_data.use_nla

    try:
        # Disable NLA temporarily
        obj.animation_data.use_nla = False
        
        # Set the current action
        obj.animation_data.action = action
        
        # Set the frame range to the action's frame range
        bpy.context.scene.frame_start = int(action.frame_range[0])
        bpy.context.scene.frame_end = int(action.frame_range[1])

        # Define a scale factor for the animation (100 for cm to m conversion)
        scale_factor = bpy.context.scene.unit_settings.scale_length * 100

        # Create a temporary action to store scaled keyframes
        temp_action = action.copy()
        obj.animation_data.action = temp_action

        # Scale the keyframes for the animation
        for fcurve in temp_action.fcurves:
            if fcurve.data_path.startswith('pose.bones'):
                for keyframe in fcurve.keyframe_points:
                    print(f"Original Keyframe Value: {keyframe.co[1]}")  # Debugging statement
                    keyframe.co[1] *= scale_factor  # Scale Y coordinate (value)
                    print(f"Scaled Keyframe Value: {keyframe.co[1]}")  # Debugging statement
                fcurve.update()

        action_name = action.name
        fbx_file = os.path.join(export_path, action_name + ".fbx")

        # Create export settings dictionary
        export_settings = {
            'global_scale': 1.0,  # Ensure this is set to 1.0 for the mesh
            'bake_anim': True,
            'bake_anim_use_all_actions': False,
            # Add any other necessary export settings here
        }

        # Export the action using the common export function
        export_fbx(fbx_file, use_selection=bpy.context.scene.limit_to_selected, **export_settings)
        
        return True, ""
    except Exception as e:
        return False, f"Error exporting {action.name}: {str(e)}\n{traceback.format_exc()}"
    finally:
        # Restore original action and NLA state
        obj.animation_data.action = original_action
        obj.animation_data.use_nla = original_use_nla

def process_root_motion(armature, root_bone_name, action):
    """Convert root bone movement to armature object movement (Blender-only fix)"""
    if not armature or not root_bone_name or not action:
        return action
    
    # Create new action for modified animation
    root_action = action.copy()
    root_bone = armature.pose.bones.get(root_bone_name)
    
    # Get rest matrix in world space
    armature_matrix = armature.matrix_world
    rest_matrix = armature_matrix @ root_bone.bone.matrix_local
    
    # Blender to Unreal scale conversion
    scale_factor = 1
    
    # Process all keyframes
    for fcurve in root_action.fcurves:
        if fcurve.data_path == f'pose.bones["{root_bone_name}"].location':
            for keyframe in fcurve.keyframe_points:
                # Get bone's world position at this frame
                bone_matrix = armature_matrix @ root_bone.matrix
                world_loc = bone_matrix.translation
                
                # Convert to armature object movement with scale fix
                delta = (world_loc - rest_matrix.translation) * scale_factor
                
                # Apply to armature with axis conversion (Y-forward to X-forward)
                armature.location.x = delta.y  # Blender Y → Unreal X
                armature.location.y = delta.x  # Blender X → Unreal Y
                armature.location.z = delta.z  # Z-up remains same
                
                # Zero out bone position
                keyframe.co[1] = 0
                
    return root_action

class ACTION_UL_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "export", text="")
            row.prop(item, "name", text="", emboss=False, icon_value=icon)
            
            # Play button
            op = row.operator("anim.set_active_action", text="", icon='PLAY')
            op.action_name = item.name
            
            # Fake User button
            row.prop(item, "use_fake_user", text="", toggle=True)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class ANIM_OT_set_active_action(bpy.types.Operator):
    bl_idname = "anim.set_active_action"
    bl_label = "Set Active Action"
    bl_description = "Set this action as the active one"
    
    action_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = context.object
        if obj and obj.animation_data:
            action = bpy.data.actions.get(self.action_name)
            if action:
                obj.animation_data.action = action
        return {'FINISHED'}

class ANIM_OT_push_actions_to_nla(bpy.types.Operator):
    bl_idname = "anim.push_actions_to_nla"
    bl_label = "Push Selected to NLA"
    bl_description = "Push selected actions to NLA strips"

    def execute(self, context):
        obj = context.object
        if obj and obj.animation_data:
            # Create a new NLA track for each selected action
            for action in bpy.data.actions:
                if action.export:
                    # Check if a track for this action already exists
                    existing_track = next((track for track in obj.animation_data.nla_tracks if track.strips and track.strips[0].action == action), None)
                    
                    if existing_track:
                        # If a track exists, remove it to avoid duplicates
                        obj.animation_data.nla_tracks.remove(existing_track)
                    
                    # Create a new track
                    track = obj.animation_data.nla_tracks.new()
                    track.name = action.name
                    
                    # Create a new strip in the track
                    start_frame = int(action.frame_range[0])
                    strip = track.strips.new(action.name, start_frame, action)
                    
                    # Set the strip's frame range
                    strip.frame_start = start_frame
                    strip.frame_end = int(action.frame_range[1])
        
        self.report({'INFO'}, f"Pushed {sum(1 for action in bpy.data.actions if action.export)} actions to NLA")
        return {'FINISHED'}

class ANIM_OT_delete_selected_actions(bpy.types.Operator):
    bl_idname = "anim.delete_selected_actions"
    bl_label = "Delete Selected"
    bl_description = "Delete selected actions"

    def execute(self, context):
        actions_to_remove = [action for action in bpy.data.actions if action.export]
        for action in actions_to_remove:
            bpy.data.actions.remove(action)
        return {'FINISHED'}

class MeshObject(PropertyGroup):
    object: PointerProperty(type=bpy.types.Object)
    export: BoolProperty(default=True)

class OBJECT_OT_batch_export_fbx(bpy.types.Operator):
    """Batch Export FBX"""
    bl_idname = "export.batch_fbx"
    bl_label = "Batch Export FBX"
    bl_options = {'REGISTER', 'UNDO'}
    
    confirm_message: bpy.props.StringProperty()

    def invoke(self, context, event):
        export_path = bpy.path.abspath(context.scene.batch_export_path)
        existing_files = []
        
        # Check character file
        if context.scene.export_character:
            char_file = os.path.join(export_path, f"{context.scene.character_name}_Character.fbx")
            if os.path.exists(char_file):
                existing_files.append(char_file)
        
        # Check animation files
        if context.scene.export_animations:
            for action in bpy.data.actions:
                if getattr(action, "export", True):
                    anim_file = os.path.join(export_path, f"{action.name}.fbx")
                    if os.path.exists(anim_file):
                        existing_files.append(anim_file)
        
        if existing_files:
            self.confirm_message = f"Overwrite {len(existing_files)} existing files?"
            return context.window_manager.invoke_props_dialog(self, width=400)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.confirm_message, icon='ERROR')

    def execute(self, context):
        export_path = bpy.path.abspath(context.scene.batch_export_path)
        if not export_path or export_path.strip() == "":
            self.report({'ERROR'}, "No export path set")
            return {'CANCELLED'}

        if not os.path.exists(export_path):
            try:
                os.makedirs(export_path)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to create export directory: {e}")
                return {'CANCELLED'}

        armature = context.scene.character_armature
        if not armature:
            self.report({'ERROR'}, "No armature selected")
            return {'CANCELLED'}

        # Store the original state
        original_action = armature.animation_data.action if armature.animation_data else None
        original_pose_position = armature.data.pose_position
        temp_action = None  # Initialize temp_action variable

        try:
            # Export character (skeletal mesh only) in rest pose
            if context.scene.export_character:
                # Set to REST position for mesh export
                armature.data.pose_position = 'REST'
                
                character_objects = [obj.object for obj in context.scene.character_objects if obj.export]
                if character_objects:
                    character_objects.append(armature)
                    
                    # Clear animation data temporarily
                    if armature.animation_data:
                        temp_action = armature.animation_data.action
                        armature.animation_data.action = None
                    
                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in character_objects:
                        obj.select_set(True)
                    context.view_layer.objects.active = armature
                    
                    fbx_file = os.path.join(export_path, f"{context.scene.character_name}_Character.fbx")
                    export_fbx(fbx_file, use_selection=True, bake_anim=False)
                    
                    # Restore the animation data if it was cleared
                    if armature.animation_data and temp_action:
                        armature.animation_data.action = temp_action
                    
                    self.report({'INFO'}, f"Exported character in rest pose: {fbx_file} (overwritten)" if os.path.exists(fbx_file) else f"Exported character in rest pose: {fbx_file}")

            # Export animations
            if context.scene.export_animations:
                # Set back to POSE position for animation export
                armature.data.pose_position = 'POSE'
                
                if armature.animation_data:
                    actions = [action for action in bpy.data.actions if getattr(action, "export", True)]

                    if not actions:
                        self.report({'WARNING'}, "No actions selected for export")
                    else:
                        for action in actions:
                            bpy.ops.object.select_all(action='DESELECT')
                            armature.select_set(True)
                            context.view_layer.objects.active = armature
                            
                            # Ensure we're in the right pose mode
                            armature.data.pose_position = 'POSE'
                            
                            # Set the current action
                            armature.animation_data.action = action
                            
                            # Set the frame range
                            context.scene.frame_start = int(action.frame_range[0])
                            context.scene.frame_end = int(action.frame_range[1])
                            
                            fbx_file = os.path.join(export_path, f"{action.name}.fbx")
                            export_fbx(
                                fbx_file, 
                                use_selection=True, 
                                bake_anim=True, 
                                bake_anim_use_all_actions=False
                            )
                            self.report({'INFO'}, f"Exported animation: {fbx_file}")
                else:
                    self.report({'WARNING'}, "Selected armature has no animation data")

        finally:
            # Restore original state
            armature.data.pose_position = original_pose_position
            if original_action and armature.animation_data:
                armature.animation_data.action = original_action

        return {'FINISHED'}



class OBJECT_UL_character_objects(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = item.object
        if ob:
            layout.prop(item, "export", text="")
            layout.prop(ob, "name", text="", emboss=False, icon_value=layout.icon(ob))
        else:
            layout.label(text="", icon='OBJECT_DATA')

class OBJECT_PT_batch_export_fbx_panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Batch FBX Export"
    bl_idname = "OBJECT_PT_batch_export_fbx_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Check if scale is incorrect and show warning button if needed
        is_correct_scale = abs(scene.unit_settings.scale_length - 0.01) < 0.001
        if not is_correct_scale:
            warning_box = layout.box()
            row = warning_box.row()
            row.alert = True
            row.label(text="⚠ Incorrect Unit Scale!", icon='ERROR')
            row = warning_box.row()
            row.label(text=f"Current: {scene.unit_settings.scale_length}, Unreal requires: 0.01")
            op = warning_box.operator("scene.set_unreal_scale", icon='MODIFIER')
            layout.separator()
        
        layout.prop(scene, "batch_export_path")
        
        # Armature selection (moved outside of character export)
        box = layout.box()
        box.prop(scene, "character_armature")
        
        # Character Export
        box = layout.box()
        row = box.row()
        row.prop(scene, "export_character", text="Export Character")
        if scene.export_character:
            box.prop(scene, "character_name")
            row = box.row()
            row.template_list("OBJECT_UL_character_objects", "", scene, "character_objects", scene, "character_object_index")
            col = row.column(align=True)
            col.operator("object.character_object_add", icon='ADD', text="")
            col.operator("object.character_object_remove", icon='REMOVE', text="")

        # Animation Export
        box = layout.box()
        row = box.row()
        row.prop(scene, "export_animations", text="Export Animations")
        if scene.export_animations:
            row = box.row()
            row.prop(scene, "select_all_actions", text="Select All")
            
            row = box.row()
            row.template_list("ACTION_UL_list", "", bpy.data, "actions", scene, "action_index")
            
            row = box.row(align=True)
            row.operator("anim.push_actions_to_nla", text="Push to NLA", icon='NLA')
            row.operator("anim.delete_selected_actions", text="Delete Selected", icon='X')
        
        # Export options
        box = layout.box()
        box.label(text="Export Options:")
        box.prop(scene, "limit_to_selected")
        box.prop(scene, "use_mesh_modifiers")
        box.prop(scene, "mesh_smooth_type")
        box.prop(scene, "use_mesh_edges")
        box.prop(scene, "use_tspace")
        box.prop(scene, "use_armature_deform_only")
        
        # Root Motion Settings
        box = layout.box()
        box.label(text="Root Motion Settings:")
        box.prop(scene, "enable_root_motion")
        if scene.enable_root_motion:
            box.prop_search(scene, "root_motion_bone", scene.character_armature.data, "bones", text="Root Bone")
            box.prop(scene, "root_motion_up_axis")
            box.prop(scene, "bake_root_z_rotation")
        
        row = layout.row()
        row.operator("export.batch_fbx", text="Export FBX Batch")

def update_select_all(self, context):
    for action in bpy.data.actions:
        action.export = self.select_all_actions

def apply_scale_to_selected():
    """Apply scale to selected objects."""
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

class OBJECT_OT_apply_scale(bpy.types.Operator):
    bl_idname = "object.apply_scale"
    bl_label = "Apply Scale"
    bl_description = "Apply scale to selected objects"

    def execute(self, context):
        apply_scale_to_selected()
        return {'FINISHED'}

class OBJECT_OT_character_object_add(bpy.types.Operator):
    bl_idname = "object.character_object_add"
    bl_label = "Add Character Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            item = context.scene.character_objects.add()
            item.object = context.active_object
        return {'FINISHED'}

class OBJECT_OT_character_object_remove(bpy.types.Operator):
    bl_idname = "object.character_object_remove"
    bl_label = "Remove Character Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.character_objects.remove(scene.character_object_index)
        scene.character_object_index = min(max(0, scene.character_object_index - 1), len(scene.character_objects) - 1)
        return {'FINISHED'}

class SCENE_OT_set_unreal_scale(bpy.types.Operator):
    bl_idname = "scene.set_unreal_scale"
    bl_label = "Fix Scale Now (May Affect Existing Rigs!)"
    bl_description = "Set the unit scale to 0.01 for Unreal Engine compatibility"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Store current scale for warning message
        old_scale = context.scene.unit_settings.scale_length
        
        # Set unit system and scale
        context.scene.unit_settings.system = 'METRIC'
        context.scene.unit_settings.scale_length = 0.01
        
        # Warning if scene already has content
        if len([obj for obj in context.scene.objects if obj.type == 'ARMATURE']) > 0:
            self.report({'WARNING'}, 
                "Scale changed from {:.4f} to 0.01. This will affect existing rigs! Consider starting over with the correct scale.".format(old_scale))
        else:
            self.report({'INFO'}, "Unit scale set to 0.01 for Unreal Engine compatibility")
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ACTION_UL_list)
    bpy.utils.register_class(ANIM_OT_set_active_action)
    bpy.utils.register_class(ANIM_OT_push_actions_to_nla)
    bpy.utils.register_class(ANIM_OT_delete_selected_actions)
    bpy.utils.register_class(MeshObject)
    bpy.utils.register_class(OBJECT_UL_character_objects)
    bpy.utils.register_class(OBJECT_OT_character_object_add)
    bpy.utils.register_class(OBJECT_OT_character_object_remove)
    bpy.utils.register_class(OBJECT_OT_batch_export_fbx)
    bpy.utils.register_class(OBJECT_PT_batch_export_fbx_panel)
    bpy.utils.register_class(OBJECT_OT_apply_scale)
    bpy.utils.register_class(SCENE_OT_set_unreal_scale)
    bpy.types.Scene.batch_export_path = StringProperty(
        name="Export Path",
        subtype='DIR_PATH',
        default="",
        description="Directory to export FBX files to"
    )
    bpy.types.Scene.action_index = bpy.props.IntProperty()
    bpy.types.Action.export = BoolProperty(default=True)
    bpy.types.Scene.select_all_actions = BoolProperty(
        name="Select All",
        description="Select or deselect all actions",
        default=True,
        update=update_select_all
    )
    bpy.types.Scene.limit_to_selected = BoolProperty(name="Limit to Selected", description="Export only selected objects", default=True)
    bpy.types.Scene.use_mesh_modifiers = BoolProperty(name="Apply Modifiers", description="Apply modifiers to mesh objects", default=True)
    bpy.types.Scene.mesh_smooth_type = bpy.props.EnumProperty(name="Smoothing", items=[('OFF', 'Off', 'Don\'t write smoothing'), ('FACE', 'Face', 'Write face smoothing'), ('EDGE', 'Edge', 'Write edge smoothing')], default='FACE')
    bpy.types.Scene.use_mesh_edges = BoolProperty(name="Include Edges", description="Include mesh edges in the export", default=False)
    bpy.types.Scene.use_tspace = BoolProperty(name="Tangent Space", description="Add binormal and tangent vectors, together with normal they form the tangent space", default=False)
    bpy.types.Scene.apply_scale_options = bpy.props.EnumProperty(name="Apply Scale", items=[('FBX_SCALE_NONE', 'All Local', 'Apply custom scale and units scaling to each object'), ('FBX_SCALE_UNITS', 'FBX Units Scale', 'Apply custom scale to FBX scale, and units scaling to each object'), ('FBX_SCALE_CUSTOM', 'FBX Custom Scale', 'Apply custom scale to FBX scale, and units scaling to each object'), ('FBX_SCALE_ALL', 'FBX All', 'Apply custom scale and units scaling to FBX scale')], default='FBX_SCALE_NONE')
    bpy.types.Scene.export_character = BoolProperty(
        name="Export Character",
        description="Export the character (skeletal mesh and associated meshes)",
        default=True
    )
    bpy.types.Scene.character_name = StringProperty(
        name="Character Name",
        description="Name of the character for export",
        default="Character"
    )
    bpy.types.Scene.character_objects = CollectionProperty(type=MeshObject)
    bpy.types.Scene.character_object_index = bpy.props.IntProperty()
    bpy.types.Scene.export_animations = BoolProperty(
        name="Export Animations",
        description="Export animations",
        default=True
    )
    bpy.types.Scene.character_armature = PointerProperty(
        type=bpy.types.Object,
        name="Character Armature",
        description="Select the armature for the character"
    )
    bpy.types.Scene.use_armature_deform_only = BoolProperty(
        name="Deform Bones Only",
        description="Export only deformation bones (skip control bones)",
        default=True
    )
    bpy.types.Scene.enable_root_motion = BoolProperty(
        name="Extract Root Motion",
        description="Bake root bone movement to armature object",
        default=False
    )
    bpy.types.Scene.root_motion_bone = StringProperty(
        name="Root Bone",
        description="Bone to use for root motion extraction",
        default=""
    )
    bpy.types.Scene.root_motion_up_axis = EnumProperty(
        name="Up Axis",
        items=[('Y', 'Y Up (Blender)', ''), ('Z', 'Z Up (Unreal)', '')],
        default='Z'
    )
    bpy.types.Scene.bake_root_z_rotation = BoolProperty(
        name="Bake Z Rotation",
        description="Convert root bone rotation to forward movement",
        default=True
    )

def unregister():
    bpy.utils.unregister_class(ACTION_UL_list)
    bpy.utils.unregister_class(ANIM_OT_set_active_action)
    bpy.utils.unregister_class(ANIM_OT_push_actions_to_nla)
    bpy.utils.unregister_class(ANIM_OT_delete_selected_actions)
    bpy.utils.unregister_class(MeshObject)
    bpy.utils.unregister_class(OBJECT_UL_character_objects)
    bpy.utils.unregister_class(OBJECT_OT_character_object_add)
    bpy.utils.unregister_class(OBJECT_OT_character_object_remove)
    bpy.utils.unregister_class(OBJECT_OT_batch_export_fbx)
    bpy.utils.unregister_class(OBJECT_PT_batch_export_fbx_panel)
    bpy.utils.unregister_class(OBJECT_OT_apply_scale)
    bpy.utils.unregister_class(SCENE_OT_set_unreal_scale)
    del bpy.types.Scene.batch_export_path
    del bpy.types.Scene.action_index
    del bpy.types.Action.export
    del bpy.types.Scene.select_all_actions
    del bpy.types.Scene.limit_to_selected
    del bpy.types.Scene.use_mesh_modifiers
    del bpy.types.Scene.mesh_smooth_type
    del bpy.types.Scene.use_mesh_edges
    del bpy.types.Scene.use_tspace
    del bpy.types.Scene.apply_scale_options
    del bpy.types.Scene.export_character
    del bpy.types.Scene.character_name
    del bpy.types.Scene.character_objects
    del bpy.types.Scene.character_object_index
    del bpy.types.Scene.export_animations
    del bpy.types.Scene.character_armature
    del bpy.types.Scene.use_armature_deform_only
    del bpy.types.Scene.enable_root_motion
    del bpy.types.Scene.root_motion_bone
    del bpy.types.Scene.root_motion_up_axis
    del bpy.types.Scene.bake_root_z_rotation

if __name__ == "__main__":
    register()
