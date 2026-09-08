"""NEXUS-LUNAR: Blender MCP Client & Headless Automation Pipeline.

Establishes a bi-directional pipeline between NEXUS Spatial Studio and Blender:
1. Online Mode: Direct TCP JSON communication with BlenderMCPServer (port 9876) running inside Blender GUI.
2. Headless Mode: Automated fallback to Blender background execution via CLI for offline photorealistic PBR rendering.
"""

import json
import logging
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus.blender_mcp")

DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 9876

BLENDER_APP_CANDIDATES = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    shutil.which("blender") or "",
]


class BlenderMCPClient:
    """Client for the Blender MCP Server socket protocol and headless runner."""

    def __init__(
        self,
        host: str = DEFAULT_MCP_HOST,
        port: int = DEFAULT_MCP_PORT,
        project_root: Optional[Path] = None,
    ):
        self.host = host
        self.port = port
        self.project_root = project_root or Path(__file__).resolve().parent.parent.parent

    def get_blender_binary(self) -> Optional[str]:
        """Locate the Blender executable on the host system."""
        for cand in BLENDER_APP_CANDIDATES:
            if cand and os.path.exists(cand):
                return cand
        return None

    def is_server_online(self, timeout: float = 0.5) -> bool:
        """Check if BlenderMCPServer is currently listening on port 9876."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((self.host, self.port))
            s.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def send_code_to_socket(self, python_code: str, timeout: float = 15.0) -> Dict[str, Any]:
        """Send bpy Python code to BlenderMCPServer over TCP socket."""
        payload = {
            "type": "execute_code",
            "params": {
                "code": python_code
            }
        }
        data_str = json.dumps(payload)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((self.host, self.port))
            s.sendall(data_str.encode("utf-8"))
            s.shutdown(socket.SHUT_WR)

            chunks = []
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                except socket.timeout:
                    break

            raw_resp = b"".join(chunks).decode("utf-8")
            if raw_resp.strip():
                try:
                    return json.loads(raw_resp)
                except json.JSONDecodeError:
                    return {"status": "success", "raw_output": raw_resp}
            return {"status": "success", "message": "Code transmitted and queued in Blender"}

    def generate_blender_scene_script(
        self,
        obj_path: Path,
        layout_path: Path,
        output_render_path: Path,
    ) -> str:
        """Generate high-fidelity bpy script to construct lunar digital twin and infrastructure."""
        return f'''
import bpy
import json
import math
import os

print("[Blender MCP] Constructing NEXUS Lunar Surface Infrastructure...")

# 1. Clear existing mesh & light objects
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Configure EEVEE / Cycles engine
if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
elif 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]:
    scene.render.engine = 'BLENDER_EEVEE'
else:
    scene.render.engine = 'CYCLES'

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100

# Deep Space Environment
world = bpy.data.worlds.new('LunarDeepSpaceWorld')
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value = (0.015, 0.018, 0.025, 1.0)
    bg.inputs['Strength'].default_value = 0.5

# 2. Construct Complete Spherical Moon Lunar Model
print("[Blender MCP] Creating Complete Spherical Moon Globe...")
bpy.ops.mesh.primitive_uv_sphere_add(radius=1200.0, segments=64, ring_count=64, location=(0, 0, -1180.0))
moon_sphere = bpy.context.active_object
moon_sphere.name = "Celestial_Moon_Globe"

# Lunar Regolith Material for Moon Globe
mat_moon = bpy.data.materials.new(name="Lunar_Regolith_PBR")
mat_moon.use_nodes = True
m_bsdf = mat_moon.node_tree.nodes.get("Principled BSDF")
if m_bsdf:
    m_bsdf.inputs["Base Color"].default_value = (0.28, 0.29, 0.32, 1.0)
    m_bsdf.inputs["Roughness"].default_value = 0.92
moon_sphere.data.materials.append(mat_moon)

# 3. Import 3D DEM Terrain Mesh for South Pole Boguslawsky Base Site
obj_file = r"{str(obj_path)}"
print(f"[Blender MCP] Loading Lunar DEM OBJ: {{obj_file}}")
if hasattr(bpy.ops.wm, 'obj_import'):
    bpy.ops.wm.obj_import(filepath=obj_file)
else:
    bpy.ops.import_scene.obj(filepath=obj_file)

terrain_obj = bpy.context.selected_objects[0]
terrain_obj.name = "Lunar_Boguslawsky_DEM"
terrain_obj.location = (0, 0, 20.0) # Sited atop the lunar sphere surface
terrain_obj.data.materials.append(mat_moon)

# 4. Collimated Grazing Lunar Sunlight (Polar Sun: 3.5 deg elevation, 124.5 deg azimuth)
sun_data = bpy.data.lights.new(name="Polar_Sun_Light", type='SUN')
sun_data.energy = 8.0
sun_data.angle = math.radians(0.53) # Accurate solar disc angular diameter
sun_obj = bpy.data.objects.new(name="Polar_Sun_Light", object_data=sun_data)
# Polar low-angle rotation
sun_obj.rotation_euler = (math.radians(86.5), math.radians(5.0), math.radians(124.5))
bpy.context.collection.objects.link(sun_obj)

# 5. Modular Infrastructure Construction on Lunar Surface
layout_file = r"{str(layout_path)}"
hab_core_target = None

if os.path.exists(layout_file):
    with open(layout_file, "r") as f:
        plan = json.load(f)

    for mod in plan.get("modules", []):
        m_id = mod.get("module_id", "")
        m_type = mod.get("type", "")
        pos = mod.get("position_m", {{}})
        x = pos.get("x", 0.0)
        y = pos.get("y", 0.0)
        z = pos.get("z", 0.0) + 1000.0

        if m_type == "HABITAT_CORE":
            # Pressurized Geodesic Habitat Dome
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=24.0, location=(x, y, z + 12.0))
            dome = bpy.context.active_object
            dome.name = f"NEXUS_{{m_id}}_Dome"
            mat_dome = bpy.data.materials.new(name="Dome_Thermal_Insulation")
            mat_dome.use_nodes = True
            d_bsdf = mat_dome.node_tree.nodes.get("Principled BSDF")
            if d_bsdf:
                d_bsdf.inputs["Base Color"].default_value = (0.94, 0.95, 0.98, 1.0)
                d_bsdf.inputs["Metallic"].default_value = 0.3
                d_bsdf.inputs["Roughness"].default_value = 0.15
            dome.data.materials.append(mat_dome)
            hab_core_target = dome

            # Airlock entry pod
            bpy.ops.mesh.primitive_cylinder_add(radius=4.0, depth=12.0, location=(x + 24.0, y, z + 4.0))
            airlock = bpy.context.active_object
            airlock.name = f"NEXUS_{{m_id}}_Airlock"
            airlock.rotation_euler = (0, math.radians(90.0), 0)

        elif m_type == "SOLAR_FARM":
            # Vertical Bifacial Solar Array Towers
            for offset in [(-25, 0), (0, 0), (25, 0)]:
                bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x + offset[0], y + offset[1], z + 18.0))
                panel = bpy.context.active_object
                panel.scale = (16.0, 1.2, 32.0)
                panel.name = f"NEXUS_{{m_id}}_Array_{{offset[0]}}"
                mat_panel = bpy.data.materials.new(name="Bifacial_PV_Silicon")
                mat_panel.use_nodes = True
                p_bsdf = mat_panel.node_tree.nodes.get("Principled BSDF")
                if p_bsdf:
                    p_bsdf.inputs["Base Color"].default_value = (0.01, 0.04, 0.18, 1.0)
                    p_bsdf.inputs["Metallic"].default_value = 0.8
                    p_bsdf.inputs["Roughness"].default_value = 0.05
                panel.data.materials.append(mat_panel)

        elif m_type == "LANDING_PAD":
            # Sintered Regolith Landing Pad
            bpy.ops.mesh.primitive_cylinder_add(radius=55.0, depth=4.0, location=(x, y, z + 2.0))
            pad = bpy.context.active_object
            pad.name = f"NEXUS_{{m_id}}_Pad"
            mat_pad = bpy.data.materials.new(name="Sintered_Basalt_Pad")
            mat_pad.use_nodes = True
            p_bsdf = mat_pad.node_tree.nodes.get("Principled BSDF")
            if p_bsdf:
                p_bsdf.inputs["Base Color"].default_value = (0.22, 0.22, 0.24, 1.0)
                p_bsdf.inputs["Roughness"].default_value = 0.6
            pad.data.materials.append(mat_pad)

        elif m_type == "REGOLITH_BERM":
            # Blast Deflection Wall
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z + 8.0))
            berm = bpy.context.active_object
            berm.scale = (70.0, 14.0, 16.0)
            berm.name = f"NEXUS_{{m_id}}_Berm"

        elif m_type == "ISRU_PLANT":
            # In-Situ Resource Water-Ice Processing Complex
            bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z + 7.0))
            isru = bpy.context.active_object
            isru.scale = (28.0, 20.0, 14.0)
            isru.name = f"NEXUS_{{m_id}}_ISRU"
            # Cryogenic storage sphere
            bpy.ops.mesh.primitive_uv_sphere_add(radius=10.0, location=(x + 20.0, y, z + 10.0))
            tank = bpy.context.active_object
            tank.name = f"NEXUS_{{m_id}}_CryoTank"

# 5. Orbital Cinematic Tracking Camera
cam_data = bpy.data.cameras.new("NEXUS_Orbital_Camera")
cam_data.lens = 35.0
cam_data.clip_end = 20000.0
cam_obj = bpy.data.objects.new("NEXUS_Orbital_Camera", object_data=cam_data)
cam_obj.location = (180.0, -280.0, 580.0)
bpy.context.collection.objects.link(cam_obj)
scene.camera = cam_obj

if hab_core_target:
    tt = cam_obj.constraints.new(type='TRACK_TO')
    tt.target = hab_core_target
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'

# 6. Render Still Frame
out_file = r"{str(output_render_path)}"
scene.render.filepath = out_file
print(f"[Blender MCP] Rendering 3D Digital Twin frame to: {{out_file}}")
bpy.ops.render.render(write_still=True)
print("[Blender MCP] 3D Infrastructure Construction Completed Successfully!")
'''

    def build_infrastructure_pipeline(
        self,
        force_headless: bool = False,
    ) -> Dict[str, Any]:
        """Execute the full 3D infrastructure construction pipeline.

        Connects via socket to Blender MCP Server on port 9876 if running;
        otherwise executes Blender headless via CLI.
        """
        out_dir = self.project_root / "outputs" / "nexus_3d"
        out_dir.mkdir(parents=True, exist_ok=True)

        obj_path = out_dir / "nexus_boguslawsky_mesh.obj"
        layout_path = out_dir / "habitat_layout_plan.json"
        render_path = out_dir / "nexus_blender_digital_twin.png"

        # If files do not exist yet, trigger POC 8 to produce them
        if not obj_path.exists() or not layout_path.exists():
            logger.info("Generating POC 8 habitat layout & 3D mesh before Blender build...")
            from packages.nexus_core.poc8_habitat_planner import HabitatConstraintPlanner
            planner = HabitatConstraintPlanner()
            planner.generate_habitat_layout()
            planner.export_3d_terrain_mesh(grid_subsample=4)

        script_code = self.generate_blender_scene_script(obj_path, layout_path, render_path)
        temp_script_path = out_dir / "blender_mcp_build_script.py"
        temp_script_path.write_text(script_code, encoding="utf-8")

        online = self.is_server_online()
        logger.info(f"Checking BlenderMCPServer on {self.host}:{self.port}... Online: {online}")

        if online and not force_headless:
            # Mode A: Active Blender GUI with MCP Server running
            try:
                resp = self.send_code_to_socket(script_code)
                return {
                    "success": True,
                    "mode": "mcp_socket",
                    "host": self.host,
                    "port": self.port,
                    "status": "connected",
                    "rendered_image": "/outputs/nexus_3d/nexus_blender_digital_twin.png",
                    "modules": ["HABITAT_CORE", "SOLAR_FARM", "LANDING_PAD", "REGOLITH_BERM", "ISRU_PLANT"],
                    "socket_response": resp,
                    "message": "3D infrastructure successfully transmitted to active Blender MCP Server on port 9876",
                }
            except Exception as e:
                logger.warning(f"Socket transmission failed: {e}. Falling back to Blender headless CLI.")

        # Mode B: Blender Headless CLI Runner
        blender_bin = self.get_blender_binary()
        if not blender_bin:
            return {
                "success": False,
                "mode": "unavailable",
                "error": "Blender binary not found on host system. Install Blender or launch BlenderMCPServer on port 9876.",
            }

        cmd = [
            blender_bin,
            "--background",
            "--python",
            str(temp_script_path),
        ]
        logger.info(f"Running headless Blender command: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0 and render_path.exists():
            return {
                "success": True,
                "mode": "headless_cli",
                "blender_bin": blender_bin,
                "rendered_image": "/outputs/nexus_3d/nexus_blender_digital_twin.png",
                "image_size_kb": round(render_path.stat().st_size / 1024, 1),
                "modules": ["HABITAT_CORE", "SOLAR_FARM", "LANDING_PAD", "REGOLITH_BERM", "ISRU_PLANT"],
                "message": "Rendered 3D Digital Twin via Blender headless CLI engine",
            }
        else:
            return {
                "success": False,
                "mode": "headless_cli",
                "error": f"Blender execution exited with code {res.returncode}",
                "stdout_tail": res.stdout[-600:] if res.stdout else "",
            }


if __name__ == "__main__":
    client = BlenderMCPClient()
    print("Blender MCP Server online:", client.is_server_online())
    result = client.build_infrastructure_pipeline()
    print(json.dumps(result, indent=2))
