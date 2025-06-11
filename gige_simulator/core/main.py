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
# Will be named "GigESim.Main" due to getLogger call below.
module_logger = logging.getLogger("GigESim.Main")

def run_simulator():
    """
    Main function to run the GigE Camera Simulator.
    Parses command-line arguments, sets up logging, initializes network components,
    and starts network listeners in separate threads.
    """
    # --- Argument Parsing ---
    # Sets up how users can configure the simulator from the command line.
    parser = argparse.ArgumentParser(description="GigE Camera Simulator")
    parser.add_argument(
        "--image_path", "-i",
        default="gige_simulator/sample_images/sample_image.png", # Default image if none specified
        help="Default image path for the simulator's image source."
    )
    parser.add_argument(
        "--discovery_port",
        default=3956, type=int, # Standard GigE Vision discovery port
        help="UDP port for GigE discovery."
    )
    parser.add_argument(
        "--gvcp_port",
        default=3957, type=int, # Standard GVCP port
        help="UDP port for GVCP commands."
    )
    parser.add_argument(
        "--log_level",
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help="Set the logging level for console output."
    )
    args = parser.parse_args() # Parse the command-line arguments

    # --- Logging Configuration ---
    # Sets up how log messages are displayed.
    numeric_log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_log_level, int): # Validate log level from arguments
        raise ValueError(f'Invalid log level: {args.log_level}')

    logging.basicConfig(
        level=numeric_log_level, # Set the global minimum log level
        format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s', # Log message format
        datefmt='%Y-%m-%d %H:%M:%S' # Timestamp format
    )

    module_logger.info(f"Starting GigE Camera Simulator with configuration: {args}")

    # --- Dynamic Imports & Configuration ---
    # Import network modules *after* logging is configured so they inherit the setup.
    # Also ensures sys.path modification (if any) has taken effect.
    from gige_simulator.network import discovery, gvcp

    # Apply command-line arguments to the network modules
    module_logger.info(f"Setting discovery port to {args.discovery_port}")
    discovery.set_discovery_port(args.discovery_port)

    module_logger.info(f"Setting GVCP port to {args.gvcp_port}")
    gvcp.set_gvcp_port(args.gvcp_port)

    module_logger.info(f"Initializing GVCP memory map with image: {args.image_path}")
    # This call is critical: it loads the GenICam XML, default image,
    # and initializes the image_source_global and gvsp_streamer_global instances within gvcp.py.
    gvcp.initialize_memory_map(args.image_path)

    # --- Threading Setup for Network Listeners ---
    # Each listener runs in its own thread so they can operate concurrently.
    # `daemon=True` means these threads will exit when the main program exits.

    module_logger.info(f"Starting Discovery listener on port {args.discovery_port} in a new thread.")
    discovery_thread = threading.Thread(
        target=discovery.start_discovery_listener,
        name="DiscoveryThread", # Assign a name for easier log identification
        daemon=True
    )

    module_logger.info(f"Starting GVCP listener on port {args.gvcp_port} in a new thread.")
    gvcp_thread = threading.Thread(
        target=gvcp.start_gvcp_listener,
        name="GVCPThread",
        daemon=True
    )

    # Start the listener threads
    discovery_thread.start()
    gvcp_thread.start()

    module_logger.info("GigE Camera Simulator is running. Press Ctrl+C to stop.")

    # --- Main Loop & Shutdown ---
    # Keep the main thread alive to handle termination (e.g., Ctrl+C).
    try:
        while True:
            # Check if network listener threads are still alive.
            # If a critical thread dies, the simulator might be in an unusable state.
            if not discovery_thread.is_alive():
                module_logger.error("Discovery thread has terminated unexpectedly. Shutting down.")
                break
            if not gvcp_thread.is_alive():
                module_logger.error("GVCP thread has terminated unexpectedly. Shutting down.")
                break
            time.sleep(1) # Keep main thread responsive, sleep for 1 second
    except KeyboardInterrupt: # Handle Ctrl+C for graceful shutdown
        module_logger.info("Ctrl+C received. Shutting down simulator...")
    finally:
        # Perform any cleanup here if necessary.
        # Daemon threads will be terminated automatically when the main program exits.
        module_logger.info("Simulator shutdown sequence complete.")

# --- Script Entry Point ---
# This ensures run_simulator() is called only when this script is executed directly
# (e.g., `python gige_simulator/core/main.py`), not when it's imported as a module.
if __name__ == "__main__":
    run_simulator()
```
