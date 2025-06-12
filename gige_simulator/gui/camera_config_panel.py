import logging
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog, QMessageBox, QGroupBox, QRadioButton
)
from PyQt6.QtGui import QIntValidator, QDoubleValidator
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

class CameraConfigPanel(QWidget):
    def __init__(self, simulator_backend, parent=None): # simulator_backend passed in
        super().__init__(parent)
        self.simulator_backend = simulator_backend # Store reference
        self._init_ui()
        self.load_initial_config_from_backend() # Load initial values

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Camera Parameters Group ---
        params_group = QGroupBox("Camera Parameters")
        params_group.setToolTip("Configure core camera parameters. These settings aim to update the backend simulator.")
        form_layout = QFormLayout(params_group)

        self.camera_name_edit = QLineEdit()
        self.camera_name_edit.setToolTip("Reflects the DeviceModelName from the backend. Read-only here.")
        self.camera_name_edit.setReadOnly(True)
        form_layout.addRow("Camera Name:", self.camera_name_edit)

        self.width_edit = QLineEdit()
        self.width_edit.setValidator(QIntValidator(64, 8192))
        self.width_edit.setToolTip("Frame width in pixels (e.g., 64 to 8192). Applied to backend.")
        form_layout.addRow("Width:", self.width_edit)

        self.height_edit = QLineEdit()
        self.height_edit.setValidator(QIntValidator(64, 8192))
        self.height_edit.setToolTip("Frame height in pixels (e.g., 64 to 8192). Applied to backend.")
        form_layout.addRow("Height:", self.height_edit)

        self.framerate_edit = QLineEdit()
        self.framerate_edit.setValidator(QDoubleValidator(0.1, 1000.0, 2))
        self.framerate_edit.setText("N/A (Not Implemented)") # Default example
        self.framerate_edit.setReadOnly(True) # As per subtask requirement
        self.framerate_edit.setToolTip("Target frame rate (FPS). Currently read-only and not implemented in backend.")
        form_layout.addRow("Frame Rate (FPS):", self.framerate_edit)

        self.pixel_format_combo = QComboBox()
        self.pixel_format_combo.setToolTip("Select the pixel format for the image data. Applied to backend.")
        self.pixel_format_combo.addItem("Mono8 (0x01080001)", 0x01080001)
        self.pixel_format_combo.addItem("RGB8Packed (0x02180014)", 0x02180014)
        form_layout.addRow("Pixel Format:", self.pixel_format_combo)

        self.ip_address_edit = QLineEdit("N/A (Backend Defined)")
        self.ip_address_edit.setReadOnly(True)
        self.ip_address_edit.setToolTip("Current IP address of the simulated device (defined by backend). Read-only.")
        form_layout.addRow("Device IP Address:", self.ip_address_edit)

        self.mac_address_edit = QLineEdit("N/A (Backend Defined)")
        self.mac_address_edit.setReadOnly(True)
        self.mac_address_edit.setToolTip("MAC address of the simulated device (defined by backend). Read-only.")
        form_layout.addRow("Device MAC Address:", self.mac_address_edit)

        # GVSP Client Destination (GevSCPHostAddress, GevSCPHostPort)
        self.client_ip_edit = QLineEdit()
        self.client_ip_edit.setPlaceholderText("e.g., 192.168.1.200")
        self.client_ip_edit.setToolTip("IP address of the client PC to stream GVSP data to. Applied to backend.")
        form_layout.addRow("GVSP Client IP:", self.client_ip_edit)

        self.client_port_edit = QLineEdit()
        self.client_port_edit.setValidator(QIntValidator(1024, 65535))
        self.client_port_edit.setPlaceholderText("e.g., 5004")
        self.client_port_edit.setToolTip("Port on the client PC to stream GVSP data to (1024-65535). Applied to backend.")
        form_layout.addRow("GVSP Client Port:", self.client_port_edit)

        main_layout.addWidget(params_group)

        # --- Trigger Mode Group ---
        trigger_group = QGroupBox("Trigger Mode")
        trigger_group.setToolTip("Select the camera's trigger mode (currently UI only).")
        trigger_layout = QHBoxLayout(trigger_group)
        self.freerun_radio = QRadioButton("Free Run")
        self.software_trigger_radio = QRadioButton("Software Trigger")
        self.freerun_radio.setChecked(True)
        self.freerun_radio.setToolTip("Camera continuously acquires images (simulated backend controls actual start/stop).")
        self.software_trigger_radio.setToolTip("Camera acquires one frame upon software trigger command (simulated by backend).")
        trigger_layout.addWidget(self.freerun_radio)
        trigger_layout.addWidget(self.software_trigger_radio)
        trigger_layout.addStretch()
        main_layout.addWidget(trigger_group)

        # --- Action Buttons ---
        action_buttons_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply to Backend")
        self.apply_button.setToolTip("Apply current parameter settings to the running backend simulator.")
        self.save_button = QPushButton("Save Config to File")
        self.save_button.setToolTip("Save the current camera configuration settings (from this panel) to a JSON file.")
        self.load_button = QPushButton("Load Config from File")
        self.load_button.setToolTip("Load camera configuration settings from a JSON file into this panel.")
        self.reset_button = QPushButton("Reset UI to Defaults")
        self.reset_button.setToolTip("Reset the fields in this panel to their initial default values.")

        action_buttons_layout.addWidget(self.apply_button)
        action_buttons_layout.addWidget(self.save_button)
        action_buttons_layout.addWidget(self.load_button)
        action_buttons_layout.addWidget(self.reset_button)
        main_layout.addLayout(action_buttons_layout)

        main_layout.addStretch() # Push elements to the top
        self.setLayout(main_layout)

        # Connect signals
        self.apply_button.clicked.connect(self._on_apply_config)
        self.save_button.clicked.connect(self._on_save_config)
        self.load_button.clicked.connect(self._on_load_config)
        self.reset_button.clicked.connect(self._on_reset_defaults)

    def load_initial_config_from_backend(self):
        logger.debug("Attempting to load initial config from backend for CameraConfigPanel.")
        if not self.simulator_backend:
            logger.error("SimulatorBackend not available for loading initial config.")
            self._on_reset_defaults() # Fallback to UI defaults
            return

        gvcp_module = self.simulator_backend.get_gvcp_module()
        if not gvcp_module:
            logger.error("GVCP module from SimulatorBackend not available.")
            self._on_reset_defaults()
            return

        try:
            self.width_edit.setText(str(gvcp_module.camera_registers.get(0x0A00, 640)))
            self.height_edit.setText(str(gvcp_module.camera_registers.get(0x0A04, 480)))

            pfnc_value = gvcp_module.camera_registers.get(0x0A08, PFNC_MONO8)
            self.set_pixel_format_selection(pfnc_value)

            model_name_addr = gvcp_module.camera_registers.get(0x0068)
            if model_name_addr is not None:
                cam_name = gvcp_module.get_string_from_memory(model_name_addr, 32)
                self.camera_name_edit.setText(cam_name if cam_name else "PySimCam_Backend")
            else:
                self.camera_name_edit.setText("PySimCam_Backend")

            # Load GevSCPHostAddress (0x0D1C) and GevSCPHostPort (0x0D18)
            client_ip_int = gvcp_module.camera_registers.get(0x0D1C, 0)
            client_port_int = gvcp_module.camera_registers.get(0x0D18, 0)
            self.client_ip_edit.setText(self.simulator_backend._ip_int_to_str(client_ip_int) if client_ip_int != 0 else "")
            self.client_port_edit.setText(str(client_port_int) if client_port_int != 0 else "")

            # For Device IP and MAC, these are typically from the discovery module's constants
            # or a more central device configuration store if it existed.
            # For now, using placeholders as they are not directly part of GVCP settable registers.
            if hasattr(gvcp_module.discovery_module, 'DEVICE_IP_ADDRESS'): # Check if accessible
                 self.ip_address_edit.setText(gvcp_module.discovery_module.DEVICE_IP_ADDRESS)
                 self.mac_address_edit.setText(gvcp_module.discovery_module.DEVICE_MAC_ADDRESS)


            logger.info("Initial config loaded from backend into CameraConfigPanel.")
        except Exception as e:
            logger.error(f"Error loading initial config from backend: {e}", exc_info=True)
            self._on_reset_defaults()

    def _on_apply_config(self):
        logger.info("Apply to Backend button clicked.")
        if not self.simulator_backend:
            logger.error("SimulatorBackend not available to apply config.")
            QMessageBox.critical(self, "Error", "Backend service not available.")
            return

        try:
            config_dict = {
                'width': self.width_edit.text(),
                'height': self.height_edit.text(),
                'pixel_format_pfnc': self.get_pixel_format_from_selection(),
                'camera_name': self.camera_name_edit.text(), # Though RO, pass it for completeness
                'client_ip': self.client_ip_edit.text(),
                'client_port': self.client_port_edit.text()
            }

            self.simulator_backend.apply_camera_config(config_dict)

            logger.info(f"Configuration sent to backend for application: {config_dict}")
            QMessageBox.information(self, "Applied", "Configuration sent to backend.")
        except ValueError as ve: # Catch potential int/float conversion errors
            logger.error(f"Invalid input value for applying config: {ve}")
            QMessageBox.warning(self, "Input Error", f"Invalid value in form: {ve}")
        except Exception as e:
            logger.error(f"Error applying config to backend: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to apply configuration: {e}")


    def _on_save_config(self):
        logger.info("Save Config to File button clicked.")
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Configuration", "", "JSON Files (*.json)")
        if not file_path:
            logger.debug("Save configuration dialog cancelled.")
            return

        config_data = {
            "camera_name": self.camera_name_edit.text(), # Though RO, save what's displayed
            "width": self.width_edit.text(),
            "height": self.height_edit.text(),
            "framerate": self.framerate_edit.text(),
            "pixel_format_pfnc": self.get_pixel_format_from_selection(),
            "pixel_format_text": self.pixel_format_combo.currentText(),
            "trigger_mode": "FreeRun" if self.freerun_radio.isChecked() else "SoftwareTrigger"
        }
        try:
            with open(file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            logger.info(f"Configuration saved to {file_path}")
            QMessageBox.information(self, "Saved", f"Configuration saved to\n{file_path}")
        except Exception as e:
            logger.error(f"Error saving configuration to {file_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")

    def _on_load_config(self):
        logger.info("Load Config from File button clicked.")
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Configuration", "", "JSON Files (*.json)")
        if not file_path:
            logger.debug("Load configuration dialog cancelled.")
            return

        try:
            with open(file_path, 'r') as f:
                config_data = json.load(f)

            # self.camera_name_edit.setText(config_data.get("camera_name", "LoadedCam")) # If name were settable
            self.width_edit.setText(config_data.get("width", "640"))
            self.height_edit.setText(config_data.get("height", "480"))
            self.framerate_edit.setText(config_data.get("framerate", "30.0"))

            pfnc_value = config_data.get("pixel_format_pfnc")
            if pfnc_value is not None:
                self.set_pixel_format_selection(pfnc_value)

            trigger_mode = config_data.get("trigger_mode", "FreeRun")
            if trigger_mode == "SoftwareTrigger":
                self.software_trigger_radio.setChecked(True)
            else:
                self.freerun_radio.setChecked(True)

            logger.info(f"Configuration loaded from {file_path}")
            QMessageBox.information(self, "Loaded", f"Configuration loaded from\n{file_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {file_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration:\n{e}")


    def _on_reset_defaults(self):
        logger.info("Reset UI to Defaults button clicked.")
        self.width_edit.setText("640")
        self.height_edit.setText("480")
        self.framerate_edit.setText("30.0")
        self.set_pixel_format_selection(0x01080001) # Mono8
        self.freerun_radio.setChecked(True)
        # self.camera_name_edit.setText("PySimCamDefault_UIReset") # If it were editable
        logger.debug("UI fields reset to default values.")

    def get_pixel_format_from_selection(self):
        """Returns the PFNC value of the currently selected pixel format."""
        return self.pixel_format_combo.currentData()

    def set_pixel_format_selection(self, pfnc_value):
        """Sets the ComboBox selection based on the PFNC value."""
        for index in range(self.pixel_format_combo.count()):
            if self.pixel_format_combo.itemData(index) == pfnc_value:
                self.pixel_format_combo.setCurrentIndex(index)
                return
        logger.warning(f"PFNC value 0x{pfnc_value:08X} not found in ComboBox.")
        if self.pixel_format_combo.count() > 0:
             self.pixel_format_combo.setCurrentIndex(0) # Default to first item if not found
