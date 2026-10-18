# -*- coding: utf-8 -*-
"""
Entry Point for Tyrant-AQ AUV Ground Control Station (GCS)
Autonomous Underwater Vehicle - Saguling Water Quality Monitoring System
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Prevent OpenCV's bundled Qt plugin from conflicting with PyQt5 on Linux
if "QT_QPA_PLATFORM_PLUGIN_PATH" in os.environ and "cv2" in os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", ""):
    del os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]

if sys.platform.startswith("linux"):
    try:
        import PyQt5
        pyqt_plugins = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins")
        if os.path.exists(pyqt_plugins) and "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = pyqt_plugins
    except Exception:
        pass

from PyQt5 import QtWidgets, QtCore
from ui.main_window import MainWindow


def get_config_path() -> str:
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        local_cfg = os.path.join(exe_dir, "config", "gui_config.json")
        if os.path.exists(local_cfg):
            return local_cfg
        if hasattr(sys, "_MEIPASS"):
            meipass_cfg = os.path.join(sys._MEIPASS, "config", "gui_config.json")
            if os.path.exists(meipass_cfg):
                try:
                    os.makedirs(os.path.join(exe_dir, "config"), exist_ok=True)
                    import shutil
                    shutil.copy2(meipass_cfg, local_cfg)
                    return local_cfg
                except Exception:
                    return meipass_cfg
        return local_cfg
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "gui_config.json")


def main():
    # Enable High DPI scaling
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    # Remove any conflicting cv2 Qt plugin paths
    for p in list(QtWidgets.QApplication.libraryPaths()):
        if "cv2" in p:
            QtWidgets.QApplication.removeLibraryPath(p)

    app.setApplicationName("Tyrant-AQ AUV GCS")
    app.setOrganizationName("Telkom University - Electrical Engineering")

    config_path = get_config_path()
    window = MainWindow(config_path=config_path)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
