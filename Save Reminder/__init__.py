bl_info = {
    "name": "Save Reminder",
    "author": "Logan Sergeant",
    "version": (1, 7),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Save Reminder",
    "description": "Periodic popup reminders to save your work, with quick save and incremental save options for people that forget to save",
    "category": "3D View",
}

import bpy
import time
import os
from bpy.types import AddonPreferences
from bpy.props import IntProperty, FloatProperty, BoolProperty


# ------------------------------
# Globals
# ------------------------------
is_enabled = False


# ------------------------------
# Preferences
# ------------------------------
class SaveReminderPreferences(AddonPreferences):
    bl_idname = __name__

    reminder_interval: IntProperty(
        name="Save Reminder Minutes",
        description="Time between save reminders",
        default=5,
        min=1,
        max=120
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "reminder_interval")


# ------------------------------
# Operators
# ------------------------------
class SAVEREMINDER_OT_toggle_reminder(bpy.types.Operator):
    """Toggle the save reminder on/off"""
    bl_idname = "savereminder.toggle_reminder"
    bl_label = "Toggle Reminder"

    def execute(self, context):
        global is_enabled
        is_enabled = not is_enabled
        prefs = bpy.context.preferences.addons[__name__].preferences

        if is_enabled:
            self.report({'INFO'}, f"Save reminder enabled - Every {prefs.reminder_interval} minutes")
            bpy.context.window_manager.savereminder_last_save_time = time.time()
        else:
            self.report({'INFO'}, "Save reminder disabled")
        return {'FINISHED'}


class SAVEREMINDER_OT_save_direct(bpy.types.Operator):
    """Immediately save the current .blend"""
    bl_idname = "savereminder.save_direct"
    bl_label = "Save Now"

    def execute(self, context):
        wm = context.window_manager
        if bpy.data.filepath:
            result = bpy.ops.wm.save_mainfile()
            if 'FINISHED' in result:
                filename = os.path.basename(bpy.data.filepath)
                self.report({'INFO'}, f"File saved: {filename}")
            else:
                self.report({'ERROR'}, "Save failed!")
                return {'CANCELLED'}
        else:
            bpy.ops.wm.save_mainfile('INVOKE_DEFAULT')
            return {'CANCELLED'}

        wm.savereminder_last_save_time = time.time()
        wm.savereminder_popup_open = False
        return {'FINISHED'}


class SAVEREMINDER_OT_save_incremental(bpy.types.Operator):
    """Save the current file with an incremented number"""
    bl_idname = "savereminder.save_incremental"
    bl_label = "Save Incremental"

    def execute(self, context):
        wm = context.window_manager
        if not bpy.data.filepath:
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT')
            return {'CANCELLED'}

        filepath = bpy.data.filepath
        directory, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        base = name.rstrip("0123456789")
        num_str = name[len(base):]

        try:
            num = int(num_str)
        except:
            num = 0

        new_num = num + 1
        new_filename = f"{base}{new_num:03d}{ext}"
        new_path = os.path.join(directory, new_filename)

        bpy.ops.wm.save_as_mainfile(filepath=new_path, copy=False)
        self.report({'INFO'}, f"Incremental save created: {new_filename}")

        wm.savereminder_last_save_time = time.time()
        wm.savereminder_popup_open = False
        return {'FINISHED'}


class SAVEREMINDER_OT_cancel(bpy.types.Operator):
    """Dismiss the reminder popup"""
    bl_idname = "savereminder.cancel"
    bl_label = "Cancel"

    def execute(self, context):
        wm = context.window_manager
        wm.savereminder_last_save_time = time.time()
        wm.savereminder_popup_open = False
        self.report({'INFO'}, "Reminder dismissed")
        return {'FINISHED'}


class SAVEREMINDER_OT_show_reminder(bpy.types.Operator):
    """Popup reminder to save work"""
    bl_idname = "savereminder.show_reminder"
    bl_label = "Save Reminder"

    def invoke(self, context, event):
        wm = context.window_manager
        wm.savereminder_popup_open = True  # ✅ mark popup active
        return context.window_manager.invoke_props_dialog(self, width=260)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Time to save your work!", icon='INFO')

        if bpy.data.filepath:
            layout.label(text=f"File: {os.path.basename(bpy.data.filepath)}")
        else:
            layout.label(text="File: Unsaved", icon='ERROR')

        row = layout.row()
        row.operator("savereminder.save_direct", text="Save", icon="FILE_TICK")
        row.operator("savereminder.save_incremental", text="Save Incremental", icon="DUPLICATE")

        row = layout.row()
        row.operator("savereminder.cancel", text="Cancel", icon="CANCEL")

    def execute(self, context):
        wm = context.window_manager
        wm.savereminder_last_save_time = time.time()  # ✅ reset timer
        wm.savereminder_popup_open = False
        return {'FINISHED'}

    def cancel(self, context):  # ✅ when user closes with ESC/X
        wm = context.window_manager
        wm.savereminder_last_save_time = time.time()
        wm.savereminder_popup_open = False
        return {'CANCELLED'}



# ------------------------------
# Panel
# ------------------------------
class SAVEREMINDER_PT_panel(bpy.types.Panel):
    bl_label = "Save Reminder"
    bl_idname = "SAVEREMINDER_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Save Reminder"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        row = layout.row()
        if is_enabled:
            row.label(text="Status: Enabled", icon='CHECKMARK')
            if hasattr(wm, 'savereminder_last_save_time'):
                prefs = bpy.context.preferences.addons[__name__].preferences
                timer_interval = prefs.reminder_interval * 60
                time_since_last = time.time() - wm.savereminder_last_save_time
                time_until_next = max(0, timer_interval - time_since_last)
                minutes = int(time_until_next // 60)
                seconds = int(time_until_next % 60)
                row = layout.row()
                row.label(text=f"Next reminder in: {minutes:02d}:{seconds:02d}")
        else:
            row.label(text="Status: Disabled", icon='X')

        layout.row().operator(
            "savereminder.toggle_reminder",
            text="Disable" if is_enabled else "Enable",
            icon='PLAY' if not is_enabled else 'PAUSE'
        )

        if bpy.data.filepath:
            layout.row().operator("savereminder.save_direct", text="Save Now", icon='FILE_TICK')
            layout.row().operator("savereminder.save_incremental", text="Save Incremental", icon='DUPLICATE')
        else:
            layout.row().operator("wm.save_as_mainfile", text="Save As...", icon='FILE_NEW')


# ------------------------------
# Timer
# ------------------------------
def save_reminder_timer():
    wm = bpy.context.window_manager
    prefs = bpy.context.preferences.addons[__name__].preferences
    interval = prefs.reminder_interval * 60

    if not is_enabled:
        return 1.0

    if not hasattr(wm, "savereminder_last_save_time"):
        wm.savereminder_last_save_time = time.time()
    if not hasattr(wm, "savereminder_popup_open"):
        wm.savereminder_popup_open = False

    screen = bpy.context.window.screen if bpy.context.window else None
    in_viewport = any(area.type == 'VIEW_3D' for area in screen.areas) if screen else False

    if in_viewport and not wm.savereminder_popup_open:
        elapsed = time.time() - wm.savereminder_last_save_time
        if elapsed >= interval:
            bpy.ops.savereminder.show_reminder('INVOKE_DEFAULT')

    return 1.0  # ✅ keep running every second



# ------------------------------
# Registration
# ------------------------------
classes = (
    SaveReminderPreferences,
    SAVEREMINDER_OT_toggle_reminder,
    SAVEREMINDER_OT_save_direct,
    SAVEREMINDER_OT_save_incremental,
    SAVEREMINDER_OT_cancel,
    SAVEREMINDER_OT_show_reminder,
    SAVEREMINDER_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.timers.register(save_reminder_timer, persistent=True)

    wm = bpy.types.WindowManager
    if not hasattr(wm, "savereminder_last_save_time"):
        bpy.types.WindowManager.savereminder_last_save_time = FloatProperty(default=0.0)
    if not hasattr(wm, "savereminder_popup_open"):
        bpy.types.WindowManager.savereminder_popup_open = BoolProperty(default=False)


def unregister():
    bpy.app.timers.unregister(save_reminder_timer)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    if hasattr(bpy.types.WindowManager, "savereminder_last_save_time"):
        del bpy.types.WindowManager.savereminder_last_save_time
    if hasattr(bpy.types.WindowManager, "savereminder_popup_open"):
        del bpy.types.WindowManager.savereminder_popup_open


if __name__ == "__main__":
    register()
