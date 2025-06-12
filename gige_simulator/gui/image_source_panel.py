import logging
import os # Added os for basename in error message
from PIL import Image, ImageDraw
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QFileDialog, QGroupBox, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QSize

logger = logging.getLogger(__name__)

# PFNC Values (Pixel Format Naming Convention)
PFNC_MONO8 = 0x01080001
PFNC_RGB8_PACKED = 0x02180014 # For RGB8

class ImageSourcePanel(QWidget):
    def __init__(self, simulator_backend, parent=None): # simulator_backend passed in
        super().__init__(parent)
        self.simulator_backend = simulator_backend # Store reference
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Image Preview Group ---
        preview_group = QGroupBox("Image Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("No image loaded or source selected.")
        self.preview_label.setToolTip("Displays the current image from the selected source after loading.")
        self.preview_label.setMinimumSize(320, 240)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: #333;")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        preview_layout.addWidget(self.preview_label)
        main_layout.addWidget(preview_group)

        # --- Source Selection Group ---
        source_group = QGroupBox("Image Source Control")
        source_group.setToolTip("Select and configure the source of the image data for the simulator.")
        source_main_layout = QVBoxLayout(source_group)

        self.source_type_combo = QComboBox()
        self.source_type_combo.setToolTip("Select the type of image source: a static file or a generated test pattern.")
        self.source_type_combo.addItem("Static Image")
        self.source_type_combo.addItem("Test Pattern")
        source_main_layout.addWidget(self.source_type_combo)

        # -- Static Image Sub-Panel --
        self.static_image_panel = QWidget()
        static_image_layout = QHBoxLayout(self.static_image_panel)
        static_image_layout.setContentsMargins(0,0,0,0)
        self.static_image_path_edit = QLineEdit()
        self.static_image_path_edit.setPlaceholderText("Path to image file...")
        self.static_image_path_edit.setReadOnly(True)
        self.static_image_path_edit.setToolTip("Path to the selected static image file.")
        browse_image_button = QPushButton("Browse...")
        browse_image_button.setToolTip("Browse for an image file (PNG, JPG, BMP, TIFF).")
        static_image_layout.addWidget(self.static_image_path_edit)
        static_image_layout.addWidget(browse_image_button)
        source_main_layout.addWidget(self.static_image_panel)

        # -- Test Pattern Sub-Panel --
        self.test_pattern_panel = QWidget()
        test_pattern_layout = QHBoxLayout(self.test_pattern_panel)
        test_pattern_layout.setContentsMargins(0,0,0,0)
        self.test_pattern_combo = QComboBox()
        self.test_pattern_combo.setToolTip("Select a pre-defined test pattern to generate.")
        self.test_pattern_combo.addItem("Solid Color (Gray)")
        self.test_pattern_combo.addItem("Grayscale Ramp (Horizontal)")
        test_pattern_layout.addWidget(self.test_pattern_combo)
        source_main_layout.addWidget(self.test_pattern_panel)

        self.load_refresh_button = QPushButton("Load Source & Update Backend")
        self.load_refresh_button.setToolTip("Load the selected image/pattern into the backend and update camera parameters (Width, Height, PixelFormat).")
        source_main_layout.addWidget(self.load_refresh_button)

        main_layout.addWidget(source_group)
        main_layout.addStretch()
        self.setLayout(main_layout)

        self.source_type_combo.currentTextChanged.connect(self._on_source_type_changed)
        browse_image_button.clicked.connect(self._on_browse_image)
        self.load_refresh_button.clicked.connect(self._on_load_refresh_source)

        self._on_source_type_changed(self.source_type_combo.currentText())

    def _on_source_type_changed(self, source_type_text):
        logger.debug(f"Image source type changed to: {source_type_text}")
        if source_type_text == "Static Image":
            self.static_image_panel.setVisible(True)
            self.test_pattern_panel.setVisible(False)
        elif source_type_text == "Test Pattern":
            self.static_image_panel.setVisible(False)
            self.test_pattern_panel.setVisible(True)
        else:
            self.static_image_panel.setVisible(False)
            self.test_pattern_panel.setVisible(False)

    def _on_browse_image(self):
        logger.debug("Browse image button clicked.")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image File", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.tif);;All Files (*)"
        )
        if file_path:
            self.static_image_path_edit.setText(file_path)
            logger.info(f"Image file selected for static source: {file_path}")
        else:
            logger.debug("Browse image dialog cancelled.")

    def _on_load_refresh_source(self):
        logger.info("Load Source & Update Backend button clicked.")
        source_type = self.source_type_combo.currentText()

        if not self.simulator_backend:
            logger.error("SimulatorBackend not available for image source operations.")
            self.preview_label.setText("Error: Backend not ready.")
            return

        image_source_backend = self.simulator_backend.get_image_source()
        gvcp_module = self.simulator_backend.get_gvcp_module() # For register updates

        if not image_source_backend:
            logger.error("Backend image source (from simulator_backend) not available.")
            self.preview_label.setText("Error: Backend not ready.")
            return
        if not gvcp_module:
            logger.error("Backend GVCP service not available.")
            self.preview_label.setText("Error: Backend not ready.")
            return

        success = False
        new_width, new_height, new_pfnc = 0, 0, 0
        pil_mode_for_qimage = "L"

        if source_type == "Static Image":
            image_path = self.static_image_path_edit.text()
            if not image_path:
                logger.warning("No image path specified for static source.")
                self.preview_label.setText("No image path specified.")
                return

            if image_source_backend.load_image(image_path, "Mono8"): # Assuming Mono8 for now
                new_width = image_source_backend.width
                new_height = image_source_backend.height
                new_pfnc = image_source_backend.pixel_format_gvsp
                pil_mode_for_qimage = image_source_backend.pil_format
                success = True
                logger.info(f"Static image '{image_path}' loaded into backend image source.")
            else:
                logger.error(f"Failed to load static image '{image_path}' into backend.")
                self.preview_label.setText(f"Failed to load:\n{os.path.basename(image_path)}")

        elif source_type == "Test Pattern":
            pattern_type = self.test_pattern_combo.currentText()
            logger.info(f"Generating test pattern: {pattern_type}")
            tp_width, tp_height = 320, 240
            pil_img = None
            new_pfnc = PFNC_MONO8
            pil_mode_for_qimage = "L"

            if pattern_type == "Solid Color (Gray)":
                pil_img = Image.new("L", (tp_width, tp_height), color=128)
            elif pattern_type == "Grayscale Ramp (Horizontal)":
                pil_img = Image.new("L", (tp_width, tp_height))
                for x_coord in range(tp_width):
                    value = int((x_coord / tp_width) * 255)
                    for y_coord in range(tp_height):
                        pil_img.putpixel((x_coord, y_coord), value)

            if pil_img:
                pixel_bytes = pil_img.tobytes()
                if image_source_backend.load_image_from_data(pixel_bytes, tp_width, tp_height, pil_mode_for_qimage, new_pfnc):
                    new_width, new_height = tp_width, tp_height
                    success = True
                    logger.info(f"Test pattern '{pattern_type}' loaded into backend image source.")
                else:
                     logger.error(f"Failed to load test pattern '{pattern_type}' data into backend.")
            else:
                logger.error(f"Could not generate test pattern '{pattern_type}'.")

        if success:
            gvcp_module.camera_registers[0x0A00] = new_width
            gvcp_module.camera_registers[0x0A04] = new_height
            gvcp_module.camera_registers[0x0A08] = new_pfnc
            logger.info(f"Backend registers updated: W={new_width}, H={new_height}, PF=0x{new_pfnc:08X}")
            self._display_image_from_backend()
        else:
            if source_type == "Static Image" and self.static_image_path_edit.text():
                 self.preview_label.setText(f"Failed to load:\n{os.path.basename(self.static_image_path_edit.text())}")
            elif source_type == "Test Pattern":
                 self.preview_label.setText(f"Failed to generate\n or load pattern.")
            else:
                 self.preview_label.setText("Failed to load source.")


    def _display_image_from_backend(self):
        logger.debug("Attempting to display image from backend image source.")
        if not self.simulator_backend:
            logger.warning("Cannot display image: SimulatorBackend not available.")
            self.preview_label.setText("Error: Backend N/A")
            return

        image_source_backend = self.simulator_backend.get_image_source()
        if not image_source_backend:
            logger.warning("Cannot display image: Backend image source (from simulator_backend) not available.")
            self.preview_label.setText("Error: Image Source N/A")
            return

        frame_info = image_source_backend.get_frame()
        if frame_info and frame_info.get('pixel_data') and frame_info.get('width',0) > 0:
            width = frame_info['width']
            height = frame_info['height']
            pixel_data = frame_info['pixel_data']
            pil_format_str = image_source_backend.pil_format

            qimage_format = None
            if pil_format_str == "L":
                qimage_format = QImage.Format.Format_Grayscale8
            elif pil_format_str == "RGB":
                qimage_format = QImage.Format.Format_RGB888

            if qimage_format is None:
                logger.error(f"Unsupported PIL format '{pil_format_str}' for QImage conversion.")
                self.preview_label.setText(f"Preview Error:\nUnsupported format '{pil_format_str}'")
                return

            try:
                q_image = QImage(pixel_data, width, height, qimage_format)
                if q_image.isNull():
                    logger.error("Failed to create QImage from backend pixel data. QImage isNull.")
                    self.preview_label.setText("Preview Error:\nCould not create QImage.")
                    return

                pixmap = QPixmap.fromImage(q_image)
                self.preview_label.setPixmap(
                    pixmap.scaled(
                        self.preview_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
                logger.debug(f"Image displayed in preview: {width}x{height}, format {pil_format_str}")
            except Exception as e:
                logger.error(f"Error creating/displaying QPixmap: {e}", exc_info=True)
                self.preview_label.setText("Preview Error:\nException during display.")
        else:
            logger.info("No valid image data in backend to display.")
            self.preview_label.setText("No image loaded in backend.")

    def load_initial_preview(self):
        logger.debug("ImageSourcePanel: load_initial_preview called.")
        self._display_image_from_backend()
