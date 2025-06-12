import threading
import logging
import time
import socket # For IP address conversion
import struct # For IP address conversion

# Import simulator modules
from gige_simulator.network import discovery as discovery_module
from gige_simulator.network import gvcp as gvcp_module
# image_loader_module is used by gvcp_module, not directly here typically
# from gige_simulator.image_source import image_loader as image_loader_module
# gvsp_sender_module is used by gvcp_module (via gvsp_streamer_global)
# from gige_simulator.network import gvsp_sender as gvsp_sender_module

logger = logging.getLogger(__name__)

class SimulatorBackend:
    def __init__(self, default_image_path, discovery_port=3956, gvcp_port=3957):
        logger.info(
            f"Initializing SimulatorBackend with image: '{default_image_path}', "
            f"Discovery: {discovery_port}, GVCP: {gvcp_port}"
        )
        self.default_image_path = default_image_path
        self.discovery_port = discovery_port
        self.gvcp_port = gvcp_port

        self.discovery_thread = None
        self.gvcp_thread = None
        self.is_running = False

        # Configure ports in respective modules
        discovery_module.set_discovery_port(self.discovery_port)
        gvcp_module.set_gvcp_port(self.gvcp_port)

        # Initialize GVCP memory map, which also sets up
        # gvcp_module.image_source_global and gvcp_module.gvsp_streamer_global
        gvcp_module.initialize_memory_map(self.default_image_path) # This is a critical call.

        # Get references to the globally managed components that were initialized within gvcp_module.
        # This coupling is due to gvcp.py historically being the main initializer.
        # Future refactoring might move ownership of these instances more directly into SimulatorBackend.
        self.image_source = gvcp_module.image_source_global
        self.gvsp_streamer = gvcp_module.gvsp_streamer_global

        if not self.image_source:
            logger.error("Image source was not initialized correctly in GVCP module.")
        if not self.gvsp_streamer:
            logger.error("GVSP streamer was not initialized correctly in GVCP module.")

        logger.info("SimulatorBackend initialized.")

    def start_servers(self):
        if self.is_running:
            logger.info("Simulator backend servers are already running.")
            return

        logger.info(f"Starting Discovery listener on port {self.discovery_port} in a new thread.")
        self.discovery_thread = threading.Thread(
            target=discovery_module.start_discovery_listener,
            name="DiscoveryThreadBackend",
            daemon=True
        )

        logger.info(f"Starting GVCP listener on port {self.gvcp_port} in a new thread.")
        self.gvcp_thread = threading.Thread(
            target=gvcp_module.start_gvcp_listener,
            name="GVCPThreadBackend",
            daemon=True
        )

        self.discovery_thread.start()
        self.gvcp_thread.start()
        self.is_running = True
        logger.info("Simulator backend servers started.")

    def stop_servers(self):
        if not self.is_running:
            logger.info("Simulator backend servers are not running.")
            return

        # For daemon threads, explicit stopping from outside is tricky without
        # internal flags in their target loops. Setting self.is_running might be
        # checked by those loops if they were designed for it.
        # For now, this mainly signifies intent to stop.
        self.is_running = False
        logger.info("Simulator backend servers stopping (threads are daemons and will exit with main program).")
        # If GVCP/Discovery loops were checking a flag:
        # if hasattr(gvcp_module, 'stop_listener_flag'): gvcp_module.stop_listener_flag = True
        # if hasattr(discovery_module, 'stop_listener_flag'): discovery_module.stop_listener_flag = True


    def get_gvcp_module(self):
        """Provides access to the GVCP module for direct register/memory map interaction if needed."""
        return gvcp_module

    def get_image_source(self):
        """Provides access to the shared image source instance."""
        return self.image_source

    def _ip_str_to_int(self, ip_str):
        """Converts an IPv4 string to its integer representation."""
        try:
            return struct.unpack("!I", socket.inet_aton(ip_str))[0]
        except socket.error:
            logger.warning(f"Invalid IP string for conversion to int: {ip_str}. Returning 0.")
            return 0
        except Exception as e:
            logger.error(f"Error converting IP string '{ip_str}' to int: {e}")
            return 0

    def _ip_int_to_str(self, ip_int):
        """Converts an integer to an IPv4 string."""
        try:
            return socket.inet_ntoa(struct.pack('!I', ip_int))
        except (struct.error, socket.error) as e:
            logger.warning(f"Invalid IP integer for conversion to string: {ip_int}. Error: {e}. Returning '0.0.0.0'.")
            return "0.0.0.0"


    def apply_camera_config(self, config_dict):
        """Applies configuration changes from the GUI to the backend."""
        logger.info(f"Applying new camera config from GUI: {config_dict}")

        # Update camera_registers directly.
        # Note: This is a simplified direct update. A more robust system might involve
        # queueing these as WRITEREG commands or calling specific setter functions
        # in gvcp_module if register writes have side-effects not handled by direct dict update,
        # or if specific setter functions in gvcp_module should be preferred.

        if 'width' in config_dict:
            # Address 0x0A00 is typically 'Width'
            gvcp_module.camera_registers[0x0A00] = int(config_dict['width'])
            logger.debug(f"Backend Width (0x0A00) updated to: {config_dict['width']}")
        if 'height' in config_dict:
            # Address 0x0A04 is typically 'Height'
            gvcp_module.camera_registers[0x0A04] = int(config_dict['height'])
            logger.debug(f"Backend Height (0x0A04) updated to: {config_dict['height']}")
        if 'pixel_format_pfnc' in config_dict:
            # Address 0x0A08 is typically 'PixelFormat'
            gvcp_module.camera_registers[0x0A08] = int(config_dict['pixel_format_pfnc'])
            logger.debug(f"Backend PixelFormat (0x0A08) updated to: 0x{int(config_dict['pixel_format_pfnc']):08X}")

        # Update GevSCPHostAddress (0x0D1C) and GevSCPHostPort (0x0D18) for GVSP streaming
        client_ip_str = config_dict.get('client_ip', "0.0.0.0")
        client_port_int = int(config_dict.get('client_port', 0))

        ip_int_for_reg = self._ip_str_to_int(client_ip_str)

        gvcp_module.camera_registers[0x0D1C] = ip_int_for_reg  # GevSCPHostAddress
        gvcp_module.camera_registers[0x0D18] = client_port_int # GevSCPHostPort
        logger.debug(f"Backend GevSCPHostAddress (0x0D1C) updated to: 0x{ip_int_for_reg:08X} ({client_ip_str})")
        logger.debug(f"Backend GevSCPHostPort (0x0D18) updated to: {client_port_int}")

        if self.gvsp_streamer:
            self.gvsp_streamer.update_client_destination(ip_int_for_reg, client_port_int)
        else:
            logger.error("Cannot update GVSP streamer destination, streamer not initialized.")

        # DeviceModelName (Camera Name) update
        if 'device_model_name' in config_dict:
            new_name_str = config_dict['device_model_name']
            logger.info(f"Attempting to update DeviceModelName to: '{new_name_str}'")
            name_bytes = new_name_str.encode('utf-8')
            # Truncate if longer than 31 bytes (to allow for null terminator), then pad to 32 bytes.
            padded_name_bytes = name_bytes[:31].ljust(32, b'\x00')

            # Address 0x0068 in camera_registers stores the *memory address* in memory_map_data for DeviceModelName.
            model_name_address_in_map = gvcp_module.camera_registers.get(0x0068, None)

            if model_name_address_in_map is not None:
                start_index = model_name_address_in_map
                end_index = start_index + 32 # Length of DeviceModelName is 32 bytes

                if end_index <= len(gvcp_module.memory_map_data):
                    gvcp_module.memory_map_data[start_index:end_index] = padded_name_bytes
                    logger.info(f"DeviceModelName updated in memory_map_data to: '{new_name_str}' (raw: {padded_name_bytes.hex()}) at mem 0x{start_index:08X}")
                else:
                    logger.error(f"Calculated end index for DeviceModelName ({end_index}) is out of bounds for memory_map_data (len: {len(gvcp_module.memory_map_data)}).")
            else:
                logger.error("DeviceModelName address key (0x0068) not found in camera_registers. Cannot update name.")

        logger.info("Camera config applied to backend registers and/or memory map.")


    def trigger_acquisition_start(self):
        """Handles the logic for starting acquisition and streaming."""
        logger.info("Backend: AcquisitionStart triggered.")
        if not self.gvsp_streamer:
            logger.error("Cannot start acquisition: GVSP streamer not initialized.")
            return
        if not self.image_source:
             logger.error("Cannot start acquisition: Image source not initialized.")
             return

        self.gvsp_streamer.start_streaming()
        gvcp_module.camera_registers[0x0B08] = 1 # Update AcquisitionStatus register
        logger.info("Backend AcquisitionStatus set to Started (1).")

        # TODO: Implement continuous streaming in a loop/thread. For now, sends one frame.
        self.gvsp_streamer.send_single_frame()


    def trigger_acquisition_stop(self):
        """Handles the logic for stopping acquisition and streaming."""
        logger.info("Backend: AcquisitionStop triggered.")
        if not self.gvsp_streamer:
            logger.error("Cannot stop acquisition: GVSP streamer not initialized.")
            return

        self.gvsp_streamer.stop_streaming()
        gvcp_module.camera_registers[0x0B08] = 0 # Update AcquisitionStatus register
        logger.info("Backend AcquisitionStatus set to Stopped (0).")
