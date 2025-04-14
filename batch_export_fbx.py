# -*- coding: utf-8 -*-
# Use UTF-8 encoding

bl_info = {
    "name": "Batch FBX Exporter (Improved)",
    "blender": (3, 6, 0),  # Broadened compatibility
    "version": (1, 2, 0),  # Version with Selection Sync (Part 1)
    "author": "Evilmushroom (Core Fixes & LOD by AI)",
    "description": "Batch export multiple animations and objects (including LODs) to separate FBX files.",
    "category": "Object",
    "location": "3D View > Sidebar > Tool Tab",
    "doc_url": "https://github.com/evilmushroom/batch-fbx-exporter" # Your original URL
}


import bpy
import os
import traceback
import re # Import regular expressions module for LOD matching
# Ensure all necessary prop types are imported
from bpy.props import StringProperty, BoolProperty, PointerProperty, CollectionProperty, EnumProperty, IntProperty
from bpy.types import PropertyGroup, Operator, Panel, UIList # Import necessary types

# --- Core Export Function (with fixes) ---
# (No changes in this section)
def export_fbx(context, filepath, use_selection, bake_anim=False, bake_anim_use_all_actions=False):
    """Common FBX export function with Unreal-friendly settings and core fixes."""
    scene = context.scene # Use context passed to function

    # Store original unit settings and time
    original_unit_system = scene.unit_settings.system
    original_scale_length = scene.unit_settings.scale_length
    original_frame = scene.frame_current

    # Store original armature transforms
    armature = scene.character_armature
    original_location = None
    original_rotation = None
    original_scale = None
    original_pose_position = None

    if armature:
        original_location = armature.location.copy()
        original_rotation = armature.rotation_euler.copy()
        original_scale = armature.scale.copy()
        original_pose_position = armature.data.pose_position

        if not bake_anim:
            armature.location = (0, 0, 0)
            armature.rotation_euler = (0, 0, 0)
            armature.data.pose_position = 'REST'

    try:
        scene.unit_settings.system = 'METRIC'

        if not bake_anim:
            scene.frame_set(0)
        elif armature:
            armature.data.pose_position = 'POSE'

        # --- Perform FBX Export ---
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=use_selection,
            use_active_collection=False,
            use_mesh_modifiers=scene.use_mesh_modifiers,
            mesh_smooth_type=scene.mesh_smooth_type,
            use_mesh_edges=scene.use_mesh_edges,
            use_tspace=scene.use_tspace,
            bake_anim=bake_anim,
            bake_anim_use_all_actions=bake_anim_use_all_actions,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_bones=True,
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            axis_forward=scene.fbx_axis_forward,
            axis_up=scene.fbx_axis_up,
            bake_space_transform=True,
            use_subsurf=False,
            use_armature_deform_only=scene.use_armature_deform_only,
            path_mode='COPY',
            embed_textures=scene.embed_textures,
            batch_mode='OFF',
            use_batch_own_dir=False,
            use_metadata=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE'
        )
    finally:
        # Restore original settings
        scene.unit_settings.system = original_unit_system
        scene.unit_settings.scale_length = original_scale_length
        scene.frame_set(original_frame)

        # Restore armature transforms and pose position
        if armature:
             if original_location is not None: armature.location = original_location
             if original_rotation is not None: armature.rotation_euler = original_rotation
             if original_scale is not None: armature.scale = original_scale
             if original_pose_position is not None: armature.data.pose_position = original_pose_position


# Removed export_action function


# --- UI List Classes ---
# (No changes in this section)
class ACTION_UL_list(UIList):
    bl_idname = "ACTION_UL_batch_export_actions"
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        action = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            if hasattr(action, "export"): row.prop(action, "export", text="")
            else: row.label(text="", icon='ERROR')
            row.prop(action, "name", text="", emboss=False, icon_value=icon)
            op = row.operator("anim.set_active_action", text="", icon='PLAY'); op.action_name = action.name
            row.prop(action, "use_fake_user", text="", toggle=True) # Auto icon
        elif self.layout_type in {'GRID'}: layout.alignment = 'CENTER'; layout.label(text="", icon_value=icon)

class OBJECT_UL_character_objects(UIList):
    bl_idname = "OBJECT_UL_batch_export_meshes"
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        mesh_obj_item = item; obj = mesh_obj_item.object; row = layout.row(align=True)
        if obj:
             if obj.name in bpy.data.objects: row.prop(mesh_obj_item, "export", text=""); row.prop(obj, "name", text="", emboss=False, icon_value=layout.icon(obj))
             else: row.label(text=f"Missing: {obj.name}", icon='ERROR')
        else: row.label(text="Empty Slot", icon='QUESTION')


# --- Property Group ---
# (No changes in this section)
class MeshObject(PropertyGroup):
    object: PointerProperty(type=bpy.types.Object)
    export: BoolProperty(default=True)


# --- Operators ---
# (No changes in this section)
class ANIM_OT_set_active_action(Operator):
    bl_idname = "anim.set_active_action"; bl_label = "Set Active Action"; bl_description = "Set this action as the active one"
    action_name: StringProperty()
    def execute(self, context):
        armature = context.scene.character_armature
        if armature and armature.type == 'ARMATURE' and armature.animation_data:
            action = bpy.data.actions.get(self.action_name)
            if action:
                try: armature.animation_data.action = action; return {'FINISHED'}
                except Exception as e: self.report({'ERROR'}, f"Failed to set action: {e}"); return {'CANCELLED'}
        elif not armature or armature.type != 'ARMATURE': self.report({'ERROR'}, "Select the character armature in the panel first."); return {'CANCELLED'}
        else: self.report({'WARNING'}, "Selected armature has no Animation Data."); return {'CANCELLED'}
        return {'CANCELLED'}

class ANIM_OT_push_actions_to_nla(Operator):
    bl_idname = "anim.push_actions_to_nla"; bl_label = "Push Selected to NLA"; bl_description = "Push selected actions to NLA strips"
    @classmethod
    def poll(cls, context): armature = context.scene.character_armature; return armature and armature.type == 'ARMATURE'
    def execute(self, context):
        armature = context.scene.character_armature
        if not armature: self.report({'ERROR'}, "Select the character armature in the panel first."); return {'CANCELLED'}
        if not armature.animation_data:
             try: armature.animation_data_create()
             except Exception as e: self.report({'ERROR'}, f"Could not create Animation Data: {e}"); return {'CANCELLED'}
        pushed_count = 0; actions_to_push = [action for action in bpy.data.actions if getattr(action, "export", False)]
        if not actions_to_push: self.report({'WARNING'}, "No actions marked for export."); return {'CANCELLED'}
        for action in actions_to_push:
            existing_track = next((track for track in armature.animation_data.nla_tracks if track.strips and track.strips[0].action == action), None)
            if existing_track: armature.animation_data.nla_tracks.remove(existing_track)
            track = armature.animation_data.nla_tracks.new(); track.name = action.name
            start_frame = int(action.frame_range[0]); strip = track.strips.new(action.name, start_frame, action); strip.frame_end = int(action.frame_range[1])
            pushed_count += 1
        self.report({'INFO'}, f"Pushed {pushed_count} actions to NLA for '{armature.name}'"); return {'FINISHED'}

class ANIM_OT_delete_selected_actions(Operator):
    bl_idname = "anim.delete_selected_actions"; bl_label = "Delete Selected"; bl_description = "Delete selected actions"
    # NOTE: This operator currently uses Action.export, which will now be synced
    # If you want it to ONLY delete based on 'export' state, it's fine.
    # If you wanted it separate, it would need its own property.
    @classmethod
    def poll(cls, context): return any(getattr(action, "export", False) for action in bpy.data.actions) # Checks 'export'
    def invoke(self, context, event): return context.window_manager.invoke_confirm(self, event)
    def execute(self, context):
        actions_to_remove = [action for action in bpy.data.actions if getattr(action, "export", False)]; removed_count = 0 # Uses 'export'
        if not actions_to_remove: self.report({'WARNING'}, "No actions marked for export."); return {'CANCELLED'}
        for action in actions_to_remove:
             try: bpy.data.actions.remove(action, do_unlink=True); removed_count += 1
             except Exception as e: print(f"Error removing action {action.name}: {e}"); self.report({'WARNING'}, f"Could not remove action '{action.name}'.")
        if removed_count > 0: self.report({'INFO'}, f"Deleted {removed_count} actions."); context.area.tag_redraw()
        else: self.report({'WARNING'}, "No actions were deleted.")
        return {'FINISHED'}

class OBJECT_OT_character_object_add(Operator):
    bl_idname = "object.character_object_add"; bl_label = "Add Character Object"; bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.type == 'MESH'
    def execute(self, context):
        active_obj = context.active_object
        if active_obj:
             if any(item.object == active_obj for item in context.scene.character_objects): self.report({'WARNING'}, f"'{active_obj.name}' already in list."); return {'CANCELLED'}
             item = context.scene.character_objects.add(); item.object = active_obj
             context.scene.character_object_index = len(context.scene.character_objects) - 1; return {'FINISHED'}
        else: self.report({'WARNING'}, "No active mesh object selected."); return {'CANCELLED'}

class OBJECT_OT_character_object_remove(Operator):
    bl_idname = "object.character_object_remove"; bl_label = "Remove Character Object"; bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): scene = context.scene; return scene.character_objects and 0 <= scene.character_object_index < len(scene.character_objects)
    def execute(self, context):
        scene = context.scene; index = scene.character_object_index
        if 0 <= index < len(scene.character_objects):
            scene.character_objects.remove(index); scene.character_object_index = min(max(0, index - 1), len(scene.character_objects) - 1); return {'FINISHED'}
        else: self.report({'WARNING'}, "No item selected to remove."); return {'CANCELLED'}

class SCENE_OT_set_unreal_scale(Operator):
    bl_idname = "scene.set_unreal_scale"; bl_label = "Set Unit Scale to 0.01 (UE)"; bl_description = "Set the unit scale to 0.01 for Unreal Engine compatibility"; bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        old_scale = context.scene.unit_settings.scale_length; context.scene.unit_settings.system = 'METRIC'; context.scene.unit_settings.scale_length = 0.01
        if len(context.scene.objects) > 0 and abs(old_scale - 0.01) > 0.0001: self.report({'WARNING'}, "Scale changed from {:.4f} to 0.01. This may affect existing objects/rigs!".format(old_scale))
        else: self.report({'INFO'}, "Unit scale set to 0.01 for Unreal Engine compatibility")
        return {'FINISHED'}

# --- Main Export Operator (LOD Logic Added) ---
class OBJECT_OT_batch_export_fbx(Operator):
    """Batch Export FBX"""
    bl_idname = "export.batch_fbx"
    bl_label = "Batch Export FBX"
    bl_options = {'REGISTER', 'UNDO'}

    confirm_message: StringProperty()

    def invoke(self, context, event):
        # ... (Overwrite check logic unchanged) ...
        scene = context.scene; export_path = bpy.path.abspath(scene.batch_export_path); existing_files = []
        if not export_path: self.report({'ERROR'}, "Export Path not set."); return {'CANCELLED'}
        parent_dir = os.path.dirname(export_path);
        if not parent_dir or not os.path.exists(parent_dir): self.report({'ERROR'}, f"Base directory does not exist: {parent_dir}"); return {'CANCELLED'}
        armature = scene.character_armature; character_name = scene.character_name if scene.character_name.strip() else "Character"
        if scene.export_character:
            char_file = os.path.join(export_path, f"{character_name}.fbx")
            if os.path.exists(char_file): existing_files.append(os.path.basename(char_file))
        if scene.export_animations and armature:
            actions_to_export = [action for action in bpy.data.actions if getattr(action, "export", False)]
            for action in actions_to_export:
                anim_name = action.name if action.name.strip() else "UnnamedAnimation"
                anim_file = os.path.join(export_path, f"{anim_name}.fbx")
                if os.path.exists(anim_file): existing_files.append(os.path.basename(anim_file))
        if existing_files:
            num_files = len(existing_files); example_files = "\n - " + "\n - ".join(existing_files[:5]) if num_files > 0 else ""
            self.confirm_message = f"Overwrite {num_files} existing file(s)? {example_files}"
            return context.window_manager.invoke_props_dialog(self, width=400)
        else: return self.execute(context)

    def draw(self, context):
        # ... (dialog draw unchanged) ...
        layout = self.layout; col = layout.column()
        for i, line in enumerate(self.confirm_message.split('\n')): icon = 'ERROR' if i == 0 else 'NONE'; col.label(text=line, icon=icon)

    def execute(self, context):
        scene = context.scene; export_path = bpy.path.abspath(scene.batch_export_path)
        if not export_path or export_path.strip() == "": self.report({'ERROR'}, "No export path set"); return {'CANCELLED'}
        if not os.path.exists(export_path):
            try: os.makedirs(export_path)
            except Exception as e: self.report({'ERROR'}, f"Failed to create export directory: {e}"); return {'CANCELLED'}
        armature = scene.character_armature
        if (scene.export_character or scene.export_animations) and not armature: self.report({'ERROR'}, "No armature selected"); return {'CANCELLED'}
        if armature and armature.type != 'ARMATURE': self.report({'ERROR'}, f"'{armature.name}' is not an Armature object."); return {'CANCELLED'}

        original_active = context.view_layer.objects.active; original_selection = context.selected_objects[:]
        original_action = None; original_pose_position = None; temp_action = None
        if armature:
            if armature.animation_data: original_action = armature.animation_data.action
            original_pose_position = armature.data.pose_position

        export_count = 0; error_count = 0
        try:
            # --- Export character ---
            if scene.export_character:
                if not armature: self.report({'ERROR'}, "Armature needed for character export not selected."); return {'CANCELLED'}
                self.report({'INFO'}, "Starting character mesh export...")
                armature.data.pose_position = 'REST'

                # Get explicitly listed meshes (LOD0 / Base)
                explicit_meshes = []
                for item in scene.character_objects:
                    if item.object and item.export and item.object.name in scene.objects:
                        explicit_meshes.append(item.object)
                    elif item.object and item.export: self.report({'WARNING'}, f"Mesh '{item.object.name}' in list but not in scene. Skipping.")

                if not explicit_meshes: self.report({'WARNING'}, "Exporting character but no meshes selected in list.")

                # Start list with armature and explicit meshes
                objects_to_export = [armature] + explicit_meshes
                num_explicit = len(explicit_meshes)

                # --- LOD Detection Logic ---
                if scene.export_lods:
                    self.report({'INFO'}, "LOD export enabled, searching for LOD meshes...")
                    found_lods = []
                    # Regex to find _LOD followed by 1-9 and optional digits at the end
                    lod_pattern = re.compile(r"_LOD([1-9]\d*)$")

                    for obj in scene.objects:
                        # Check if it's a mesh, not already included, and visible in current view layer
                        if obj.type == 'MESH' and obj not in objects_to_export and obj.name in context.view_layer.objects:
                            # Check naming convention
                            if lod_pattern.search(obj.name):
                                # Check if skinned to the correct armature
                                is_skinned = False
                                for mod in obj.modifiers:
                                    if mod.type == 'ARMATURE' and mod.object == armature:
                                        is_skinned = True
                                        break
                                if is_skinned:
                                    found_lods.append(obj)

                    if found_lods:
                        self.report({'INFO'}, f"Found {len(found_lods)} additional LOD meshes matching pattern.")
                        objects_to_export.extend(found_lods)
                    else:
                         self.report({'WARNING'}, "LOD export enabled, but no additional LOD meshes found matching '_LODn' (n>0) pattern and skinned to selected armature.")
                # --- End LOD Detection ---

                # Clear animation data temporarily
                temp_action = None
                if armature.animation_data: temp_action = armature.animation_data.action; armature.animation_data.action = None

                # Select all objects for export (Armature + Explicit + Found LODs)
                bpy.ops.object.select_all(action='DESELECT')
                valid_selection = []
                for obj in objects_to_export:
                    try:
                        obj.select_set(True)
                        valid_selection.append(obj) # Keep track of successfully selected
                    except ReferenceError: self.report({'WARNING'}, f"Object '{obj.name}' not found for selection. Skipping.")

                if armature not in valid_selection:
                     self.report({'ERROR'}, "Armature could not be selected for export.")
                     # Decide if we should stop here or try animations
                else:
                    context.view_layer.objects.active = armature # Ensure armature active
                    char_name = scene.character_name if scene.character_name.strip() else "Character"
                    fbx_file = os.path.join(export_path, f"{char_name}.fbx")
                    try:
                        export_fbx(context, fbx_file, use_selection=True, bake_anim=False)
                        self.report({'INFO'}, f"Exported character: {os.path.basename(fbx_file)}")
                        export_count += 1
                    except Exception as e_char:
                        self.report({'ERROR'}, f"Failed exporting character: {e_char}"); error_count += 1; print(traceback.format_exc())

                # Restore animation data if cleared
                if armature.animation_data and temp_action: armature.animation_data.action = temp_action

            # --- Export animations ---
            if scene.export_animations:
                # ... (Animation export logic remains unchanged) ...
                if not armature: self.report({'ERROR'}, "Armature needed for animation export not selected."); return {'CANCELLED'}
                if not armature.animation_data: self.report({'WARNING'}, "Armature has no Animation Data. Cannot export animations.")
                else:
                    self.report({'INFO'}, "Starting animation export...")
                    armature.data.pose_position = 'POSE'
                    actions_to_export = [action for action in bpy.data.actions if getattr(action, "export", False)]
                    if not actions_to_export: self.report({'WARNING'}, "Animation export enabled, but no actions marked for export.")
                    else:
                        current_original_action = armature.animation_data.action
                        for action in actions_to_export:
                            bpy.ops.object.select_all(action='DESELECT')
                            try: armature.select_set(True); context.view_layer.objects.active = armature
                            except ReferenceError: self.report({'ERROR'}, f"Armature not found for exporting action '{action.name}'. Skipping."); error_count += 1; continue
                            armature.data.pose_position = 'POSE'
                            try: armature.animation_data.action = action; scene.frame_start = int(action.frame_range[0]); scene.frame_end = int(action.frame_range[1])
                            except Exception as e_set: self.report({'ERROR'}, f"Failed setting action/range for '{action.name}': {e_set}. Skipping."); error_count += 1; continue
                            fbx_file = os.path.join(export_path, f"{action.name}.fbx")
                            try: export_fbx(context, fbx_file, use_selection=True, bake_anim=True, bake_anim_use_all_actions=False); self.report({'INFO'}, f"Exported animation: {os.path.basename(fbx_file)}"); export_count += 1
                            except Exception as e_anim: self.report({'ERROR'}, f"Failed exporting animation '{action.name}': {e_anim}"); error_count += 1; print(traceback.format_exc())
                        # Check if current_original_action still exists before assigning
                        if armature.animation_data and current_original_action and current_original_action.name in bpy.data.actions:
                            armature.animation_data.action = current_original_action
                        elif armature.animation_data: # Assign None if original was deleted or invalid
                            armature.animation_data.action = None


        finally:
            # --- Restore original state ---
            if armature and original_pose_position is not None: armature.data.pose_position = original_pose_position
            # Action restore is handled after loop now, this is mostly redundant
            # if armature and armature.animation_data and original_action is not None:
            #      try:
            #          if original_action.name in bpy.data.actions: armature.animation_data.action = original_action
            #          else: armature.animation_data.action = None
            #      except Exception as e_restore: print(f"Could not fully restore original action state: {e_restore}")
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                try:
                    if obj and obj.name in context.view_layer.objects: obj.select_set(True)
                except ReferenceError: pass
            try:
                 if original_active and original_active.name in context.view_layer.objects: context.view_layer.objects.active = original_active
                 elif context.selected_objects: context.view_layer.objects.active = context.selected_objects[0]
                 else: context.view_layer.objects.active = None
            except ReferenceError: context.view_layer.objects.active = None

        # --- Final report ---
        if error_count > 0: self.report({'WARNING'}, f"Export finished with {error_count} errors. See console for details.")
        elif export_count == 0: self.report({'WARNING'}, "Export finished, but nothing was exported. Check settings.")
        else: self.report({'INFO'}, f"Batch export finished successfully ({export_count} files).")
        return {'FINISHED'}


# --- Panel ---
class OBJECT_PT_batch_export_fbx_panel(Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Batch FBX Export"
    bl_idname = "OBJECT_PT_batch_export_fbx_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    # bl_context = "objectmode"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Scale Warning ---
        is_correct_scale = abs(scene.unit_settings.scale_length - 0.01) < 0.001
        if not is_correct_scale:
            warning_box = layout.box()
            row = warning_box.row(); row.alert = True; row.label(text="⚠ Incorrect Unit Scale!", icon='ERROR')
            row = warning_box.row(); row.label(text=f"Current: {scene.unit_settings.scale_length:.4f}, Unreal requires: 0.01")
            op = warning_box.operator("scene.set_unreal_scale", icon='MODIFIER', text="Fix Scale Now")
            layout.separator()

        # --- Export Path ---
        layout.prop(scene, "batch_export_path")

        # --- Armature selection ---
        box = layout.box()
        box.prop(scene, "character_armature")

        # --- Character Export ---
        box_char = layout.box()
        row = box_char.row()
        row.prop(scene, "export_character", text="Export Character")
        char_options_enabled = scene.character_armature is not None
        row.active = char_options_enabled # Enable/disable based on armature selection

        if scene.export_character:
            inner_char_box = box_char.box()
            inner_char_box.enabled = char_options_enabled # Grey out options if no armature

            inner_char_box.prop(scene, "character_name")
            # *** ADDED LOD TOGGLE ***
            inner_char_box.prop(scene, "export_lods")
            inner_char_box.separator()

            row = inner_char_box.row()
            row.label(text="Meshes to Include (LOD0 / Base):") # Clarify list purpose
            row = inner_char_box.row()
            row.template_list(OBJECT_UL_character_objects.bl_idname, "", scene, "character_objects", scene, "character_object_index")
            col = row.column(align=True)
            col.operator("object.character_object_add", icon='ADD', text="")
            col.operator("object.character_object_remove", icon='REMOVE', text="")

        # --- Animation Export ---
        box_anim = layout.box()
        row = box_anim.row()
        row.prop(scene, "export_animations", text="Export Animations")
        anim_options_enabled = scene.character_armature is not None
        row.active = anim_options_enabled # Enable/disable based on armature selection

        if scene.export_animations:
            inner_anim_box = box_anim.box()
            inner_anim_box.enabled = anim_options_enabled # Grey out options if no armature

            row = inner_anim_box.row()
            row.prop(scene, "select_all_actions", text="Select All")
            row = inner_anim_box.row()
            row.template_list(ACTION_UL_list.bl_idname, "", bpy.data, "actions", scene, "action_index")
            row = inner_anim_box.row(align=True)
            row.operator("anim.push_actions_to_nla", text="Push to NLA", icon='NLA')
            row.operator("anim.delete_selected_actions", text="Delete Selected", icon='X')

        # --- Export options Toggle ---
        main_opts_box = layout.box()
        main_opts_box.prop(scene, "show_export_options")

        # --- Conditionally draw Export Options ---
        if scene.show_export_options:
            options_inner_box = main_opts_box.box()
            options_inner_box.label(text="Export Options:")

            # --- Axis Options ---
            row_axis = options_inner_box.row(align=True)
            row_axis.prop(scene, "fbx_axis_forward")
            row_axis.prop(scene, "fbx_axis_up")
            options_inner_box.separator()

            # --- Other Options ---
            options_inner_box.prop(scene, "use_mesh_modifiers")
            options_inner_box.prop(scene, "mesh_smooth_type")
            options_inner_box.prop(scene, "use_armature_deform_only")
            options_inner_box.prop(scene, "use_tspace")
            options_inner_box.prop(scene, "use_mesh_edges")
            options_inner_box.prop(scene, "embed_textures")

        # --- Export Button ---
        row = layout.row()
        row.scale_y = 1.5
        try:
             is_ready = False; has_path = bool(scene.batch_export_path)
             if has_path:
                 armature_selected = scene.character_armature is not None
                 exporting_requires_armature = scene.export_character or scene.export_animations
                 if (exporting_requires_armature and armature_selected) or (not exporting_requires_armature): is_ready = True
             row.enabled = is_ready
             row.operator("export.batch_fbx", text="Export FBX Batch")
        except Exception as e:
             print(f"ERROR drawing export button: {e}\n{traceback.format_exc()}")
             layout.label(text="Error drawing button!", icon='ERROR')


# --- Update Function for Syncing ---
# This function will be called when Action.export changes
def update_export_sync(self, context):
    """Updates Action.select if it exists and has a different value."""
    # Check if the 'select' property exists (i.e., Animation Manager is loaded)
    if hasattr(self, "select"):
        # Check if the value needs changing to prevent infinite loops
        if self.select != self.export:
            # print(f"SYNC: Setting 'select' from 'export' for {self.name} to {self.export}") # Optional Debug Print
            self.select = self.export # Update the 'select' property


# --- Utility Operators ---
# (No changes in this section)
def update_select_all(self, context):
    # This function now toggles Action.export, which will trigger the sync
    for action in bpy.data.actions: setattr(action, "export", self.select_all_actions)

class OBJECT_OT_character_object_add(Operator):
    bl_idname = "object.character_object_add"; bl_label = "Add Character Object"; bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): return context.active_object and context.active_object.type == 'MESH'
    def execute(self, context):
        active_obj = context.active_object
        if active_obj:
             if any(item.object == active_obj for item in context.scene.character_objects): self.report({'WARNING'}, f"'{active_obj.name}' already in list."); return {'CANCELLED'}
             item = context.scene.character_objects.add(); item.object = active_obj
             context.scene.character_object_index = len(context.scene.character_objects) - 1; return {'FINISHED'}
        else: self.report({'WARNING'}, "No active mesh object selected."); return {'CANCELLED'}

class OBJECT_OT_character_object_remove(Operator):
    bl_idname = "object.character_object_remove"; bl_label = "Remove Character Object"; bl_options = {'REGISTER', 'UNDO'}
    @classmethod
    def poll(cls, context): scene = context.scene; return scene.character_objects and 0 <= scene.character_object_index < len(scene.character_objects)
    def execute(self, context):
        scene = context.scene; index = scene.character_object_index
        if 0 <= index < len(scene.character_objects):
            scene.character_objects.remove(index); scene.character_object_index = min(max(0, index - 1), len(scene.character_objects) - 1); return {'FINISHED'}
        else: self.report({'WARNING'}, "No item selected to remove."); return {'CANCELLED'}

class SCENE_OT_set_unreal_scale(Operator):
    bl_idname = "scene.set_unreal_scale"; bl_label = "Set Unit Scale to 0.01 (UE)"; bl_description = "Set the unit scale to 0.01 for Unreal Engine compatibility"; bl_options = {'REGISTER', 'UNDO'}
    def execute(self, context):
        old_scale = context.scene.unit_settings.scale_length; context.scene.unit_settings.system = 'METRIC'; context.scene.unit_settings.scale_length = 0.01
        if len(context.scene.objects) > 0 and abs(old_scale - 0.01) > 0.0001: self.report({'WARNING'}, "Scale changed from {:.4f} to 0.01. This may affect existing objects/rigs!".format(old_scale))
        else: self.report({'INFO'}, "Unit scale set to 0.01 for Unreal Engine compatibility")
        return {'FINISHED'}

# --- Registration ---
# Define axis items tuple (used by both properties)
axis_items = ( ('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", ""), ('-X', "-X", ""), ('-Y', "-Y", ""), ('-Z', "-Z", ""),)

# Define list of classes to register
classes = ( ACTION_UL_list, ANIM_OT_set_active_action, ANIM_OT_push_actions_to_nla, ANIM_OT_delete_selected_actions, MeshObject, OBJECT_UL_character_objects, OBJECT_OT_character_object_add, OBJECT_OT_character_object_remove, OBJECT_OT_batch_export_fbx, OBJECT_PT_batch_export_fbx_panel, SCENE_OT_set_unreal_scale,)

def register():
    for cls in classes: bpy.utils.register_class(cls)

    # --- Scene Properties ---
    bpy.types.Scene.batch_export_path = StringProperty(name="Export Path", subtype='DIR_PATH', default="", description="Directory to export FBX files into")
    bpy.types.Scene.action_index = IntProperty()
    # --- Action Property Definition with Update Callback ---
    # Define Action.export and attach the update function
    bpy.types.Action.export = BoolProperty(
        name="Export Action", # Name used in tooltips etc.
        description="Include this action in the batch export / sync with Animation Manager selection",
        default=True,
        update=update_export_sync # Assign the update function
        )
    # --- End Action Property Definition ---
    bpy.types.Scene.select_all_actions = BoolProperty(name="Select All", description="Select or deselect all actions for export", default=True, update=update_select_all) # Note: update_select_all now affects Action.export
    bpy.types.Scene.use_mesh_modifiers = BoolProperty(name="Apply Modifiers", description="Apply modifiers to mesh objects", default=True)
    bpy.types.Scene.mesh_smooth_type = EnumProperty(name="Smoothing", items=[('OFF', 'Off', 'Don\'t write smoothing'), ('FACE', 'Face', 'Write face smoothing'), ('EDGE', 'Edge', 'Write edge smoothing')], default='FACE')
    bpy.types.Scene.use_mesh_edges = BoolProperty(name="Include Edges", description="Include mesh edges in the export", default=False)
    bpy.types.Scene.use_tspace = BoolProperty(name="Tangent Space", description="Add binormal and tangent vectors", default=False)
    bpy.types.Scene.export_character = BoolProperty(name="Export Character", description="Export the character (skeletal mesh and associated meshes)", default=True)
    bpy.types.Scene.character_name = StringProperty(name="Character Name", description="Name of the character for export", default="Character")
    bpy.types.Scene.character_objects = CollectionProperty(type=MeshObject)
    bpy.types.Scene.character_object_index = IntProperty()
    bpy.types.Scene.export_animations = BoolProperty(name="Export Animations", description="Export animations", default=True)
    bpy.types.Scene.character_armature = PointerProperty(type=bpy.types.Object, name="Character Armature", description="Select the armature for the character", poll=lambda self, obj: obj.type == 'ARMATURE')
    bpy.types.Scene.use_armature_deform_only = BoolProperty(name="Deform Bones Only", description="Export only deformation bones (skip control bones)", default=True)
    bpy.types.Scene.embed_textures = BoolProperty(name="Embed Textures", description="Embed texture files within the FBX", default=False)
    bpy.types.Scene.show_export_options = BoolProperty(name="Show Advanced Export Options", description="Show detailed FBX export settings like axis orientation", default=False)
    bpy.types.Scene.fbx_axis_forward = EnumProperty(name="Forward", description="Forward axis for FBX export", items=axis_items, default='-Y')
    bpy.types.Scene.fbx_axis_up = EnumProperty(name="Up", description="Up axis for FBX export", items=axis_items, default='Z')
    bpy.types.Scene.export_lods = BoolProperty(name="Export LODs (by Name)", description="Automatically find and include meshes named _LOD1, _LOD2, etc., skinned to the same armature", default=False)


def unregister():
    # --- Delete Custom Properties ---
    props_to_delete = [
        "batch_export_path", "action_index", "select_all_actions",
        "use_mesh_modifiers", "mesh_smooth_type", "use_mesh_edges", "use_tspace",
        "export_character", "character_name", "character_objects", "character_object_index",
        "export_animations", "character_armature", "use_armature_deform_only",
        "embed_textures", "show_export_options", "fbx_axis_forward", "fbx_axis_up",
        "export_lods"
    ]
    for prop in props_to_delete:
        try: delattr(bpy.types.Scene, prop)
        except AttributeError: pass
    # Delete Action property safely
    if hasattr(bpy.types.Action, "export"):
        try: del bpy.types.Action.export
        except Exception as e: print(f"Could not delete Action.export: {e}")

    # --- Unregister Classes ---
    for cls in reversed(classes):
        try: bpy.utils.unregister_class(cls)
        except RuntimeError: print(f"Could not unregister class: {cls.__name__}")


if __name__ == "__main__":
    try: unregister()
    except Exception as e: print(f"Unregistration failed silently: {e}")
    register()
