import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

class MainControlPanel(QWidget):
    def __init__(self, simulator_backend, parent=None): # simulator_backend passed in
        super().__init__(parent)
        self.simulator_backend = simulator_backend # Store reference
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Control Buttons Section ---
        control_buttons_layout = QHBoxLayout()
        self.start_acquisition_button = QPushButton("Start Acquisition") # Renamed
        self.start_acquisition_button.setToolTip("Start image acquisition and streaming for DefaultCam.")
        self.stop_acquisition_button = QPushButton("Stop Acquisition") # Renamed
        self.stop_acquisition_button.setToolTip("Stop image acquisition and streaming for DefaultCam.")
        self.stop_acquisition_button.setEnabled(False) # Initially disabled
        control_buttons_layout.addWidget(self.start_acquisition_button)
        control_buttons_layout.addWidget(self.stop_acquisition_button)
        main_layout.addLayout(control_buttons_layout)

        # --- Camera Management Buttons Section ---
        camera_buttons_layout = QHBoxLayout()
        self.new_cam_button = QPushButton("Add Virtual Camera")
        self.new_cam_button.setToolTip("Add a new placeholder virtual camera to the list below (UI only).") # Enhanced tooltip
        self.delete_cam_button = QPushButton("Remove Virtual Camera")
        self.delete_cam_button.setToolTip("Remove the selected placeholder virtual camera from the list (UI only).") # Enhanced tooltip
        self.delete_cam_button.setEnabled(False) # Initially disabled
        camera_buttons_layout.addWidget(self.new_cam_button)
        camera_buttons_layout.addWidget(self.delete_cam_button)
        main_layout.addLayout(camera_buttons_layout)

        # --- Camera List Table Section ---
        self.camera_table = QTableWidget()
        self.camera_table.setToolTip("Displays simulated camera instances. 'DefaultCam' is linked to the backend.") # Added tooltip
        self.camera_table.setColumnCount(3)
        self.camera_table.setHorizontalHeaderLabels(["Name", "IP Address / Identifier", "Status"])
        self.camera_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.camera_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.camera_table.horizontalHeader().setStretchLastSection(True)
        self.camera_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.camera_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # Read-only table
        main_layout.addWidget(self.camera_table)

        self.setLayout(main_layout)

        # Connect signals to slots
        self.start_acquisition_button.clicked.connect(self._on_start_acquisition) # Renamed slot
        self.stop_acquisition_button.clicked.connect(self._on_stop_acquisition)   # Renamed slot
        self.new_cam_button.clicked.connect(self._on_new_camera)
        self.delete_cam_button.clicked.connect(self._on_delete_camera)
        self.camera_table.itemSelectionChanged.connect(self._on_camera_selection_changed)
        self.camera_table.setToolTip("List of simulated camera instances. Select a row to manage (UI only for non-DefaultCam).")


        self._add_default_camera_entry()

    def _add_default_camera_entry(self):
        """Adds the initial 'DefaultCam' entry that represents the backend simulator instance."""
        self._add_camera_to_table("DefaultCam", "N/A (Core Simulator)", "Stopped (Ready)")

    def _add_camera_to_table(self, name, ip_address, status):
        """Helper function to add a new row to the camera table."""
        row_position = self.camera_table.rowCount()
        self.camera_table.insertRow(row_position)
        self.camera_table.setItem(row_position, 0, QTableWidgetItem(name))
        self.camera_table.setItem(row_position, 1, QTableWidgetItem(ip_address))
        self.camera_table.setItem(row_position, 2, QTableWidgetItem(status))
        logger.debug(f"Added camera to table: Name='{name}', IP='{ip_address}', Status='{status}'")

    def _on_start_acquisition(self): # Renamed
        """Handles starting the acquisition for the DefaultCam."""
        logger.info("Start Acquisition button clicked for DefaultCam.")
        if self.simulator_backend:
            if not self.simulator_backend.is_running: # Ensure servers are running first
                logger.info("Backend servers not running, starting them now...")
                self.simulator_backend.start_servers()
                # Could add a small delay or check here if needed, but start_servers is synchronous for thread creation

            self.simulator_backend.trigger_acquisition_start()
            self.update_camera_status("DefaultCam", "Acquiring")
            self.start_acquisition_button.setEnabled(False)
            self.stop_acquisition_button.setEnabled(True)
            logger.info("AcquisitionStart triggered for DefaultCam via UI.")
        else:
            logger.error("Simulator backend not available to start acquisition.")
            QMessageBox.critical(self, "Error", "Simulator backend not available.")

    def _on_stop_acquisition(self): # Renamed
        """Handles stopping the acquisition for the DefaultCam."""
        logger.info("Stop Acquisition button clicked for DefaultCam.")
        if self.simulator_backend:
            self.simulator_backend.trigger_acquisition_stop()
            self.update_camera_status("DefaultCam", "Stopped (Ready)") # More descriptive status
            self.start_acquisition_button.setEnabled(True)
            self.stop_acquisition_button.setEnabled(False)
            logger.info("AcquisitionStop triggered for DefaultCam via UI.")
            # Note: This does not stop the backend servers (Discovery/GVCP listeners)
            # Those are stopped by the MainControlPanel's "Stop Simulation Backend" if that was the design.
            # For now, this button only controls acquisition.
        else:
            logger.error("Simulator backend not available to stop acquisition.")
            QMessageBox.critical(self, "Error", "Simulator backend not available.")


    def _on_new_camera(self):
        """Handles adding a new (placeholder) virtual camera entry to the table."""
        logger.info("New Virtual Camera button clicked.")
        cam_name, ok = QInputDialog.getText(self, "New Virtual Camera", "Enter Camera Name:")
        if ok and cam_name:
            # Check if camera name already exists
            for row in range(self.camera_table.rowCount()):
                if self.camera_table.item(row, 0).text() == cam_name:
                    QMessageBox.warning(self, "Duplicate Name", f"A camera with the name '{cam_name}' already exists.")
                    return
            self._add_camera_to_table(cam_name, "N/A (UI Mockup)", "Not Initialized")
        else:
            logger.debug("New camera dialog cancelled or empty name.")

    def _on_delete_camera(self):
        """Handles deleting the selected virtual camera entry from the table."""
        logger.info("Delete Virtual Camera button clicked.")
        selected_items = self.camera_table.selectedItems()
        if not selected_items:
            logger.warning("Delete camera called but no camera selected.")
            QMessageBox.information(self, "No Selection", "Please select a camera to delete.")
            return

        selected_row = self.camera_table.currentRow()
        camera_name_item = self.camera_table.item(selected_row, 0)
        if not camera_name_item: # Should not happen if a row is selected
            return

        camera_name = camera_name_item.text()

        # Prevent deletion of the "DefaultCam" which represents the core simulator
        if camera_name == "DefaultCam":
            QMessageBox.warning(self, "Cannot Delete", "The 'DefaultCam' represents the core simulator and cannot be deleted from the UI.")
            return

        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete camera '{camera_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.camera_table.removeRow(selected_row)
            logger.info(f"Camera '{camera_name}' removed from UI table.")
            self._on_camera_selection_changed() # Update button state
        else:
            logger.debug(f"Deletion of camera '{camera_name}' cancelled.")


    def _on_camera_selection_changed(self):
        """Enables or disables the delete button based on table selection."""
        selected_items = self.camera_table.selectedItems()
        if selected_items:
            # Check if the selected camera is the "DefaultCam"
            camera_name = self.camera_table.item(self.camera_table.currentRow(), 0).text()
            if camera_name == "DefaultCam":
                self.delete_cam_button.setEnabled(False)
                self.delete_cam_button.setToolTip("The 'DefaultCam' cannot be deleted.")
            else:
                self.delete_cam_button.setEnabled(True)
                self.delete_cam_button.setToolTip("Remove the selected virtual camera (UI only).")
        else:
            self.delete_cam_button.setEnabled(False)
            self.delete_cam_button.setToolTip("Select a camera to delete.")
        logger.debug(f"Camera selection changed. Delete button enabled: {self.delete_cam_button.isEnabled()}")

    def update_camera_status(self, name, new_status):
        """Updates the status of a camera in the table by its name."""
        for row in range(self.camera_table.rowCount()):
            name_item = self.camera_table.item(row, 0)
            if name_item and name_item.text() == name:
                status_item = self.camera_table.item(row, 2)
                if status_item:
                    status_item.setText(new_status)
                    logger.debug(f"Updated status for camera '{name}' to '{new_status}'.")
                else: # Should not happen if table is populated correctly
                    new_status_item = QTableWidgetItem(new_status)
                    self.camera_table.setItem(row, 2, new_status_item)
                    logger.debug(f"Added status for camera '{name}' to '{new_status}' (item was missing).")
                return
        logger.warning(f"Camera '{name}' not found in table to update status.")
