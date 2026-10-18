# -*- coding: utf-8 -*-
"""
3D Submersible Navigation & Orientation Widget for Tyrant-AQ AUV GCS.
Hardware-accelerated OpenGL 3D vehicle orientation display supporting high-precision CAD STL models
with studio-grade lighting, exact 6-DOF vectored thruster orientations aligned with manual control,
real-time thrust vector visualization, and tactical HUD overlays.
"""
import sys
import os
import math
import struct
from typing import List, Tuple, Optional, Dict
import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QOpenGLWidget

try:
    from OpenGL import GL, GLU
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False

# Global cache for heavy STL meshes to avoid redundant disk parsing across multiple widget instances
_GLOBAL_STL_CACHE = {}


class Submersible3DWidget(QOpenGLWidget if HAS_OPENGL else QtWidgets.QWidget):
    """
    Tactical 3D Vehicle Orientation & Navigation Display with Hardware-Accelerated
    OpenGL Rendering, Precise 6-DOF Vectored Thrusters, and QPainter HUD Telemetry Overlays.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(240, 180)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Vehicle Attitude State
        self.roll = 0.0          # degrees (-180 to 180)
        self.pitch = 0.0         # degrees (-90 to 90)
        self.yaw = 0.0           # degrees (0 to 360)
        self.depth = 0.0         # meters
        self.target_depth = 0.0

        # Camera View Orbit Parameters
        self.cam_azimuth = 35.0    # View angle horizontal (deg)
        self.cam_elevation = 25.0  # View angle vertical (deg)
        self.cam_zoom = 1.0        # Zoom multiplier
        self._last_mouse_pos = None

        # Thruster PWMs for dynamic thrust vector animation (T1 to T6)
        self.pwms = [1500] * 6

        # Colors & Aesthetics
        self.is_dark_theme = True
        self.gl_bg = (0.086, 0.094, 0.11, 1.0)
        self.bg_color = QtGui.QColor(22, 24, 28)
        self.water_color = QtGui.QColor(20, 55, 90, 70)

    def set_theme(self, theme_name: str):
        self.is_dark_theme = "Dark" in theme_name
        if self.is_dark_theme:
            self.bg_color = QtGui.QColor(22, 24, 28)
            self.gl_bg = (0.086, 0.094, 0.11, 1.0)
        else:
            self.bg_color = QtGui.QColor(240, 242, 245)
            self.gl_bg = (0.941, 0.949, 0.961, 1.0)
        self.update()

        # Custom STL Mesh Data (NumPy float32 arrays for zero-copy OpenGL VBO/VAO rendering)
        self.gl_verts: Optional[np.ndarray] = None
        self.gl_normals: Optional[np.ndarray] = None
        self.custom_mesh_loaded = False

        # Precise 6-Thruster Anchor Positions & Force Vectors (Body Coordinates)
        self.thruster_data: List[Dict] = []
        self._init_thruster_geometry()

        # Procedural fallback faces (vertices, base_color, outline_color)
        self.solid_faces = []

        # Screen projection cache for 2D badge overlay
        self._thruster_screen_pos: List[Tuple[float, float, bool, int]] = []

        # Attempt to load custom CAD STL model or build procedural fallback mesh
        self.init_mesh()

    def _init_thruster_geometry(self):
        """
        Initializes high-precision 3D anchor coordinates and unit force vectors for all 6 thrusters,
        perfectly matching the CAD chassis geometry and the 6-DOF manual motion mixing formulas:
          - T1: Bow Port (Depan Kiri) @ +45° Vectored
          - T2: Bow Starboard (Depan Kanan) @ -45° Vectored
          - T3: Stern Port (Belakang Kiri) @ -45° Vectored
          - T4: Stern Starboard (Belakang Kanan) @ +45° Vectored
          - T5: Vertical Port (Heave Kiri) @ Vertical Z-Axis
          - T6: Vertical Starboard (Heave Kanan) @ Vertical Z-Axis
        """
        cos45 = 0.70710678
        sin45 = 0.70710678

        # In normalized body space:
        # X: Forward (+X = Bow / Dome)
        # Y: Right (+Y = Starboard)
        # Z: Up (+Z = Dorsal / Sensors)
        self.thruster_data = [
            {
                "id": "T1",
                "label": "T1 Depan Kiri (45°)",
                "pos": np.array([+0.837, -0.528, -0.017], dtype=np.float32),
                "force_dir": np.array([+cos45, +sin45, 0.0], dtype=np.float32),
                "type": "horizontal"
            },
            {
                "id": "T2",
                "label": "T2 Depan Kanan (45°)",
                "pos": np.array([+0.837, +0.528, -0.017], dtype=np.float32),
                "force_dir": np.array([+cos45, -sin45, 0.0], dtype=np.float32),
                "type": "horizontal"
            },
            {
                "id": "T3",
                "label": "T3 Belakang Kiri (45°)",
                "pos": np.array([-0.837, -0.528, -0.017], dtype=np.float32),
                "force_dir": np.array([+cos45, -sin45, 0.0], dtype=np.float32),
                "type": "horizontal"
            },
            {
                "id": "T4",
                "label": "T4 Belakang Kanan (45°)",
                "pos": np.array([-0.837, +0.528, -0.017], dtype=np.float32),
                "force_dir": np.array([+cos45, +sin45, 0.0], dtype=np.float32),
                "type": "horizontal"
            },
            {
                "id": "T5",
                "label": "T5 Vertikal Kiri",
                "pos": np.array([0.000, -0.604, +0.146], dtype=np.float32),
                "force_dir": np.array([0.0, 0.0, -1.0], dtype=np.float32), # +PWM drives down (Heave Down)
                "type": "vertical"
            },
            {
                "id": "T6",
                "label": "T6 Vertikal Kanan",
                "pos": np.array([0.000, +0.604, +0.146], dtype=np.float32),
                "force_dir": np.array([0.0, 0.0, -1.0], dtype=np.float32), # +PWM drives down (Heave Down)
                "type": "vertical"
            }
        ]

    def init_mesh(self):
        """Tries to load external STL model; otherwise generates high-fidelity solid shaded twin-hull AUV."""
        stl_path = self._find_custom_stl()
        if stl_path and self._load_stl(stl_path):
            self.custom_mesh_loaded = True
        else:
            self.build_procedural_solid_mesh()

    def _find_custom_stl(self) -> Optional[str]:
        """Searches for user-provided STL model file in assets/ directory."""
        candidates = []
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "assets"))
            if hasattr(sys, "_MEIPASS"):
                candidates.append(os.path.join(sys._MEIPASS, "assets"))

        source_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))
        candidates.append(source_dir)

        preferred = ["finaltes2.stl", "finaltes2.STL", "robot_model.stl", "model.stl", "auv.stl", "robot.stl"]
        for assets_dir in candidates:
            if not os.path.isdir(assets_dir):
                continue
            for p_name in preferred:
                p = os.path.join(assets_dir, p_name)
                if os.path.isfile(p):
                    return p
            for fname in sorted(os.listdir(assets_dir)):
                if fname.lower().endswith(".stl"):
                    return os.path.join(assets_dir, fname)

        return None

    def _load_stl(self, filepath: str) -> bool:
        """Fast binary and ASCII STL loader using NumPy for instant parsing (<0.05s)."""
        global _GLOBAL_STL_CACHE
        if filepath in _GLOBAL_STL_CACHE:
            cached = _GLOBAL_STL_CACHE[filepath]
            self.gl_verts = cached["verts"]
            self.gl_normals = cached["normals"]
            self.solid_faces = cached["solid_faces"]
            return True

        try:
            file_size = os.path.getsize(filepath)
            verts = None
            normals = None

            # Fast Binary STL Parsing with NumPy
            with open(filepath, "rb") as f:
                header = f.read(80)
                num_bytes = f.read(4)
                if len(num_bytes) == 4:
                    num_tris = struct.unpack("<I", num_bytes)[0]
                    expected_size = 84 + num_tris * 50
                    if file_size == expected_size:
                        dt = np.dtype([
                            ("normal", "<f4", (3,)),
                            ("v1", "<f4", (3,)),
                            ("v2", "<f4", (3,)),
                            ("v3", "<f4", (3,)),
                            ("attr", "<u2")
                        ])
                        data = np.fromfile(f, dtype=dt, count=num_tris)
                        raw_v = np.empty((num_tris * 3, 3), dtype=np.float32)
                        raw_v[0::3] = data["v1"]
                        raw_v[1::3] = data["v2"]
                        raw_v[2::3] = data["v3"]

                        # Align CAD coordinates to standard AUV Body Frame:
                        # Forward (+X) = Dome (-CAD_Z)
                        # Right (+Y)   = Starboard (+CAD_X)
                        # Up (+Z)      = Dorsal/Sensors (+CAD_Y)
                        verts = np.empty_like(raw_v)
                        verts[:, 0] = -raw_v[:, 2]
                        verts[:, 1] = raw_v[:, 0]
                        verts[:, 2] = raw_v[:, 1]

                        # Compute face normals aligned with transformed vertices
                        tri_v = verts.reshape(-1, 3, 3)
                        e1 = tri_v[:, 1] - tri_v[:, 0]
                        e2 = tri_v[:, 2] - tri_v[:, 0]
                        c = np.cross(e1, e2)
                        c_lens = np.linalg.norm(c, axis=1, keepdims=True)
                        c_lens[c_lens == 0] = 1.0
                        c /= c_lens
                        normals = np.repeat(c, 3, axis=0).astype(np.float32)

            # Fallback for ASCII STL if not binary
            if verts is None:
                triangles = []
                curr_tri = []
                with open(filepath, "r", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4 and parts[0] == "vertex":
                            curr_tri.append((float(parts[1]), float(parts[2]), float(parts[3])))
                            if len(curr_tri) == 3:
                                triangles.append(curr_tri)
                                curr_tri = []
                if triangles:
                    raw_arr = np.array(triangles, dtype=np.float32).reshape(-1, 3)
                    verts = np.empty_like(raw_arr)
                    verts[:, 0] = -raw_arr[:, 2]
                    verts[:, 1] = raw_arr[:, 0]
                    verts[:, 2] = raw_arr[:, 1]
                    tri_v = verts.reshape(-1, 3, 3)
                    e1 = tri_v[:, 1] - tri_v[:, 0]
                    e2 = tri_v[:, 2] - tri_v[:, 0]
                    c = np.cross(e1, e2)
                    c_lens = np.linalg.norm(c, axis=1, keepdims=True)
                    c_lens[c_lens == 0] = 1.0
                    c /= c_lens
                    normals = np.repeat(c, 3, axis=0).astype(np.float32)

            if verts is None or len(verts) == 0:
                return False

            # Normalize bounding box and center precisely at origin (0, 0, 0)
            min_v = verts.min(axis=0)
            max_v = verts.max(axis=0)
            center = (min_v + max_v) / 2.0
            max_span = float(np.max(max_v - min_v)) or 1.0
            scale = 2.0 / max_span
            verts = (verts - center) * scale

            self.gl_verts = np.ascontiguousarray(verts, dtype=np.float32)
            self.gl_normals = np.ascontiguousarray(normals, dtype=np.float32)

            # For QPainter fallback mode (sampled to responsive count)
            num_t = len(verts) // 3
            sample_stride = max(1, num_t // 6000)
            sample_indices = np.arange(0, num_t, sample_stride) * 3
            self.solid_faces = []
            base_col = QtGui.QColor(42, 110, 185)
            border_col = QtGui.QColor(20, 50, 85)
            for idx in sample_indices:
                p1 = tuple(self.gl_verts[idx])
                p2 = tuple(self.gl_verts[idx + 1])
                p3 = tuple(self.gl_verts[idx + 2])
                self.solid_faces.append(([p1, p2, p3], base_col, border_col))

            _GLOBAL_STL_CACHE[filepath] = {
                "verts": self.gl_verts,
                "normals": self.gl_normals,
                "solid_faces": self.solid_faces
            }
            return True
        except Exception as e:
            print(f"[3D Widget] Gagal memuat STL '{filepath}': {e}")
            return False

    def build_procedural_solid_mesh(self):
        """Constructs procedural twin-hull 3D model fallback."""
        self.solid_faces = []
        length = 1.55
        radius = 0.18
        separation = 0.58
        hull_blue = QtGui.QColor(32, 95, 170)
        hull_cone = QtGui.QColor(210, 220, 235)
        chassis_dark = QtGui.QColor(40, 44, 52)
        edge_subtle = QtGui.QColor(20, 25, 32, 100)

        segs = 12
        for y_center in [-separation, separation]:
            circle_pts = []
            for i in range(segs):
                ang = i * (2.0 * math.pi / segs)
                cz = math.sin(ang) * radius
                cy = y_center + math.cos(ang) * radius
                circle_pts.append((cy, cz))

            x_nose = length * 0.52
            x_fwd = length * 0.35
            x_aft = -length * 0.35
            x_tail = -length * 0.52

            for i in range(segs):
                ni = (i + 1) % segs
                self.solid_faces.append((
                    [(x_nose, y_center, 0.0), (x_fwd, circle_pts[ni][0], circle_pts[ni][1]), (x_fwd, circle_pts[i][0], circle_pts[i][1])],
                    hull_cone, edge_subtle
                ))
                self.solid_faces.append((
                    [(x_fwd, circle_pts[i][0], circle_pts[i][1]), (x_fwd, circle_pts[ni][0], circle_pts[ni][1]),
                     (x_aft, circle_pts[ni][0], circle_pts[ni][1]), (x_aft, circle_pts[i][0], circle_pts[i][1])],
                    hull_blue, edge_subtle
                ))
                self.solid_faces.append((
                    [(x_aft, circle_pts[i][0], circle_pts[i][1]), (x_aft, circle_pts[ni][0], circle_pts[ni][1]), (x_tail, y_center, 0.0)],
                    chassis_dark, edge_subtle
                ))

    def update_attitude(self, roll: float, pitch: float, yaw: float, depth: float,
                        target_depth: float = 0.0, pwms: List[int] = None):
        """Updates vehicle 6-DOF attitude and triggers visual repaint."""
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw % 360.0
        self.depth = depth
        self.target_depth = target_depth
        if pwms and len(pwms) >= 6:
            self.pwms = pwms
        self.update()

    # =========================================================
    # --- HARDWARE-ACCELERATED OPENGL PIPELINE ---
    # =========================================================
    def initializeGL(self):
        if not HAS_OPENGL:
            return
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LESS)
        GL.glEnable(GL.GL_NORMALIZE)

        # Enable two-sided lighting so internal duct walls and cutouts are illuminated
        GL.glLightModeli(GL.GL_LIGHT_MODEL_TWO_SIDE, GL.GL_TRUE)
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_LIGHT1)
        GL.glEnable(GL.GL_LIGHT2)

        # 3-Point Studio Lighting Setup:
        # 1. Key Light: Top-Front-Right (Bright white, crisp specular)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [3.0, 4.0, 5.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_SPECULAR, [0.55, 0.55, 0.65, 1.0])

        # 2. Fill Light: Front-Left (Soft oceanic fill, illuminates port side)
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_POSITION, [3.0, -4.0, 2.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT1, GL.GL_DIFFUSE, [0.55, 0.60, 0.70, 1.0])

        # 3. Rim / Back Light: Bottom-Rear (Separates chassis contours from dark water)
        GL.glLightfv(GL.GL_LIGHT2, GL.GL_POSITION, [-4.0, 0.0, -3.0, 0.0])
        GL.glLightfv(GL.GL_LIGHT2, GL.GL_DIFFUSE, [0.40, 0.45, 0.55, 1.0])

        GL.glLightModelfv(GL.GL_LIGHT_MODEL_AMBIENT, [0.35, 0.38, 0.42, 1.0])

        # Polished Material Properties: Tactical Subsea Blue with Gloss Highlights
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glMaterialfv(GL.GL_FRONT_AND_BACK, GL.GL_SPECULAR, [0.45, 0.45, 0.50, 1.0])
        GL.glMaterialf(GL.GL_FRONT_AND_BACK, GL.GL_SHININESS, 42.0)

        GL.glClearColor(0.086, 0.094, 0.11, 1.0) # #16181C Dark Slate

    def resizeGL(self, w: int, h: int):
        if not HAS_OPENGL:
            return
        dpr = self.devicePixelRatioF()
        fb_w = max(1, int(w * dpr))
        fb_h = max(1, int(h * dpr))
        GL.glViewport(0, 0, fb_w, fb_h)

    def paintGL(self):
        w = self.width()
        h = max(1, self.height())

        if HAS_OPENGL:
            self._render_opengl_scene(w, h)
        else:
            self._render_software_scene(w, h)

        # Overlay 2D HUD Telemetry and 3D Thruster Badges via QPainter
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing)
        self._draw_thruster_badges(painter, w, h)
        self.draw_hud_overlay(painter, w, h)
        painter.end()

    def _render_opengl_scene(self, w: int, h: int):
        dpr = self.devicePixelRatioF()
        fb_w = max(1, int(w * dpr))
        fb_h = max(1, int(h * dpr))

        gl_bg = getattr(self, "gl_bg", (0.086, 0.094, 0.11, 1.0))
        GL.glClearColor(*gl_bg)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glViewport(0, 0, fb_w, fb_h)

        # Setup Perspective Camera
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(35.0, fb_w / fb_h, 0.1, 100.0)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        # Camera Orbit & Zoom
        cam_dist = 3.6 / max(0.2, self.cam_zoom)
        GL.glTranslatef(0.0, 0.0, -cam_dist)
        GL.glRotatef(self.cam_elevation, 1.0, 0.0, 0.0)
        GL.glRotatef(self.cam_azimuth, 0.0, 0.0, 1.0)

        # 1. Static Subsea Water Grid & Compass Reference
        self._draw_opengl_world_grid()

        # 2. Vehicle 6-DOF Attitude Rotation
        GL.glPushMatrix()
        GL.glRotatef(self.yaw, 0.0, 0.0, 1.0)    # Yaw (Z)
        GL.glRotatef(self.pitch, 0.0, 1.0, 0.0)  # Pitch (Y)
        GL.glRotatef(self.roll, 1.0, 0.0, 0.0)   # Roll (X)

        # 3. Draw Submersible Vehicle (Full CAD Solid Model)
        if self.gl_verts is not None and len(self.gl_verts) > 0:
            GL.glEnable(GL.GL_LIGHTING)
            GL.glColor3f(0.24, 0.55, 0.88) # Tactical Marine Cyan-Blue
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, self.gl_verts)
            GL.glNormalPointer(GL.GL_FLOAT, 0, self.gl_normals)
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, len(self.gl_verts))
            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
        else:
            self._draw_opengl_procedural_mesh()

        # 4. Draw 6 Thruster Vector Force Arrows & Exhaust Plumes
        self._draw_opengl_thruster_vectors()

        # 5. Nose Heading Pointer (Forward Bow Indicator)
        GL.glDisable(GL.GL_LIGHTING)
        GL.glLineWidth(3.0)
        GL.glBegin(GL.GL_LINES)
        GL.glColor4f(0.25, 0.85, 1.0, 0.85)
        GL.glVertex3f(0.0, 0.0, 0.0)
        GL.glVertex3f(1.25, 0.0, 0.0)
        GL.glEnd()

        # Cache projected 2D coordinates for screen-space badge labels
        self._cache_screen_thruster_positions(w, h)

        GL.glPopMatrix()

    def _draw_opengl_world_grid(self):
        """Draws static water plane grid, reference axes, and compass circle in OpenGL."""
        GL.glDisable(GL.GL_LIGHTING)
        grid_z = -0.75
        grid_size = 2.0
        grid_step = 0.5

        # Water Grid Plane Lines
        GL.glLineWidth(1.0)
        GL.glBegin(GL.GL_LINES)
        GL.glColor4f(0.18, 0.28, 0.40, 0.45)
        x = -grid_size
        while x <= grid_size + 0.01:
            GL.glVertex3f(x, -grid_size, grid_z); GL.glVertex3f(x, grid_size, grid_z)
            x += grid_step

        y = -grid_size
        while y <= grid_size + 0.01:
            GL.glVertex3f(-grid_size, y, grid_z); GL.glVertex3f(grid_size, y, grid_z)
            y += grid_step
        GL.glEnd()

        # 3D Compass Circle Ring
        GL.glLineWidth(1.5)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glColor4f(0.25, 0.55, 0.85, 0.6)
        r_ring = 1.7
        for i in range(48):
            ang = i * (2.0 * math.pi / 48)
            GL.glVertex3f(math.cos(ang) * r_ring, math.sin(ang) * r_ring, grid_z)
        GL.glEnd()

        # Coordinate Reference Axes (X=Red/Forward, Y=Green/Right, Z=Blue/Up)
        GL.glLineWidth(2.5)
        GL.glBegin(GL.GL_LINES)
        # X Forward (Red)
        GL.glColor3f(0.95, 0.25, 0.25)
        GL.glVertex3f(0.0, 0.0, grid_z); GL.glVertex3f(0.65, 0.0, grid_z)
        # Y Right (Green)
        GL.glColor3f(0.25, 0.85, 0.35)
        GL.glVertex3f(0.0, 0.0, grid_z); GL.glVertex3f(0.0, 0.65, grid_z)
        # Z Up (Blue)
        GL.glColor3f(0.25, 0.60, 0.95)
        GL.glVertex3f(0.0, 0.0, grid_z); GL.glVertex3f(0.0, 0.0, grid_z + 0.65)
        GL.glEnd()

    def _draw_opengl_thruster_vectors(self):
        """
        Draws dynamic 3D thrust vector force arrows (Cyan) and water exhaust plumes (Orange)
        matching the exact physical 45-degree angled and vertical thrusters:
          - Force Arrow: points in the direction of vehicle acceleration.
          - Water Plume: shoots in the opposite direction out of the nozzle.
        """
        GL.glDisable(GL.GL_LIGHTING)
        for i, t in enumerate(self.thruster_data):
            pos = t["pos"]
            f_dir = t["force_dir"]
            pwm_val = self.pwms[i] if i < len(self.pwms) else 1500
            delta_pwm = pwm_val - 1500

            # 1. Thruster Anchor Marker Core (Gold)
            GL.glPointSize(10.0)
            GL.glBegin(GL.GL_POINTS)
            if abs(delta_pwm) > 25:
                GL.glColor3f(1.0, 0.85, 0.20)
            else:
                GL.glColor4f(0.45, 0.55, 0.65, 0.7)
            GL.glVertex3f(*pos)
            GL.glEnd()

            # 2. Dynamic 3D Vectors
            if abs(delta_pwm) > 25:
                sgn = 1.0 if delta_pwm > 0 else -1.0
                f_len = min(0.55, (abs(delta_pwm) / 400.0) * 0.45)
                force_tip = pos + f_dir * (f_len * sgn)
                exhaust_tip = pos - f_dir * (f_len * 0.75 * sgn)

                # A. Vehicle Acceleration Force Vector (Bright Neon Cyan)
                GL.glLineWidth(4.5)
                GL.glBegin(GL.GL_LINES)
                GL.glColor4f(0.0, 0.95, 1.0, 0.95)
                GL.glVertex3f(*pos)
                GL.glVertex3f(*force_tip)

                # B. Water Exhaust Plume Behind Nozzle (Glowing Amber-Orange)
                GL.glColor4f(1.0, 0.45, 0.12, 0.85)
                GL.glVertex3f(*pos)
                GL.glVertex3f(*exhaust_tip)
                GL.glEnd()
            else:
                # Idle Orientation Guideline (Subtle 45°/Vertical line)
                hint_len = 0.14
                hint_tip = pos + f_dir * hint_len
                GL.glLineWidth(1.8)
                GL.glBegin(GL.GL_LINES)
                GL.glColor4f(0.35, 0.55, 0.75, 0.45)
                GL.glVertex3f(*pos)
                GL.glVertex3f(*hint_tip)
                GL.glEnd()

    def _cache_screen_thruster_positions(self, w: int, h: int):
        """Projects 3D thruster coordinates into 2D viewport coordinates for overlay badges."""
        self._thruster_screen_pos = []
        if not HAS_OPENGL:
            return
        try:
            dpr = self.devicePixelRatioF()
            mv = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
            proj = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
            vp = GL.glGetIntegerv(GL.GL_VIEWPORT)
            fb_h = vp[3] if len(vp) >= 4 and vp[3] > 0 else int(h * dpr)
            for i, t in enumerate(self.thruster_data):
                px, py, pz = t["pos"]
                win_x, win_y, win_z = GLU.gluProject(px, py, pz, mv, proj, vp)
                if win_z < 1.0: # In front of camera
                    screen_x = float(win_x / dpr)
                    screen_y = float((fb_h - win_y) / dpr)
                    self._thruster_screen_pos.append((screen_x, screen_y, True, i))
                else:
                    self._thruster_screen_pos.append((0.0, 0.0, False, i))
        except Exception:
            pass

    def _draw_thruster_badges(self, painter: QtGui.QPainter, w: int, h: int):
        """Renders 2D floating badges (T1..T6) directly attached to each thruster."""
        if not self._thruster_screen_pos:
            return

        font_badge = QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold)
        painter.setFont(font_badge)

        for sx, sy, visible, idx in self._thruster_screen_pos:
            if not visible or sx < 10 or sx > w - 10 or sy < 10 or sy > h - 10:
                continue

            t_info = self.thruster_data[idx]
            t_id = t_info["id"]
            pwm = self.pwms[idx] if idx < len(self.pwms) else 1500
            delta = pwm - 1500

            badge_w = 42
            badge_h = 18
            badge_rect = QtCore.QRectF(sx - badge_w / 2.0, sy - badge_h - 10, badge_w, badge_h)

            # Highlight active thrusters with vivid gold/cyan
            if abs(delta) > 25:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(24, 32, 44, 230)))
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 220, 255) if delta > 0 else QtGui.QColor(255, 140, 20), 1.5))
                painter.drawRoundedRect(badge_rect, 3, 3)

                painter.setPen(QtGui.QColor(255, 255, 255))
                painter.drawText(badge_rect, QtCore.Qt.AlignCenter, f"{t_id}:{delta:+d}")
            else:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(16, 20, 26, 180)))
                painter.setPen(QtGui.QPen(QtGui.QColor(45, 55, 68), 1))
                painter.drawRoundedRect(badge_rect, 3, 3)

                painter.setPen(QtGui.QColor(160, 175, 190))
                painter.drawText(badge_rect, QtCore.Qt.AlignCenter, t_id)

    def _draw_opengl_procedural_mesh(self):
        """Draws procedural twin-hull solid faces via OpenGL if no STL is loaded."""
        GL.glEnable(GL.GL_LIGHTING)
        GL.glBegin(GL.GL_TRIANGLES)
        for pts, base_col, _ in self.solid_faces:
            GL.glColor3f(base_col.redF(), base_col.greenF(), base_col.blueF())
            if len(pts) == 3:
                p0, p1, p2 = pts
                u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                nx = u[1] * v[2] - u[2] * v[1]
                ny = u[2] * v[0] - u[0] * v[2]
                nz = u[0] * v[1] - u[1] * v[0]
                n_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                GL.glNormal3f(nx / n_len, ny / n_len, nz / n_len)
                GL.glVertex3f(*p0); GL.glVertex3f(*p1); GL.glVertex3f(*p2)
            elif len(pts) == 4:
                p0, p1, p2, p3 = pts
                u = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                v = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                nx = u[1] * v[2] - u[2] * v[1]
                ny = u[2] * v[0] - u[0] * v[2]
                nz = u[0] * v[1] - u[1] * v[0]
                n_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                GL.glNormal3f(nx / n_len, ny / n_len, nz / n_len)
                GL.glVertex3f(*p0); GL.glVertex3f(*p1); GL.glVertex3f(*p2)
                GL.glVertex3f(*p0); GL.glVertex3f(*p2); GL.glVertex3f(*p3)
        GL.glEnd()

    # =========================================================
    # --- SOFTWARE RENDERING FALLBACK (IF OPENGL UNAVAILABLE) ---
    # =========================================================
    def _render_software_scene(self, w: int, h: int):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(0, 0, w, h, self.bg_color)

        cx = w / 2.0
        cy = h / 2.0
        scale = min(w, h) * 0.33

        faces_to_render = []
        for pts, base_col, border_col in self.solid_faces:
            rot_pts = [self.rotate_point(p, self.roll, self.pitch, self.yaw) for p in pts]
            screen_pts = [self.project_to_screen(rp, cx, cy, scale) for rp in rot_pts]
            avg_depth = sum(sp[2] for sp in screen_pts) / len(screen_pts)
            poly = QtGui.QPolygonF([QtCore.QPointF(sp[0], sp[1]) for sp in screen_pts])
            faces_to_render.append((avg_depth, poly, base_col, border_col))

        faces_to_render.sort(key=lambda x: x[0], reverse=True)
        for _, poly, col, border in faces_to_render:
            painter.setBrush(QtGui.QBrush(col))
            painter.setPen(QtGui.QPen(border, 1.0))
            painter.drawPolygon(poly)

        painter.end()

    def rotate_point(self, pt: Tuple[float, float, float], r_deg: float, p_deg: float, y_deg: float) -> Tuple[float, float, float]:
        x, y, z = pt
        r = math.radians(r_deg)
        p = math.radians(p_deg)
        yw = math.radians(y_deg)
        x1 = x * math.cos(yw) - y * math.sin(yw)
        y1 = x * math.sin(yw) + y * math.cos(yw)
        z1 = z
        x2 = x1 * math.cos(p) + z1 * math.sin(p)
        y2 = y1
        z2 = -x1 * math.sin(p) + z1 * math.cos(p)
        x3 = x2
        y3 = y2 * math.cos(r) - z2 * math.sin(r)
        z3 = y2 * math.sin(r) + z2 * math.cos(r)
        return (x3, y3, z3)

    def project_to_screen(self, pt: Tuple[float, float, float], cx: float, cy: float, scale: float) -> Tuple[float, float, float]:
        x, y, z = pt
        az = math.radians(self.cam_azimuth)
        x_cam = x * math.cos(az) + y * math.sin(az)
        y_cam = -x * math.sin(az) + y * math.cos(az)
        z_cam = z
        el = math.radians(self.cam_elevation)
        x_cam2 = x_cam
        y_cam2 = y_cam * math.cos(el) - z_cam * math.sin(el)
        z_cam2 = y_cam * math.sin(el) + z_cam * math.cos(el)
        distance = 5.0
        depth_factor = distance / (distance + y_cam2 * 0.4)
        sx = cx + x_cam2 * scale * self.cam_zoom * depth_factor
        sy = cy - z_cam2 * scale * self.cam_zoom * depth_factor
        return (sx, sy, y_cam2)

    # =========================================================
    # --- MOUSE INTERACTION (ORBIT & ZOOM) ---
    # =========================================================
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self._last_mouse_pos = event.pos()
        elif event.button() == QtCore.Qt.RightButton:
            self.cam_azimuth = 35.0
            self.cam_elevation = 25.0
            self.cam_zoom = 1.0
            self.update()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._last_mouse_pos is not None:
            dx = event.x() - self._last_mouse_pos.x()
            dy = event.y() - self._last_mouse_pos.y()
            self._last_mouse_pos = event.pos()

            self.cam_azimuth = (self.cam_azimuth + dx * 0.7) % 360.0
            self.cam_elevation = max(-85.0, min(85.0, self.cam_elevation + dy * 0.7))
            self.update()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._last_mouse_pos = None

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            self.cam_zoom = min(3.5, self.cam_zoom * 1.1)
        else:
            self.cam_zoom = max(0.4, self.cam_zoom / 1.1)
        self.update()

    # =========================================================
    # --- HUD TELEMETRY OVERLAY ---
    # =========================================================
    def draw_hud_overlay(self, painter: QtGui.QPainter, w: int, h: int):
        """Draws clean, ergonomic telemetry metrics without clutter or visual noise."""
        painter.save()

        is_dark = getattr(self, "is_dark_theme", True)

        # Top-Left Telemetry Card (Rounded Glass Style)
        card_w = 165
        card_h = 84
        card_rect = QtCore.QRect(10, 10, card_w, card_h)
        if is_dark:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(20, 24, 30, 225)))
            painter.setPen(QtGui.QPen(QtGui.QColor(48, 60, 75), 1))
        else:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 235)))
            painter.setPen(QtGui.QPen(QtGui.QColor(203, 213, 225), 1))
        painter.drawRoundedRect(card_rect, 6, 6)

        painter.setFont(QtGui.QFont("Segoe UI", 9, QtGui.QFont.Bold))
        painter.setPen(QtGui.QColor(74, 144, 226) if is_dark else QtGui.QColor(2, 132, 199))
        painter.drawText(20, 28, "ORIENTASI WAHANA")

        font_val = QtGui.QFont("Segoe UI", 8)
        painter.setFont(font_val)
        painter.setPen(QtGui.QColor(220, 225, 230) if is_dark else QtGui.QColor(30, 41, 59))
        painter.drawText(20, 44, f"Roll       : {self.roll:+.1f}°")
        painter.drawText(20, 58, f"Pitch      : {self.pitch:+.1f}°")
        painter.drawText(20, 72, f"Heading : {self.yaw:05.1f}°")
        painter.drawText(20, 86, f"Kedalaman: {self.depth:.2f} m")

        # Top-Right Model Status Badge
        badge_w = 110
        badge_h = 24
        badge_rect = QtCore.QRect(w - badge_w - 10, 10, badge_w, badge_h)
        if is_dark:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(20, 24, 30, 200)))
            painter.setPen(QtGui.QPen(QtGui.QColor(40, 140, 80) if self.custom_mesh_loaded else QtGui.QColor(70, 80, 95), 1))
        else:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 220)))
            painter.setPen(QtGui.QPen(QtGui.QColor(22, 163, 74) if self.custom_mesh_loaded else QtGui.QColor(203, 213, 225), 1))
        painter.drawRoundedRect(badge_rect, 4, 4)

        painter.setFont(QtGui.QFont("Segoe UI", 7, QtGui.QFont.Bold))
        if self.custom_mesh_loaded:
            painter.setPen(QtGui.QColor(80, 220, 130) if is_dark else QtGui.QColor(22, 163, 74))
            painter.drawText(badge_rect, QtCore.Qt.AlignCenter, "CAD 3D AKTIF")
        else:
            painter.setPen(QtGui.QColor(160, 175, 190) if is_dark else QtGui.QColor(100, 116, 139))
            painter.drawText(badge_rect, QtCore.Qt.AlignCenter, "MODEL BAWAAN")

        # Bottom-Right Orbit Hint (Subtle & Non-distracting)
        hint_w = 200
        hint_h = 22
        hint_rect = QtCore.QRect(w - hint_w - 10, h - hint_h - 10, hint_w, hint_h)
        if is_dark:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(20, 24, 30, 180)))
            painter.setPen(QtGui.QPen(QtGui.QColor(42, 48, 58), 1))
        else:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255, 200)))
            painter.setPen(QtGui.QPen(QtGui.QColor(203, 213, 225), 1))
        painter.drawRoundedRect(hint_rect, 4, 4)

        painter.setFont(QtGui.QFont("Segoe UI", 7))
        painter.setPen(QtGui.QColor(140, 150, 160) if is_dark else QtGui.QColor(100, 116, 139))
        painter.drawText(hint_rect, QtCore.Qt.AlignCenter, "Drag: Rotasi | Scroll: Zoom | R-Click: Reset")

        painter.restore()
