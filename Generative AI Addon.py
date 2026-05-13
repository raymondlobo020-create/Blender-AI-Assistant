import bpy
import subprocess
import sys
import importlib

bl_info = {
    "name": "AI Agent Bridge",
    "author": "Raymond",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Scene > Generative Agent",
    "description": "Bridge for AI automation and remote execution.",
    "category": "System",
}

# --- Dependency Management ---
def install_and_import(package):
    try:
        return importlib.import_module(package)
    except ImportError:
        py_path = sys.executable
        subprocess.check_call([py_path, "-m", "pip", "install", package])
        return importlib.import_module(package)

# Pre-importing requests to avoid lag in modal loop
requests = install_and_import("requests")

# --- Operators ---
class AI_OT_Bridge(bpy.types.Operator):
    bl_idname = "wm.ai_bridge"
    bl_label = "AI Bridge"
    _timer = None

    def modal(self, context, event):
        if not context.scene.ai_bridge_active:
            return self.cancel(context)

        if event.type == 'TIMER':
            try:
                # 1. POLL THE SERVER FOR TASKS
                # We assume your server has an endpoint that gives the next 'code' string
                response = requests.get("http://localhost:8000/internal/get_task", timeout=0.1)
                
                if response.status_code == 200:
                    task = response.json()
                    code_to_run = task.get("code")
                    task_id = task.get("id")

                    if code_to_run:
                        print(f"Executing AI Task: {task_id}")
                        
                        # 2. CAPTURE THE RESULT
                        # We create a dictionary to catch the 'result' variable
                        local_namespace = {"bpy": bpy, "context": context}
                        
                        try:
                            exec(code_to_run, globals(), local_namespace)
                            execution_result = local_namespace.get("result", "Done (No 'result' assigned)")
                        except Exception as e:
                            execution_result = f"Error: {str(e)}"

                        # 3. POST THE RESULT BACK
                        requests.post(
                            "http://localhost:8000/internal/post_result", 
                            json={"id": task_id, "response": execution_result}
                        )
                        
            except Exception:
                # Silently fail if server is down to keep Blender smooth
                pass

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        if context.scene.ai_bridge_active:
            context.scene.ai_bridge_active = False
            return {'FINISHED'}
        else:
            self._timer = wm.event_timer_add(0.2, window=context.window) # Faster poll rate (0.2s)
            wm.modal_handler_add(self)
            context.scene.ai_bridge_active = True
            return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        return {'CANCELLED'}

# --- UI Panel ---
class AI_PT_MainPanel(bpy.types.Panel):
    bl_label = "Generative Agent"
    bl_idname = "AI_PT_main_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'} 

    def draw(self, layout):
        scene = bpy.context.scene
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column(align=True)
        
        if not scene.ai_bridge_active:
            col.operator("wm.ai_bridge_listener", icon='OUTLINER_OB_LIGHTPROBE', text="Connect to Server")
        else:
            # Active State UI
            box = col.box()
            row = box.row()
            row.label(text="Status: Connected", icon='URL')
            
            # Sub-row for the disconnect button to keep it clean
            col.separator()
            col.operator("wm.ai_bridge_listener", icon='CANCEL', text="Disconnect Bridge")

# --- Registration ---
classes = (
    AI_OT_BridgeOperator,
    AI_PT_MainPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ai_bridge_active = bpy.props.BoolProperty(
        name="Bridge Active", 
        default=False,
        description="Tracks the state of the AI Bridge modal operator"
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ai_bridge_active

if __name__ == "__main__":
    register()
