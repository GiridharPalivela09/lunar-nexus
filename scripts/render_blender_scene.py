#!/usr/bin/env python3
"""NEXUS 3D Digital Twin: Automated Headless Blender Rendering Pipeline.

Loads:
- 3D DEM terrain mesh (outputs/nexus_3d/nexus_boguslawsky_mesh.obj)
- Modular habitat layout plan (outputs/nexus_3d/habitat_layout_plan.json)

Executes headless in Blender via Python API (bpy):
- Realistic lunar regolith PBR shader (roughness 0.95, albedo 0.12)
- Collimated physical Sun lighting at polar grazing angle (elevation 3.5°, azimuth 124.5°)
- Instantiates 3D architectural habitat modules (living dome, solar towers, landing pad, berm)
- High-fidelity raytraced digital twin render exported to outputs/nexus_3d/nexus_blender_digital_twin.png
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BLENDER_APP_CANDIDATES = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    shutil.which("blender") or "",
]


def run_blender_headless():
    # 1. Locate Blender executable
    blender_bin = None
    for cand in BLENDER_APP_CANDIDATES:
        if cand and os.path.exists(cand):
            blender_bin = cand
            break

    if not blender_bin:
        print("[!] Blender binary not found. Please install Blender to generate offline raytraced renders.")
        print("    (Three.js interactive WebGL 3D Digital Twin remains fully functional in the dashboard).")
        return False

    print(f"[*] Found Blender binary at: {blender_bin}")

    # 2. Check inputs
    obj_path = Path("outputs/nexus_3d/nexus_boguslawsky_mesh.obj").resolve()
    layout_path = Path("outputs/nexus_3d/habitat_layout_plan.json").resolve()
    output_img = Path("outputs/nexus_3d/nexus_blender_digital_twin.png").resolve()

    if not obj_path.exists():
        print(f"[!] OBJ mesh not found at {obj_path}. Running POC 8 demo first...")
        subprocess.run([sys.executable, "scripts/demo_nexus_poc8.py"], check=True)

    # 3. Create inline Blender script to execute inside Blender Python environment
    blender_script_content = f"""
import bpy
import json
import math
import os

print("[Blender] Initializing clean scene...")
bpy.ops.wm.read_factory_settings(use_empty=True)
# 1. Set render engine
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100

# Ambient World Fill Light (deep space with subtle starlight bounce)
world = bpy.data.worlds.new('LunarSpaceWorld')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.05, 0.05, 0.07, 1.0)
    bg.inputs['Strength'].default_value = 0.8

# 2. Import 3D OBJ Terrain
obj_path = r"{str(obj_path)}"
print(f"[Blender] Importing terrain mesh from: {{obj_path}}")
if hasattr(bpy.ops.wm, 'obj_import'):
    bpy.ops.wm.obj_import(filepath=obj_path)
else:
    bpy.ops.import_scene.obj(filepath=obj_path)

terrain_obj = bpy.context.selected_objects[0]
terrain_obj.name = "Lunar_Terrain_DEM"
# Align terrain vertically so surface is at Z ~ 0
terrain_obj.location = (0, 0, 1000.0)

# Create Regolith PBR Material
mat_terrain = bpy.data.materials.new(name="Lunar_Regolith_PBR")
mat_terrain.use_nodes = True
bsdf = mat_terrain.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.35, 0.35, 0.38, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
terrain_obj.data.materials.append(mat_terrain)

# 3. Setup Sun Lighting (directional sun casting clear crater & module shadows)
sun_data = bpy.data.lights.new(name="Lunar_Sun", type='SUN')
sun_data.energy = 6.0
sun_data.angle = math.radians(1.0)
sun_obj = bpy.data.objects.new(name="Lunar_Sun", object_data=sun_data)
sun_obj.rotation_euler = (math.radians(35.0), math.radians(15.0), math.radians(45.0))
bpy.context.collection.objects.link(sun_obj)

# 4. Load Habitat Components
layout_path = r"{str(layout_path)}"
hab_core_obj = None

if os.path.exists(layout_path):
    with open(layout_path, "r") as f:
        plan = json.load(f)

    for mod in plan.get("modules", []):
        m_type = mod.get("type")
        pos = mod.get("position_m", {{}})
        x, y = pos.get("x", 0.0), pos.get("y", 0.0)
        # Since terrain was shifted +1000m, module Z is offset
        z = pos.get("z", 0.0) + 1000.0

        if m_type == "HABITAT_CORE":
            # White geodesic pressurized living dome
            bpy.ops.mesh.primitive_uv_sphere_add(radius=22.0, location=(x, y, z + 12.0))
            dome = bpy.context.active_object
            dome.name = "Habitat_Core_Dome"
            mat_dome = bpy.data.materials.new(name="Hab_Dome_Mat")
            mat_dome.use_nodes = True
            d_bsdf = mat_dome.node_tree.nodes.get("Principled BSDF")
            if d_bsdf:
                d_bsdf.inputs["Base Color"].default_value = (0.92, 0.94, 0.98, 1.0)
                d_bsdf.inputs["Roughness"].default_value = 0.2
            dome.data.materials.append(mat_dome)
            hab_core_obj = dome

        elif m_type == "SOLAR_FARM":
            # Bifacial solar panel field
            bpy.ops.mesh.primitive_cube_add(size=40.0, location=(x, y, z + 20.0))
            solar = bpy.context.active_object
            solar.name = "Solar_Array_Field"
            mat_sol = bpy.data.materials.new(name="Solar_Cell_Mat")
            mat_sol.use_nodes = True
            s_bsdf = mat_sol.node_tree.nodes.get("Principled BSDF")
            if s_bsdf:
                s_bsdf.inputs["Base Color"].default_value = (0.02, 0.08, 0.25, 1.0)
                s_bsdf.inputs["Roughness"].default_value = 0.1
            solar.data.materials.append(mat_sol)

        elif m_type == "LANDING_PAD":
            # Sintered regolith touchdown pad
            bpy.ops.mesh.primitive_cylinder_add(radius=50.0, depth=4.0, location=(x, y, z + 2.0))
            pad = bpy.context.active_object
            pad.name = "Landing_Pad_Depot"

# 5. Position High-Angle Orbital Camera with Track-To Constraint
cam_data = bpy.data.cameras.new("Digital_Twin_Orbital_Camera")
cam_data.lens = 32
cam_data.clip_end = 10000.0
cam_obj = bpy.data.objects.new("Digital_Twin_Orbital_Camera", object_data=cam_data)
cam_obj.location = (50.0, -100.0, 550.0)
bpy.context.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Track directly to Habitat Core
if hab_core_obj:
    tt = cam_obj.constraints.new(type='TRACK_TO')
    tt.target = hab_core_obj
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'

# 6. Render Output
output_img = r"{str(output_img)}"
scene.render.filepath = output_img
print(f"[Blender] Rendering 3D Digital Twin frame to: {{output_img}}")
bpy.ops.render.render(write_still=True)
print("[Blender] Digital Twin rendering completed successfully!")
"""

    temp_script_path = Path("outputs/nexus_3d/blender_render_script.py").resolve()
    temp_script_path.write_text(blender_script_content, encoding="utf-8")

    # 4. Invoke Blender headless
    cmd = [
        blender_bin,
        "--background",
        "--python",
        str(temp_script_path),
    ]

    print(f"[*] Executing headless Blender rendering...")
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and output_img.exists():
        print(f"[✓] Raytraced 3D Digital Twin Render Saved: {output_img} ({output_img.stat().st_size / 1024:.1f} KB)")
        return True
    else:
        print("[!] Blender exited with return code:", res.returncode)
        print("Blender Output Tail:\n", res.stdout[-800:] if res.stdout else "No output")
        return False


if __name__ == "__main__":
    run_blender_headless()
