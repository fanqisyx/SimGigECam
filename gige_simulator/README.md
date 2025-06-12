# GigE Camera Simulator

This project is a basic simulator for a GigE Vision compliant camera. It aims to simulate the discovery, control (GVCP), and streaming (GVSP) protocols, and includes a basic PyQt6 GUI for interaction.

## How it Works

The simulator operates using several key components:

1.  **Core Backend (`core/simulator_backend.py`)**:
    *   Manages the lifecycle of network services (Discovery, GVCP).
    *   Handles shared resources like the image source and GVSP streamer instance.
    *   Provides an interface for frontends (CLI/GUI) to interact with the simulation.

2.  **Discovery (`network/discovery.py`)**:
    *   Listens for broadcast messages from GigE Vision clients on a specific UDP port.
    *   Responds with a DISCOVERY_ACK packet containing basic camera information (IP, MAC, model, manufacturer, etc.) and the GVCP service port.

3.  **GVCP - GigE Vision Control Protocol (`network/gvcp.py`)**:
    *   Listens for commands on a specific UDP port, as advertised in the discovery ACK.
    *   Handles register read (`READREG_CMD`) and write (`WRITEREG_CMD`) operations.
    *   **GenICam XML (`genicam/genicam_model.xml`)**: GVCP provides access to a GenICam XML file. This XML describes camera features (e.g., width, height, pixel format, acquisition control) and their register addresses. Clients parse this XML to control the camera.
    *   Manages camera state (registers, current image, GVSP stream destination).

4.  **GVSP - GigE Vision Streaming Protocol (`network/gvsp_sender.py`)**:
    *   When image acquisition is started (via GVCP or GUI), GVSP sends image data to a client-specified IP/port.
    *   Currently sends a single frame composed of Leader, Payload, and Trailer packets using a simplified structure.

5.  **Image Source (`image_source/image_loader.py`)**:
    *   Loads images from files (using Pillow) or generates test patterns.
    *   Provides pixel data to the GVSP component.

6.  **User Interfaces (CLI and GUI)**:
    *   **CLI (`core/main.py`)**: Allows starting the backend with command-line arguments.
    *   **GUI (`gui_main.py` and `gui/` panels)**: Provides a graphical interface to control the simulator.

## Features

*   **GigE Discovery**: Responds to discovery broadcasts.
*   **GVCP Implementation**: Basic register read/write, GenICam XML serving, image loading control, acquisition control, GVSP stream destination configuration.
*   **GVSP Sender**: Sends a single image frame (Leader, Payloads, Trailer) with a simplified packet structure.
*   **GenICam XML**: Includes `genicam/genicam_model.xml` describing camera features.
*   **Configurable**:
    *   **CLI**: Command-line arguments for ports, default image, log level.
    *   **GUI**: Allows runtime modification of some parameters (e.g., image source, GVSP client).
*   **Logging**: Structured logging across modules, viewable in the GUI or console.
*   **Image Source**: Supports loading static images (PNG, JPG, BMP, TIFF via Pillow) and generating basic test patterns (solid color, grayscale ramp).
*   **Threading**: Discovery and GVCP listeners run in separate daemon threads managed by the `SimulatorBackend`.
*   **Graphical User Interface (GUI)**:
    *   **Main Window**: Dockable panel interface using PyQt6.
    *   **Main Control Panel**: Starting/stopping image acquisition for the default simulated camera, managing a list of (currently conceptual) virtual cameras.
    *   **Camera Configuration Panel**: Viewing/editing camera parameters (Width, Height, PixelFormat), trigger mode (UI placeholder), GVSP client IP/Port. Supports saving/loading panel configuration to/from JSON. Allows applying settings to the backend simulator.
    *   **Image Preview & Source Management Panel**: Displays a preview of the loaded static image or generated test pattern. Allows selecting the image source type, browsing for static files, or choosing a test pattern. Loading a new source updates the backend.
    *   **Network Status & Log Window Panel**: Displays (currently placeholder) network statistics. Provides a real-time log display capturing messages from all simulator components, with level filtering and export capability.
    *   **Toolbar**: Quick access to common functions (most are placeholders). Includes a (non-functional) theme toggle.

## Running the Simulator

There are two ways to run the simulator:

### 1. CLI Mode (Backend Services Only)

This mode runs the discovery and GVCP listeners without a graphical interface.
It can be run as a Python module from the project's root directory:

```bash
python -m gige_simulator [options]
```
Alternatively, you can run the main core script directly:
```bash
python gige_simulator/core/main.py [options]
```

**CLI Options:**

*   `--image_path` / `-i`: Path to the default image file (default: `gige_simulator/sample_images/sample_image.png`).
*   `--discovery_port`: UDP port for GigE discovery (default: 3956).
*   `--gvcp_port`: UDP port for GVCP commands (default: 3957).
*   `--log_level`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

**CLI Examples:**

*   Run with default settings:
    ```bash
    python -m gige_simulator
    ```
*   Specify a different image and run with debug logging:
    ```bash
    python -m gige_simulator -i path/to/your/image.jpeg --log_level DEBUG
    ```

### 2. GUI Mode

This mode launches the PyQt6 graphical user interface.

```bash
python gige_simulator/gui_main.py
```

**GUI Notes:**

*   The GUI internally starts a `SimulatorBackend` instance using a default image path.
*   Running the GUI requires a desktop environment with a display server (e.g., X11 or Wayland) and the necessary Qt platform plugins. If you encounter errors like "Could not load the Qt platform plugin 'xcb'", you may need to install additional system libraries (see "Development Notes").
*   Logging from all simulator components will be directed to the "Network & Logs" panel in the GUI.

## Project Structure

*   `gige_simulator/`
    *   `core/`: Main application logic and backend.
        *   `main.py`: CLI entry point.
        *   `simulator_backend.py`: Central class for managing simulation services.
    *   `gui/`: PyQt6 GUI components.
        *   `gui_main.py`: Main window (`MainWindow`) for the GUI application.
        *   `main_control_panel.py`: Panel for simulation and camera list management.
        *   `camera_config_panel.py`: Panel for camera parameter configuration.
        *   `image_source_panel.py`: Panel for image source selection and preview.
        *   `network_log_panel.py`: Panel for displaying logs and network status.
    *   `network/`: GVCP, GVSP, and discovery protocol implementations.
        *   `discovery.py`: Handles GigE Vision discovery broadcasts.
        *   `gvcp.py`: Manages GVCP commands and register access.
        *   `gvsp_sender.py`: Constructs and sends GVSP image stream packets.
    *   `image_source/`: Image loading and management.
        *   `image_loader.py`: `StaticImageSource` class.
    *   `genicam/`: GenICam XML device description file.
        *   `genicam_model.xml`: Describes camera features and register map.
    *   `sample_images/`: Contains sample images for testing.
    *   `tests/`: (Placeholder for unit tests).
    *   `__init__.py`: Marks directories as Python packages.
    *   `__main__.py`: Enables running CLI as `python -m gige_simulator`.
    *   `README.md`: This file.
    *   `requirements.txt`: Python dependencies.

## Key Files

*   `gige_simulator/core/main.py`: CLI application entry point.
*   `gige_simulator/gui_main.py`: GUI application entry point.
*   `gige_simulator/core/simulator_backend.py`: Core backend logic.
*   `gige_simulator/network/gvcp.py`: GVCP command and register logic, also initializes image source and GVSP streamer.
*   `gige_simulator/genicam/genicam_model.xml`: The camera's feature description file.

## Dependencies

*   **Pillow**: For image file loading and manipulation.
*   **PyQt6**: For the graphical user interface.
*   **PyQt6-sip**: Required by PyQt6.
*   **qtpy**: For Qt API abstraction (though not heavily used yet, good for future flexibility).

Install dependencies using:
```bash
pip install -r requirements.txt
```

## Current Limitations / Future Work

*   **Continuous Streaming**: Currently, the simulator sends only one frame per `AcquisitionStart` command. Continuous streaming at a configurable frame rate requires a dedicated streaming thread for GVSP.
*   **GVSP Packet Structure**: The GVSP packet structure is simplified. Full compliance with GigE Vision specification headers (e.g., detailed status, block ID format, packet ID format) and features (e.g., packet resends) is needed.
*   **Multi-Camera Backend**: The GUI allows adding multiple cameras to a list, but this is purely a UI concept for now. The backend `SimulatorBackend` only manages a single instance of the discovery/GVCP/GVSP chain. True multi-camera simulation would require significant backend refactoring.
*   **GenICam Feature Completeness**: The GenICam XML is basic. More features (e.g., Float, Boolean registers, more complex Enumerations, advanced Commands like chunk data) and standard feature naming conventions should be implemented.
*   **Pixel Format Handling**: Primarily focused on Mono8 for loading and generation. Support for other formats (e.g., RGB8, Bayer types) needs to be expanded in `ImageLoader`, `CameraConfigPanel`, GVCP register handling, and GVSP packet formatting.
*   **Register Validation**: More robust validation for register read/write operations against GenICam definitions (min, max, increment, access mode enforcement).
*   **Error Handling**: More comprehensive error handling and reporting via GVCP status codes for various failure scenarios.
*   **Configuration Management**: Device constants (IP, MAC in `discovery.py`) are hardcoded. A more robust configuration mechanism (e.g., external config file or per-instance GUI settings) is needed.
*   **Unit Tests**: Needs comprehensive unit tests for all modules.
*   **READMEM/WRITEMEM Commands**: Full implementation of `READMEM_CMD` and `WRITEMEM_CMD` for efficient access to large data blocks.
*   **Event Handling (GVCP EVENT_CMD, EVENTDATA_CMD)**: Not yet implemented.
*   **GVCP Heartbeat (Keep-Alive)**: The `SCPT` register is defined, but actual heartbeat handling is not implemented.
*   **GUI Theme Toggle**: The "Toggle Theme" toolbar action is a placeholder and does not change the visual style yet.
*   **Network Status Indicators**: The network status labels in the GUI are placeholders and do not display real-time data from the backend.

## Development Notes
The GUI is developed using PyQt6. During this phase of development, visual testing of the GUI was hindered by limitations in the execution environment (lack of a suitable display server for Qt platform plugins like XCB). The code structure for the GUI panels and their basic interactions is in place, but thorough visual testing and refinement should be performed in a standard desktop environment. For example, to run Qt applications in a headless Linux environment, tools like Xvfb (X virtual framebuffer) might be necessary, or ensuring all `libxcb` and related X11 dependencies are fully installed.
```
