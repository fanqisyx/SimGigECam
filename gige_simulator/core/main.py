import argparse
import logging
import threading
import time
import sys
import os

# --- Path Setup ---
# This ensures that when core/main.py is run directly (e.g., for testing or development),
# Python can find other modules within the gige_simulator package.
# If the script is run as part of a module (`python -m gige_simulator`),
# Python's import system typically handles this, but this makes direct execution more robust.
if __name__ == '__main__': # Only adjust path if this script is the entry point
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # Assuming main.py is in gige_simulator/core/, then PROJECT_ROOT is gige_simulator/
    PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT) # Add project root to the start of Python's module search path

# Logger for this module (main application logic)
# Will be named "GigESim.CliMain" due to getLogger call below for clarity.
module_logger = logging.getLogger("GigESim.CliMain")
from .simulator_backend import SimulatorBackend # Import the backend

def run_simulator():
    """
    Main function to run the GigE Camera Simulator.
    Parses command-line arguments, sets up logging, initializes network components,
    and starts network listeners in separate threads.
    """
    """
    Main function to run the GigE Camera Simulator (CLI version).
    Parses arguments, sets up logging, initializes and starts the SimulatorBackend.
    """
    parser = argparse.ArgumentParser(description="GigE Camera Simulator (CLI)")
    parser.add_argument(
        "--image_path", "-i",
        default="gige_simulator/sample_images/sample_image.png",
        help="Default image path for the simulator's image source."
    )
    parser.add_argument(
        "--discovery_port",
        default=3956, type=int,
        help="UDP port for GigE discovery."
    )
    parser.add_argument(
        "--gvcp_port",
        default=3957, type=int,
        help="UDP port for GVCP commands."
    )
    parser.add_argument(
        "--log_level",
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level for console output."
    )
    args = parser.parse_args()

    numeric_log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Configure root logger for CLI mode.
    # This will be inherited by all module loggers unless they are individually configured.
    logging.basicConfig(
        level=numeric_log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    module_logger.info(f"Starting GigE Camera Simulator (CLI) with configuration: {args}")

    # Create and start the backend
    backend = None # Define backend here to ensure it's in scope for finally block
    try:
        backend = SimulatorBackend(
            default_image_path=args.image_path,
            discovery_port=args.discovery_port,
            gvcp_port=args.gvcp_port
        )
        backend.start_servers()
        # module_logger.info("Simulator backend servers started.") # Backend logs this already
        module_logger.info("GigE Camera Simulator (CLI) is running. Press Ctrl+C to stop.")

        while True:
            if not backend.is_running:
                module_logger.info("Backend is no longer running. Shutting down CLI.")
                break
            # Check thread health more carefully
            if backend.discovery_thread and not backend.discovery_thread.is_alive() and backend.is_running:
                module_logger.error("Discovery thread has terminated unexpectedly while backend was expected to run. Shutting down CLI.")
                backend.stop_servers()
                break
            if backend.gvcp_thread and not backend.gvcp_thread.is_alive() and backend.is_running:
                module_logger.error("GVCP thread has terminated unexpectedly while backend was expected to run. Shutting down CLI.")
                backend.stop_servers()
                break
            time.sleep(1)
    except ValueError as ve:
        module_logger.critical(f"Configuration error: {ve}")
    except KeyboardInterrupt:
        module_logger.info("Ctrl+C received. Shutting down simulator (CLI)...")
    except Exception as e:
        module_logger.critical(f"An unexpected error occurred in CLI main: {e}", exc_info=True)
    finally:
        if backend and backend.is_running: # Ensure backend exists and was running
            backend.stop_servers()
        module_logger.info("Simulator (CLI) shutdown sequence complete.")

# --- Script Entry Point ---
# This ensures run_simulator() is called only when this script is executed directly
# (e.g., `python gige_simulator/core/main.py`), not when it's imported as a module.
if __name__ == "__main__":
    run_simulator()
