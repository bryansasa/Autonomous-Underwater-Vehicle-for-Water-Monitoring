# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec for Tyrant-AQ AUV Ground Control Station (GCS)
Includes:
  - 3D Navigasi CAD OpenGL
  - PFD 2D HUD
  - EA-DSRA Power & Sampling Management Widget
  - 6-Thruster Propulsion Matrix
  - Foxglove Studio Companion WebSocket Bridge
  - Real Hardware & Built-in Dummy Simulator Engine
"""
import sys
import os

block_cipher = None

project_dir = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(project_dir, 'config'), 'config'),
    (os.path.join(project_dir, 'assets'), 'assets'),
    (os.path.join(project_dir, 'ui', 'styles'), 'ui/styles'),
    (os.path.join(project_dir, 'ui', 'styles'), 'styles'),
]

hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'PyQt5.QtOpenGL',
    'OpenGL',
    'OpenGL.GL',
    'OpenGL.GLU',
    'OpenGL.platform',
    'OpenGL.platform.win32',
    'OpenGL.arrays',
    'OpenGL.arrays.ctypesarrays',
    'pyqtgraph',
    'numpy',
    'serial',
    'serial.tools.list_ports',
    'websockets',
    'websockets.legacy',
    'websockets.legacy.server',
    'asyncio',
    'pygame',
    'core',
    'core.comm_engine',
    'core.telemetry_parser',
    'core.internal_simulator',
    'core.event_hook',
    'core.foxglove_bridge',
    'core.gcs_service',
    'core.joystick_manager',
    'core.qt_adapter',
    'core.alert_engine',
    'core.data_logger',
    'ui',
    'ui.main_window',
    'ui.widgets',
    'ui.widgets.quick_action_bar',
    'ui.widgets.main_control_tab',
    'ui.widgets.sensor_graph_tab',
    'ui.widgets.csv_importer_tab',
    'ui.widgets.mission_control',
    'ui.widgets.config_settings_tab',
    'ui.widgets.submersible_3d_widget',
    'ui.widgets.pfd_widget',
    'ui.widgets.camera_feed_widget',
    'ui.widgets.thruster_matrix',
    'ui.widgets.water_quality_card',
    'ui.widgets.power_dsra_widget',
]

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'torch'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Tyrant-AQ_GCS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Tyrant-AQ_GCS',
)
