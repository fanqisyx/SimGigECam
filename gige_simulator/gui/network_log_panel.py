import logging
import json # Though not used in this snippet, good for consistency if planned for other panels
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QBrush, QFont, QTextCursor

# --- Custom Log Handler for Qt ---
class QtLogHandler(logging.Handler):
    """
    A custom logging handler that emits a Qt signal for each log record.
    """
    log_received = pyqtSignal(str, str) # Signal: (formatted_message, levelname)

    def __init__(self, parent=None):
        super().__init__()
        # Parent is not strictly needed for a logging.Handler but can be useful
        # if the handler needs to interact with a QObject parent.

    def emit(self, record):
        """
        Formats the log record and emits the log_received signal.
        """
        try:
            msg = self.format(record)
            self.log_received.emit(msg, record.levelname)
        except Exception:
            self.handleError(record) # Default error handling

logger = logging.getLogger(__name__) # Logger for this panel's own messages

class NetworkLogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._setup_logging()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Status Display Group ---
        status_group = QGroupBox("Network Status (Simulated)")
        form_layout = QFormLayout(status_group)

        self.bandwidth_label = QLabel("N/A")
        self.packets_sent_label = QLabel("0")
        self.packets_lost_label = QLabel("0") # Placeholder
        self.client_ip_label = QLabel("N/A")  # Placeholder, could be updated from GVCP

        form_layout.addRow("Current Bandwidth:", self.bandwidth_label)
        form_layout.addRow("Packets Sent (GVSP):", self.packets_sent_label)
        form_layout.addRow("Packets Lost (GVSP):", self.packets_lost_label)
        form_layout.addRow("Streaming Client IP:", self.client_ip_label)
        main_layout.addWidget(status_group)

        # --- Log Control Group ---
        log_control_group = QGroupBox("Log Controls")
        log_control_layout = QHBoxLayout(log_control_group)

        log_control_layout.addWidget(QLabel("Display Level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.log_level_combo.setCurrentText("INFO") # Default display level
        self.log_level_combo.setToolTip("Select the minimum log level to display.")
        log_control_layout.addWidget(self.log_level_combo)
        log_control_layout.addStretch()

        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.setToolTip("Clear all messages from the log display.")
        log_control_layout.addWidget(self.clear_log_button)

        self.export_log_button = QPushButton("Export Log...")
        self.export_log_button.setToolTip("Save the displayed log messages to a text file.")
        log_control_layout.addWidget(self.export_log_button)
        main_layout.addWidget(log_control_group)

        # --- Log Display ---
        self.log_display_text = QTextEdit()
        self.log_display_text.setReadOnly(True)
        self.log_display_text.setFont(QFont("Monospace", 9)) # Monospaced font for logs
        self.log_display_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) # Optional: disable line wrap
        main_layout.addWidget(self.log_display_text)

        self.setLayout(main_layout)

        # Connect signals
        self.clear_log_button.clicked.connect(self.log_display_text.clear)
        self.export_log_button.clicked.connect(self._on_export_log)
        self.log_level_combo.currentTextChanged.connect(self._on_log_level_changed)

    def _setup_logging(self):
        """Configures the QtLogHandler to capture logs for the GUI."""
        self.log_handler = QtLogHandler(self)
        # Standard log format, matches the console output from core.main
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.log_handler.setFormatter(formatter)

        # Add this handler to the root logger of the 'gige_simulator' package.
        # This allows capturing logs from all modules within gige_simulator.
        package_root_logger = logging.getLogger('gige_simulator')
        package_root_logger.addHandler(self.log_handler)
        # The level of package_root_logger should be set in gui_main.py (e.g., to DEBUG)
        # so that this handler receives all messages it might need to filter.

        self.log_handler.log_received.connect(self._append_log_message)

        # Set initial filter level for the handler based on ComboBox
        self._on_log_level_changed(self.log_level_combo.currentText())
        logger.info("NetworkLogPanel logging initialized and handler attached to 'gige_simulator' logger.")

    def _append_log_message(self, message, levelname):
        """Appends a log message to the QTextEdit with appropriate color."""
        # The handler's level already filters messages, so we just display what we receive.

        cursor = self.log_display_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End) # Move cursor to end before inserting

        log_format = QTextCharFormat()

        # Define color map for log levels
        color_map = {
            "DEBUG": QColor(Qt.GlobalColor.gray),
            "INFO": QColor(Qt.GlobalColor.black), # Or use default text color of the widget
            "WARNING": QColor(Qt.GlobalColor.darkYellow), # Using darkYellow for better readability on light themes
            "ERROR": QColor(Qt.GlobalColor.red),
            "CRITICAL": QColor(Qt.GlobalColor.darkRed)
        }
        text_color = color_map.get(levelname.upper(), QColor(Qt.GlobalColor.black))
        log_format.setForeground(QBrush(text_color))

        # Optionally make critical/error messages bold
        if levelname.upper() in ["CRITICAL", "ERROR"]:
            log_format.setFontWeight(QFont.Weight.Bold)
        else:
            log_format.setFontWeight(QFont.Weight.Normal)

        cursor.insertText(message + '\n', log_format) # Ensure newline if formatter doesn't add it
        self.log_display_text.ensureCursorVisible() # Auto-scroll to the latest message

    def _on_export_log(self):
        """Saves the content of the log display to a text file."""
        logger.info("Export Log button clicked.")
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Log File", "", "Text Files (*.txt);;All Files (*)")
        if not file_path:
            logger.debug("Export log dialog cancelled.")
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_display_text.toPlainText())
            logger.info(f"Log exported successfully to {file_path}")
            QMessageBox.information(self, "Log Exported", f"Log saved to:\n{file_path}")
        except Exception as e:
            logger.error(f"Error exporting log to {file_path}: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Error", f"Failed to save log:\n{e}")

    def _on_log_level_changed(self, level_string):
        """
        Sets the filter level on the QtLogHandler based on ComboBox selection.
        """
        level_int = logging.getLevelName(level_string.upper())
        if isinstance(level_int, int) and hasattr(self, 'log_handler'): # Check if log_handler exists
            self.log_handler.setLevel(level_int)
            logger.info(f"Log display filter level set to: {level_string} ({level_int})")
        elif not hasattr(self, 'log_handler'):
             logger.warning(f"Log level changed to {level_string}, but log_handler not yet initialized.")


    # --- Public methods to update status labels (called from outside) ---
    def update_network_stats(self, bandwidth="N/A", packets_sent="0", packets_lost="0"):
        self.bandwidth_label.setText(str(bandwidth))
        self.packets_sent_label.setText(str(packets_sent))
        self.packets_lost_label.setText(str(packets_lost))
        logger.debug(f"Network stats UI updated: BW={bandwidth}, Sent={packets_sent}, Lost={packets_lost}")

    def update_client_ip(self, client_ip_str="N/A"):
        self.client_ip_label.setText(str(client_ip_str))
        logger.debug(f"Client IP UI updated: {client_ip_str}")
