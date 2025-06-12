import sys
import os # Added for path manipulation
import logging # For placeholder actions

# Path Setup for direct execution:
# Ensures that when gui_main.py is run directly, Python can find the gige_simulator package.
if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # gige_simulator/
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR) # /app/
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLabel, QStatusBar, QDockWidget, QTextEdit
)
from PyQt6.QtGui import QAction, QIcon # Added QIcon
from PyQt6.QtCore import Qt, QSize
from gige_simulator.gui.main_control_panel import MainControlPanel
from gige_simulator.gui.camera_config_panel import CameraConfigPanel
from gige_simulator.gui.image_source_panel import ImageSourcePanel
from gige_simulator.gui.network_log_panel import NetworkLogPanel
from gige_simulator.core.simulator_backend import SimulatorBackend # Import the backend

# Import backend module for the service provider function - NO LONGER NEEDED directly by panels
# from gige_simulator.network import gvcp as gvcp_backend_module

# Helper functions to pass backend to panels are no longer needed if backend is passed to MainWindow
# def get_gvcp_service():
#     """Provides access to the GVCP backend module."""
#     return gvcp_backend_module

# def get_image_source_backend_instance():
#     """Provides access to the global image_source_global instance from the GVCP module."""
#     return gvcp_backend_module.image_source_global

# Configure basic logging for GUI actions (if main CLI logging isn't running)
# This is mainly for when running gui_main.py directly for development.
if __name__ == "__main__": # Only configure if this is the entry point
    # Basic configuration for the script itself, if needed for early messages.
    # The main 'gige_simulator' package logger is configured further down before MainWindow.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# This logger is for gui_main.py itself. Child panel loggers will be separate.
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, simulator_backend, parent=None): # Added simulator_backend
        super().__init__(parent)
        self.simulator_backend = simulator_backend # Store the backend instance
        self.dark_mode_enabled = False # Initialize theme state

        self.setWindowTitle("GigE Vision Camera Simulator")
        self.setMinimumSize(QSize(800, 600))
        self.resize(1200, 800)

        self._create_toolbar()
        self._create_status_bar()
        self._create_panels() # This will now pass the backend to panels

        self.show()

    def _create_toolbar(self):
        """Creates and populates the main toolbar with actions."""
        self.toolbar = QToolBar("Main Toolbar") # Store as self.toolbar
        self.addToolBar(self.toolbar)

        # New Camera Action
        new_cam_action = QAction(QIcon.fromTheme("document-new"), "New Cam", self)
        new_cam_action.setToolTip("Create a new virtual camera instance (Not Implemented)")
        new_cam_action.triggered.connect(self._on_new_cam)
        self.toolbar.addAction(new_cam_action)

        # Save Configuration Action
        save_config_action = QAction(QIcon.fromTheme("document-save"), "Save Cfg", self)
        save_config_action.setToolTip("Save current simulator configuration (Not Implemented)")
        save_config_action.triggered.connect(self._on_save_config)
        self.toolbar.addAction(save_config_action)

        # Load Configuration Action
        load_config_action = QAction(QIcon.fromTheme("document-open"), "Load Cfg", self)
        load_config_action.setToolTip("Load simulator configuration from file (Not Implemented)")
        load_config_action.triggered.connect(self._on_load_config)
        self.toolbar.addAction(load_config_action)

        self.toolbar.addSeparator()

        # Refresh Status Action
        refresh_status_action = QAction(QIcon.fromTheme("view-refresh"), "Refresh", self)
        refresh_status_action.setToolTip("Refresh current status displays (Not Implemented)")
        refresh_status_action.triggered.connect(self._on_refresh_status)
        self.toolbar.addAction(refresh_status_action)

        self.toolbar.addSeparator()

        # Help Action
        help_action = QAction(QIcon.fromTheme("help-contents"), "Help", self)
        help_action.setToolTip("Show help (Not Implemented)")
        help_action.triggered.connect(self._on_help)
        self.toolbar.addAction(help_action)

        # Toggle Theme Action (Example for a non-icon action)
        theme_action = QAction("Toggle Theme", self)
        theme_action.setToolTip("Toggle UI theme (Not Implemented)")
        theme_action.triggered.connect(self._on_toggle_theme)
        self.toolbar.addAction(theme_action)


    def _create_status_bar(self):
        """Creates the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - GigE Vision Camera Simulator Initialized")

    def _create_panels(self):
        """Creates the dockable panels for different functionalities."""
        self.setDockNestingEnabled(True)

        # Main Control Panel
        self.main_control_dock = QDockWidget("Main Control", self) # Store as instance member
        self.main_control_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        # Create and set the MainControlPanel widget
        main_control_widget = MainControlPanel(self.simulator_backend, self)
        self.main_control_dock.setWidget(main_control_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.main_control_dock)

        # Camera Configuration Panel
        self.cam_config_dock = QDockWidget("Camera Configuration", self)
        self.cam_config_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        # Create and set the CameraConfigPanel widget
        camera_config_widget = CameraConfigPanel(self.simulator_backend, self) # Pass backend
        self.cam_config_dock.setWidget(camera_config_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.cam_config_dock)

        self.tabifyDockWidget(self.main_control_dock, self.cam_config_dock)
        self.main_control_dock.raise_()

        # Image Preview & Source Management Panel
        self.image_source_dock = QDockWidget("Image Preview & Source", self)
        self.image_source_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        self.image_source_widget = ImageSourcePanel(self.simulator_backend, self) # Pass backend
        self.image_source_dock.setWidget(self.image_source_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.image_source_dock)

        # Network Status & Log Window Panel
        self.log_dock = QDockWidget("Network & Logs", self) # Store as instance member
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        # Create and set the NetworkLogPanel widget
        # The NetworkLogPanel's _setup_logging method will attach its handler.
        network_log_widget = NetworkLogPanel(self)
        self.log_dock.setWidget(network_log_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        # Note: The old self.log_text_edit is now encapsulated within NetworkLogPanel.
        # If MainWindow methods need to log, they should use standard Python logging to 'gige_simulator'
        # and it will be picked up by the handler in NetworkLogPanel.

    # --- Placeholder methods for QAction triggers ---
    def _on_new_cam(self):
        message = "Action: New Camera triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000) # Show for 3 seconds
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)

    def _on_save_config(self):
        message = "Action: Save Config triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000)
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)

    def _on_load_config(self):
        message = "Action: Load Config triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000)
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)

    def _on_refresh_status(self):
        message = "Action: Refresh Status triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000)
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)

    def _on_help(self):
        message = "Action: Help triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000)
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)

    def _on_toggle_theme(self):
        message = "Action: Toggle Theme triggered (Not Implemented)"
        logger.info(message)
        self.status_bar.showMessage(message, 3000)
        if hasattr(self, 'log_text_edit'): self.log_text_edit.append(message)
        # Example: could toggle a simple stylesheet or re-apply a global one
        # For a real theme change, one might load a .qss file or set a palette.
        # QApplication.instance().setStyleSheet("QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }")
        if self.dark_mode_enabled:
            # Example: Apply a dark stylesheet (very basic)
            # For a real application, you'd use a more comprehensive stylesheet or a library.
            # QApplication.instance().setStyleSheet("QWidget { background-color: #333; color: #EEE; }")
            # self.log_text_edit.setStyleSheet("background-color: #222; color: #DDD;") # Example for one widget
            pass # Visual change not implemented in this step
        else:
            # QApplication.instance().setStyleSheet("") # Clear stylesheet to revert to default
            pass # Visual change not implemented in this step
        self.setWindowTitle(f"GigE Vision Camera Simulator{'' if not self.dark_mode_enabled else ' [Dark Mode Placeholder]'} ")


if __name__ == "__main__":
    # Setup logging for the 'gige_simulator' package BEFORE creating MainWindow,
    # so that NetworkLogPanel's handler can be added to an already configured logger.
    package_logger = logging.getLogger('gige_simulator')
    package_logger.setLevel(logging.DEBUG) # Set to DEBUG to capture all levels for the handler to filter.
    # Optional: Add a console handler to see logs in console when running GUI directly for dev.
    # console_handler = logging.StreamHandler(sys.stdout) # For console output
    # console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    # console_handler.setFormatter(console_formatter)
    # if not package_logger.handlers: # Add handler only if no handlers are configured
    #    package_logger.addHandler(console_handler)
    # package_logger.propagate = False # Optional: stop log from propagating to root logger

    # Default image path for GUI direct launch if not using CLI args for GUI
    # This path should exist or be handled gracefully by SimulatorBackend/ImageSource
    default_gui_image_path = "gige_simulator/sample_images/sample_image.png"
    # Create the backend instance
    simulator_backend = SimulatorBackend(default_image_path=default_gui_image_path)
    # Note: For GUI, server start/stop is typically handled by GUI buttons, not auto-started here.

    app = QApplication(sys.argv)
    main_win = MainWindow(simulator_backend) # Pass backend to MainWindow
    # main_win.show() # Already called in MainWindow's __init__

    # Call load_initial_preview after the event loop has started or window is shown
    # Using QTimer.singleShot to ensure it runs after __init__ is fully complete and window is up.
    from PyQt6.QtCore import QTimer
    if hasattr(main_win, 'image_source_widget') and main_win.image_source_widget:
        QTimer.singleShot(0, main_win.image_source_widget.load_initial_preview)

    sys.exit(app.exec())
