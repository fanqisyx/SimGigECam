# GigE Camera Simulator

This project is a basic simulator for a GigE Vision compliant camera. It aims to simulate the discovery, control (GVCP), and streaming (GVSP) protocols.

## How it Works

The simulator operates using three main components:

1.  **Discovery (network/discovery.py)**:
    *   Listens for broadcast messages from GigE Vision clients on a specific UDP port (default 3956).
    *   When a discovery request is received, it responds with a DISCOVERY_ACK packet containing basic camera information (IP address, MAC, model name, manufacturer, etc.) and, crucially, the port on which the GVCP service is running.

2.  **GVCP - GigE Vision Control Protocol (network/gvcp.py)**:
    *   Listens for commands on a specific UDP port (default 3957), as advertised in the discovery ACK.
    *   Handles register read (`READREG_CMD`) and write (`WRITEREG_CMD`) operations.
    *   **GenICam XML (genicam/genicam_model.xml)**: GVCP provides access to a GenICam XML file. This XML file describes all the features of the camera (e.g., width, height, pixel format, acquisition control) and their corresponding register addresses. Clients parse this XML to understand how to control the camera. The simulator serves this XML file when requested via specific GVCP bootstrap registers.
    *   Manages camera state, such as current image dimensions, pixel format, acquisition mode, and GVSP stream destination.

3.  **GVSP - GigE Vision Streaming Protocol (network/gvsp_sender.py)**:
    *   When image acquisition is started via a GVCP command:
    *   GVSP prepares to send image data to a client-specified IP address and port (configured via GVCP registers).
    *   It (currently) sends a single frame composed of:
        *   A **Leader Packet**: Contains metadata about the image (e.g., size, pixel format, timestamp).
        *   **Payload Packets**: Multiple packets containing the actual pixel data, respecting a maximum payload size.
        *   A **Trailer Packet**: Marks the end of the frame's data.
    *   The current implementation uses a simplified GVSP packet structure.

## Features

*   **GigE Discovery**: Responds to discovery broadcasts.
*   **GVCP Implementation**: Basic register read/write, GenICam XML serving, image loading control, acquisition control, GVSP stream destination configuration.
*   **GVSP Sender**: Sends a single image frame (Leader, Payloads, Trailer) with a simplified packet structure.
*   **GenICam XML**: Includes `genicam/genicam_model.xml`.
*   **Configurable**: Command-line arguments for ports, default image, log level.
*   **Logging**: Structured logging across modules.
*   **Image Source**: Loads images using Pillow (currently Mono8 focused).
*   **Threading**: Discovery and GVCP listeners run in separate threads.

## Running the Simulator

The simulator can be run as a Python module from the project's root directory:

```bash
python -m gige_simulator [options]
```

**Options:**

*   `--image_path` / `-i`: Path to the default image file (default: `gige_simulator/sample_images/sample_image.png`).
*   `--discovery_port`: UDP port for GigE discovery (default: 3956).
*   `--gvcp_port`: UDP port for GVCP commands (default: 3957).
*   `--log_level`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO).

**Examples:**

*   Run with default settings:
    ```bash
    python -m gige_simulator
    ```
*   Specify a different image and run with debug logging:
    ```bash
    python -m gige_simulator -i path/to/your/image.jpeg --log_level DEBUG
    ```
*   Change discovery and GVCP ports:
    ```bash
    python -m gige_simulator --discovery_port 3000 --gvcp_port 3001
    ```

## Project Structure

*   `gige_simulator/`
    *   `core/`: Main application logic and coordination.
        *   `main.py`: Entry point, argument parsing, logging setup, thread management.
    *   `network/`: GVCP, GVSP, and discovery protocol implementations.
        *   `discovery.py`: Handles GigE Vision discovery broadcasts.
        *   `gvcp.py`: Manages GVCP commands and register access.
        *   `gvsp_sender.py`: Constructs and sends GVSP image stream packets.
    *   `image_source/`: Image loading and management.
        *   `image_loader.py`: `StaticImageSource` class for loading images with Pillow.
    *   `genicam/`: GenICam XML device description file.
        *   `genicam_model.xml`: Describes camera features and register map.
    *   `sample_images/`: Contains sample images for testing.
    *   `tests/`: (Placeholder for unit tests).
    *   `__init__.py`: Marks directories as Python packages.
    *   `__main__.py`: Enables running as `python -m gige_simulator`.
    *   `README.md`: This file.
    *   `requirements.txt`: Python dependencies.

## Key Files

*   `gige_simulator/core/main.py`: Main application entry point.
*   `gige_simulator/network/discovery.py`: Discovery protocol handler.
*   `gige_simulator/network/gvcp.py`: GVCP command and register logic.
*   `gige_simulator/network/gvsp_sender.py`: GVSP packet streaming logic.
*   `gige_simulator/genicam/genicam_model.xml`: The camera's feature description file.
*   `gige_simulator/image_source/image_loader.py`: Image loading functionality.

## Current Limitations / Future Work

*   **Continuous Streaming**: Currently, the simulator sends only one frame per `AcquisitionStart` command. Continuous streaming at a configurable frame rate requires a dedicated streaming thread for GVSP.
*   **GVSP Packet Structure**: The GVSP packet structure is simplified. Full compliance with GigE Vision specification headers (e.g., detailed status, block ID format, packet ID format) and features (e.g., packet resends) is needed.
*   **GenICam Feature Completeness**: The GenICam XML is basic. More features (e.g., Float, Boolean registers, more complex Enumerations, advanced Commands like chunk data) and standard feature naming conventions should be implemented.
*   **Pixel Format Handling**: Primarily focused on Mono8. Support for other formats (e.g., RGB8, Bayer types) needs to be expanded in `ImageLoader`, GVCP register handling, and GVSP packet formatting.
*   **Register Validation**: More robust validation for register read/write operations against GenICam definitions (min, max, increment, access mode enforcement).
*   **Error Handling**: More comprehensive error handling and reporting via GVCP status codes for various failure scenarios.
*   **Configuration Management**: Device IP, MAC, default image path, etc., are currently hardcoded or simple defaults within the code. A more robust configuration mechanism (e.g., external config file) would be beneficial for `DEVICE_IP_ADDRESS`, `DEVICE_MAC_ADDRESS` etc. in `discovery.py`.
*   **Unit Tests**: Needs comprehensive unit tests for all modules.
*   **READMEM/WRITEMEM Commands**: Full implementation of `READMEM_CMD` and `WRITEMEM_CMD` for efficient access to large data blocks (like the full XML file, string registers, or image buffers if exposed via memory reads).
*   **Event Handling (GVCP EVENT_CMD, EVENTDATA_CMD)**: Not yet implemented. This is important for asynchronous camera notifications.
*   **Multiple Network Interfaces**: The simulator currently assumes a single network interface.
*   **GVCP Heartbeat (Keep-Alive)**: The `SCPT` (Standard Control Protocol Timeout) register is defined, but actual heartbeat handling (sending `HEARTBEAT_CMD` or responding to client heartbeats to maintain control channel) is not implemented.

## Dependencies
* Pillow

Install dependencies using:
```bash
pip install -r requirements.txt
```
