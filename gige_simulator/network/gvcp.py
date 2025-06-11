import socket
import struct
import os
import logging

from gige_simulator.image_source.image_loader import StaticImageSource
from gige_simulator.network.gvsp_sender import GVSPStreamer

logger = logging.getLogger(__name__)

MODULE_GVCP_PORT = 3957
GVCP_PORT = MODULE_GVCP_PORT # Alias for convenience

# GVCP Status Codes (GigE Vision Spec Table 6-2)
STATUS_SUCCESS = 0x0000             # Operation was successful
STATUS_CMD_NOT_IMPLEMENTED = 0x8001 # Command is not implemented by this device
STATUS_INVALID_ADDRESS = 0x8006     # Invalid address was specified
STATUS_WRITE_PROTECT = 0x8007       # The addressed register is read-only
STATUS_BAD_ALIGNMENT = 0x800F       # Read or write is not aligned to a 4-byte boundary
STATUS_ACCESS_DENIED = 0x8010       # Access to this register is not allowed with current privilege
STATUS_PACKET_RESEND = 0x0100       # Flag: A request to resend packets for a stream channel (not an error)

# GVCP Command Codes (GigE Vision Spec Table 6-1)
READREG_CMD = 0x0080
READREG_ACK = 0x0081
WRITEREG_CMD = 0x0082
WRITEREG_ACK = 0x0083
READMEM_CMD = 0x0084  # For reading blocks of memory
READMEM_ACK = 0x0085
# Other commands like WRITEMEM, PENDING_ACK, EVENT_CMD, etc. exist

XML_FILE_PATH = os.path.join('gige_simulator', 'genicam', 'genicam_model.xml')
GENICAM_XML_DATA_BYTES = b"" # Loaded at runtime from XML_FILE_PATH
GENICAM_URL_STRING = "Local:genicam_model.xml" # URL for accessing the XML via manifest table
GENICAM_URL_STRING_BYTES = b"" # Byte representation of GENICAM_URL_STRING

image_source_global = None # Global instance of StaticImageSource, initialized by initialize_memory_map
def get_image_source_global_func(): # Wrapper to provide image_source_global to GVSPStreamer
    return image_source_global
gvsp_streamer_global = None # Global instance of GVSPStreamer, initialized by initialize_memory_map

# --- Memory Map Addresses for GenICam Bootstrap Registers and Data Areas ---
# These are specific addresses used by clients to locate the GenICam XML and other data.
# Some of these registers directly contain values, others contain pointers (addresses) to data
# stored in the `memory_map_data` bytearray.

# This GVCP register (0x0D00) holds the *address* where the Manifest Table itself can be found.
MANIFEST_TABLE_ADDRESS_REGISTER = 0x0D00 # Standard CCP Bootstrap Register for Manifest Table Address
ACTUAL_MANIFEST_TABLE_START_ADDRESS = 0x10000 # The Manifest Table data itself starts at this memory location.

# These memory locations will store the URL string for the XML file and the XML data itself.
XML_URL_STRING_MEMORY_ADDRESS = 0x1F000
XML_DATA_MEMORY_ADDRESS = 0x20000

# This memory location is the start of an area dedicated to storing various string register values
# (like DeviceVendorName, DeviceModelName, etc.) as defined in the GenICam XML.
STRINGS_AREA_MEMORY_ADDRESS = 0x30000

# This memory location is used to store the file path for image loading.
IMAGE_PATH_STRING_MEMORY_ADDRESS = 0x31000

# --- String Constants for Device Information ---
DEVICE_VENDOR_NAME_STR = "PythonSim"
DEVICE_MODEL_NAME_STR = "PySimCam"
DEVICE_VERSION_STR = "0.0.1"

# --- `camera_registers` Dictionary ---
# This dictionary simulates the camera's register map.
# Keys are register addresses (integers).
# Values can be:
#   1. Direct integer values for simple registers (e.g., Width, Height, GevVersionMajor).
#   2. Pointers (memory addresses) to data stored in `memory_map_data`. This includes:
#      - Pointers to strings (e.g., DeviceVendorName's address points into STRINGS_AREA_MEMORY_ADDRESS).
#      - Pointers to data structures (e.g., MANIFEST_TABLE_ADDRESS_REGISTER points to ACTUAL_MANIFEST_TABLE_START_ADDRESS).
#      - Pointers for image loading (e.g., 0xC000 points to IMAGE_PATH_STRING_MEMORY_ADDRESS).
camera_registers = {
    # --- Bootstrap Registers (Standard Control Protocol - SCP) ---
    # Ref: GigE Vision Spec Appendix D & Table 5-1 (CCP Bootstrap Registers)
    0x0000: 0x00020000,  # GVCP Version (SCPR): Bits 16-31 Major (2), Bits 0-15 Minor (0) -> Version 2.0
    0x0004: 0x00000001,  # SCPS: Standard Control Port Status (Bit 0: Unconditional Access to Control Port)
    0x0008: 500,         # SCPT: Standard Control Protocol Timeout (ms). Device may close session if no GVCP activity.
    0x000C: (1 << 1),    # SCDC: Standard Control Description Command (Bit 1: Primary Application Interface URL available)
    0x0010: (1 << 0),    # SCFT: Standard Control Features Toggle (Bit 0: CCP Support for Interface 0 enabled)

    # Manifest Table Pointer Register
    # This register's value is the *address* where the manifest table begins in memory.
    MANIFEST_TABLE_ADDRESS_REGISTER: ACTUAL_MANIFEST_TABLE_START_ADDRESS, # 0x0D00 -> 0x10000

    # Device Information Registers (Values often mirrored from GenICam XML for direct access)
    # String registers below point to their respective data locations within STRINGS_AREA_MEMORY_ADDRESS.
    0x0048: STRINGS_AREA_MEMORY_ADDRESS + 0,   # DeviceVendorName string location
    0x0068: STRINGS_AREA_MEMORY_ADDRESS + 32,  # DeviceModelName string location
    0x0088: STRINGS_AREA_MEMORY_ADDRESS + 64,  # DeviceVersion string location

    # GEV Version registers (as per XML, reflects parts of SCPR or device capabilities)
    0x0030: 2,           # GevVersionMajor (reflects SCPR Major version)
    0x0032: 0,           # GevVersionMinor (reflects SCPR Minor version)

    # Image Control/Status Registers (values typically match GenICam XML defaults or current state)
    0x0A00: 640,         # Width (pixels)
    0x0A04: 480,         # Height (pixels)
    0x0A08: 0x01080001,  # PixelFormat (Mono8, from PFNC - Pixel Format Naming Convention)
    0x0B00: 0,           # AcquisitionStart (Command Register - write 1 to trigger)
    0x0B04: 0,           # AcquisitionStop (Command Register - write 1 to trigger)
    0x0B08: 0,           # AcquisitionStatus (Read-Only): 0=Stopped, 1=Started

    # Image Loading Control Registers
    # 0xC000 register holds the memory address where the current image file path string is stored.
    0xC000: IMAGE_PATH_STRING_MEMORY_ADDRESS,
    0xC004: 0,           # LoadImageCmd (Command Register - write 1 to trigger loading)

    # GVSP Stream Channel Control Registers (CCP Bootstrap Registers for Streaming Channel)
    0x0D18: 0,           # GevSCPHostPort (Client's listening port for GVSP stream)
    0x0D1C: 0,           # GevSCPHostAddress (Client's IP address for GVSP stream, as integer)
}
# `memory_map_data` simulates a flat memory space accessible by the camera's GVCP logic.
# It stores data pointed to by registers in `camera_registers` (e.g., XML, strings, manifest table).
memory_map_data = bytearray(65536 * 5) # Approx 320KB simulation memory

def set_gvcp_port(port):
    global MODULE_GVCP_PORT, GVCP_PORT
    MODULE_GVCP_PORT = port
    GVCP_PORT = port
    logger.info(f"GVCP port dynamically set to {MODULE_GVCP_PORT}")

def get_string_from_memory(start_address, max_len=255):
    try:
        # Find null terminator or read up to max_len
        end_index = memory_map_data.find(b'\x00', start_address, start_address + max_len)
        actual_end = end_index if end_index != -1 else start_address + max_len
        raw_bytes = memory_map_data[start_address : actual_end]
        return raw_bytes.decode('utf-8', errors='ignore')
    except Exception as e: logger.error(f"Error reading string from 0x{start_address:08X}: {e}", exc_info=False); return ""

def initialize_memory_map(default_image_path_arg):
    global GENICAM_XML_DATA_BYTES, GENICAM_URL_STRING_BYTES, memory_map_data, camera_registers, image_source_global, gvsp_streamer_global

    logger.info(f"Initializing GVCP memory map. Default image: '{default_image_path_arg}'")
    image_source_global = StaticImageSource() # Create image source instance
    if os.path.exists(default_image_path_arg):
        if image_source_global.load_image(default_image_path_arg, "Mono8"): # Load default image
            # Update camera registers with actual dimensions and format from loaded image
            camera_registers[0x0A00] = image_source_global.width
            camera_registers[0x0A04] = image_source_global.height
            camera_registers[0x0A08] = image_source_global.pixel_format_gvsp
            logger.info(f"Default image '{default_image_path_arg}' loaded. W,H,PF updated in registers.")
    else:
        logger.warning(f"Default image path '{default_image_path_arg}' not found during init. Camera may not stream valid data until an image is loaded via GVCP.")

    gvsp_streamer_global = GVSPStreamer(get_image_source_global_func) # Initialize GVSP streamer

    # Load GenICam XML file into memory
    try:
        with open(XML_FILE_PATH, 'rb') as f: GENICAM_XML_DATA_BYTES = f.read()
        logger.info(f"Loaded GenICam XML: {XML_FILE_PATH}, Size: {len(GENICAM_XML_DATA_BYTES)} bytes")
    except Exception as e: logger.error(f"Error loading GenICam XML '{XML_FILE_PATH}': {e}", exc_info=True); GENICAM_XML_DATA_BYTES = b"<error_loading_xml/>"

    GENICAM_URL_STRING_BYTES = GENICAM_URL_STRING.encode('utf-8')

    # --- Populate Manifest Table in `memory_map_data` ---
    # The manifest table tells the client where to find the XML file.
    # It's located at ACTUAL_MANIFEST_TABLE_START_ADDRESS (e.g., 0x10000).
    # Structure (simplified):
    #   Offset 0: Schema Version (e.g., 1.0.0 -> 0x01000000) - 4 bytes
    #   Offset 4: Number of Entries (1 for our single XML file) - 4 bytes
    #   Offset 8: URL Length for entry 1 - 4 bytes
    #   Offset 12: URL Address for entry 1 (points to XML_URL_STRING_MEMORY_ADDRESS) - 4 bytes
    #   Offset 16: XML File Size for entry 1 - 4 bytes
    #   Offset 20: XML File Address for entry 1 (points to XML_DATA_MEMORY_ADDRESS) - 4 bytes
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 0, 0x01000000)
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 4, 1)
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 8, len(GENICAM_URL_STRING_BYTES))
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 12, XML_URL_STRING_MEMORY_ADDRESS)
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 16, len(GENICAM_XML_DATA_BYTES))
    struct.pack_into('>I', memory_map_data, ACTUAL_MANIFEST_TABLE_START_ADDRESS + 20, XML_DATA_MEMORY_ADDRESS)
    logger.debug(f"Manifest table (1 entry) populated at memory 0x{ACTUAL_MANIFEST_TABLE_START_ADDRESS:08X}")

    # Store the XML URL string ("Local:genicam_model.xml") in `memory_map_data`
    memory_map_data[XML_URL_STRING_MEMORY_ADDRESS : XML_URL_STRING_MEMORY_ADDRESS + len(GENICAM_URL_STRING_BYTES)] = GENICAM_URL_STRING_BYTES
    logger.debug(f"XML URL string '{GENICAM_URL_STRING}' stored at memory 0x{XML_URL_STRING_MEMORY_ADDRESS:08X}")

    # Store the actual XML file content in `memory_map_data`
    memory_map_data[XML_DATA_MEMORY_ADDRESS : XML_DATA_MEMORY_ADDRESS + len(GENICAM_XML_DATA_BYTES)] = GENICAM_XML_DATA_BYTES
    logger.debug(f"XML data (size {len(GENICAM_XML_DATA_BYTES)}) stored at memory 0x{XML_DATA_MEMORY_ADDRESS:08X}")

    # Populate String Registers Area in `memory_map_data`
    string_registers_map = {
        0x0048: DEVICE_VENDOR_NAME_STR,
        0x0068: DEVICE_MODEL_NAME_STR,
        0x0088: DEVICE_VERSION_STR,
    }
    for reg_addr_key, str_val in string_registers_map.items():
        mem_addr_for_string = camera_registers.get(reg_addr_key) # This is the address in STRINGS_AREA_MEMORY_ADDRESS
        if mem_addr_for_string is not None:
            encoded_bytes = str_val.encode('utf-8')[:32].ljust(32, b'\0') # Ensure 32 bytes, null padded
            memory_map_data[mem_addr_for_string : mem_addr_for_string + 32] = encoded_bytes
            logger.debug(f"String '{str_val}' for GenICam feature at reg 0x{reg_addr_key:04X} stored at mem 0x{mem_addr_for_string:08X}")
        else: # Should not happen if camera_registers is correctly defined
            logger.error(f"Register key 0x{reg_addr_key:04X} (for string '{str_val}') not found in camera_registers during init.")

    # Store the default image path string in `memory_map_data`
    default_path_bytes = default_image_path_arg.encode('utf-8')[:255].ljust(256, b'\0') # Max 255 chars + null
    memory_map_data[IMAGE_PATH_STRING_MEMORY_ADDRESS : IMAGE_PATH_STRING_MEMORY_ADDRESS + 256] = default_path_bytes
    logger.debug(f"Default image path string ('{default_image_path_arg}') stored at memory 0x{IMAGE_PATH_STRING_MEMORY_ADDRESS:08X}")

    logger.info("GVCP memory map, GenICam data, and string areas initialized.")


def handle_readreg_cmd(request_id, data_payload):
    if len(data_payload) < 4: # READREG_CMD payload must be at least 4 bytes (address)
        logger.warning(f"READREG_CMD: Payload too short ({len(data_payload)} bytes). Expected 4.")
        return struct.pack('>HHHH', STATUS_BAD_ALIGNMENT, READREG_ACK, 0, request_id) # Error ACK

    reg_addr = struct.unpack('>I', data_payload[:4])[0] # Register address is Big Endian Unsigned Int
    logger.debug(f"GVCP: READREG_CMD for address 0x{reg_addr:08X}, ReqID: {request_id}")

    reg_value_to_pack = 0 # Default value if address is invalid or read fails
    status = STATUS_SUCCESS

    # 1. Check if the address is for a direct register value in `camera_registers`
    if reg_addr in camera_registers:
        reg_value_to_pack = camera_registers[reg_addr]
        logger.debug(f"  Read from camera_registers: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X}")

    # 2. Check if the address falls into a mapped memory region (e.g., manifest table, XML data, strings)
    #    For these, READREG typically reads a 4-byte chunk from that memory location.
    elif ACTUAL_MANIFEST_TABLE_START_ADDRESS <= reg_addr < ACTUAL_MANIFEST_TABLE_START_ADDRESS + 128: # Arbitrary reasonable size for manifest
        try:
            # Ensure read is aligned if necessary (typically 4-byte for READREG)
            if reg_addr % 4 != 0: status = STATUS_BAD_ALIGNMENT; logger.warning(f"  Read from Manifest Table: Unaligned address 0x{reg_addr:08X}")
            else:
                reg_value_to_pack = struct.unpack('>I', memory_map_data[reg_addr : reg_addr+4])[0]
                logger.debug(f"  Read from Manifest Table memory: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X}")
        except IndexError: status = STATUS_INVALID_ADDRESS; logger.warning(f"  Read from Manifest Table: Address 0x{reg_addr:08X} out of bounds (IndexError).")
        except struct.error: status = STATUS_BAD_ALIGNMENT; logger.warning(f"  Read from Manifest Table: Struct error at 0x{reg_addr:08X} (likely bad data or offset).")

    elif XML_URL_STRING_MEMORY_ADDRESS <= reg_addr < XML_URL_STRING_MEMORY_ADDRESS + len(GENICAM_URL_STRING_BYTES) + 3: # Allow reading last few bytes
        chunk = memory_map_data[reg_addr : reg_addr + 4].ljust(4, b'\0') # Pad with nulls if reading past end
        reg_value_to_pack = struct.unpack('>I', chunk)[0]
        logger.debug(f"  Read from XML URL String memory: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X} (bytes: {chunk.hex()})")
    elif XML_DATA_MEMORY_ADDRESS <= reg_addr < XML_DATA_MEMORY_ADDRESS + len(GENICAM_XML_DATA_BYTES) + 3:
        chunk = memory_map_data[reg_addr : reg_addr + 4].ljust(4, b'\0')
        reg_value_to_pack = struct.unpack('>I', chunk)[0]
        logger.debug(f"  Read from XML Data memory: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X} (bytes: {chunk.hex()})")
    elif STRINGS_AREA_MEMORY_ADDRESS <= reg_addr < STRINGS_AREA_MEMORY_ADDRESS + 256 + 3 : # Max size of strings area + padding
        chunk = memory_map_data[reg_addr : reg_addr + 4].ljust(4, b'\0')
        reg_value_to_pack = struct.unpack('>I', chunk)[0]
        logger.debug(f"  Read from Strings Area memory: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X} (bytes: {chunk.hex()})")
    elif IMAGE_PATH_STRING_MEMORY_ADDRESS <= reg_addr < IMAGE_PATH_STRING_MEMORY_ADDRESS + 256 + 3: # Image path string area
        chunk = memory_map_data[reg_addr : reg_addr + 4].ljust(4, b'\0')
        reg_value_to_pack = struct.unpack('>I', chunk)[0]
        logger.debug(f"  Read from Image Path String memory: 0x{reg_addr:08X} -> Value: 0x{reg_value_to_pack:08X} (bytes: {chunk.hex()})")
    else: # Address not found in direct registers or mapped memory
        status = STATUS_INVALID_ADDRESS
        logger.warning(f"READREG_CMD: Address 0x{reg_addr:08X} is not a known register or mapped memory area.")

    # Construct and return ACK
    if status == STATUS_SUCCESS:
        # READREG_ACK payload: Address (4 bytes), Value (4 bytes)
        ack_payload = struct.pack('>II', reg_addr, reg_value_to_pack)
        # READREG_ACK header: Status (Success), ACK Code, Payload Length, Request ID
        ack_header = struct.pack('>HHHH', STATUS_SUCCESS, READREG_ACK, len(ack_payload), request_id)
        return ack_header + ack_payload
    else: # Error status
        # Error ACK: Status (Error Code), ACK Code, Payload Length (0), Request ID
        return struct.pack('>HHHH', status, READREG_ACK, 0, request_id)


def handle_writereg_cmd(request_id, data_payload, source_ip_port_tuple):
    global image_source_global, gvsp_streamer_global

    if len(data_payload) < 8: # WRITEREG_CMD payload: Address (4B) + Value (4B) minimum
        logger.warning(f"WRITEREG_CMD from {source_ip_port_tuple}: Payload too short ({len(data_payload)} bytes). Expected at least 8.")
        return struct.pack('>HHHH', STATUS_BAD_ALIGNMENT, WRITEREG_ACK, 0, request_id)

    reg_addr, reg_value = struct.unpack('>II', data_payload[:8]) # Address and Value are Big Endian Unsigned Int
    logger.info(f"GVCP: WRITEREG_CMD from {source_ip_port_tuple} for address 0x{reg_addr:08X} with value 0x{reg_value:08X} (ReqID: {request_id})")

    status = STATUS_SUCCESS
    # 1. Handle Command Registers
    if reg_addr == 0xC004 and reg_value == 1: # LoadImageCmd
        logger.info(f"  Command: LoadImageCmd invoked by {source_ip_port_tuple}.")
        path_addr_in_reg = camera_registers.get(0xC000, IMAGE_PATH_STRING_MEMORY_ADDRESS) # Get address of path string from reg 0xC000
        image_file_path_str = get_string_from_memory(path_addr_in_reg) # Read path from memory_map_data
        logger.debug(f"  Attempting to load image from path string: '{image_file_path_str}' (read from mem addr 0x{path_addr_in_reg:08X})")
        if image_source_global and image_file_path_str:
            current_gvsp_pf = camera_registers.get(0x0A08, 0x01080001) # Get current pixel format
            target_pf_str = "Mono8" if current_gvsp_pf == 0x01080001 else "RGB8" # Determine target format string
            if image_source_global.load_image(image_file_path_str, target_pf_str):
                camera_registers[0x0A00] = image_source_global.width   # Update Width register
                camera_registers[0x0A04] = image_source_global.height  # Update Height register
                camera_registers[0x0A08] = image_source_global.pixel_format_gvsp # Update PixelFormat register
                logger.info(f"  Image '{image_file_path_str}' loaded. W,H,PF updated in camera_registers.")
                logger.debug(f"  New W: {camera_registers[0x0A00]}, H: {camera_registers[0x0A04]}, PF: 0x{camera_registers[0x0A08]:08X}")
            else: status = STATUS_ACCESS_DENIED; logger.error(f"  Failed to load image '{image_file_path_str}' for LoadImageCmd.")
        else: status = STATUS_ACCESS_DENIED; logger.error("  Image source not available or path string empty for LoadImageCmd.")
        camera_registers[0xC004] = 0 # Reset command register value after execution

    elif reg_addr == 0x0B00 and reg_value == 1: # AcquisitionStart Command
        logger.info(f"  Command: AcquisitionStart invoked by {source_ip_port_tuple}.")
        if gvsp_streamer_global:
            gvsp_streamer_global.start_streaming()
            camera_registers[0x0B08] = 1 # Update AcquisitionStatus register
            gvsp_streamer_global.send_single_frame() # Send one frame as per current design
            logger.debug("  Acquisition started, one frame initiated for sending.")
        else: status = STATUS_ACCESS_DENIED; logger.error("  GVSP streamer not ready for AcquisitionStart.")
        # Typically, command registers don't hold the trigger value, or are reset by firmware.
        # camera_registers[0x0B00] = 0

    elif reg_addr == 0x0B04 and reg_value == 1: # AcquisitionStop Command
        logger.info(f"  Command: AcquisitionStop invoked by {source_ip_port_tuple}.")
        if gvsp_streamer_global:
            gvsp_streamer_global.stop_streaming()
            camera_registers[0x0B08] = 0 # Update AcquisitionStatus register
            logger.debug("  Acquisition stopped.")
        else: status = STATUS_ACCESS_DENIED; logger.error("  GVSP streamer not ready for AcquisitionStop.")
        # camera_registers[0x0B04] = 0

    # 2. Handle writes to specific registers (e.g., GevSCPHostPort, GevSCPHostAddress)
    elif reg_addr == 0x0D18: # GevSCPHostPort
        camera_registers[reg_addr] = reg_value # Store the port
        if gvsp_streamer_global: # Update streamer destination
            gvsp_streamer_global.update_client_destination(camera_registers.get(0x0D1C,0), camera_registers.get(0x0D18,0))
        logger.debug(f"  GevSCPHostPort (0x0D18) set to {reg_value}.")
    elif reg_addr == 0x0D1C: # GevSCPHostAddress
        camera_registers[reg_addr] = reg_value # Store the IP address (integer)
        if gvsp_streamer_global: # Update streamer destination
             gvsp_streamer_global.update_client_destination(camera_registers.get(0x0D1C,0), camera_registers.get(0x0D18,0))
        logger.debug(f"  GevSCPHostAddress (0x0D1C) set to 0x{reg_value:08X}.")

    # 3. Handle writes to memory areas (e.g., ImageFilePath string)
    #    This allows client to write string data chunk by chunk using WRITEREG.
    #    A full WRITEMEM_CMD would be more efficient for longer strings.
    elif IMAGE_PATH_STRING_MEMORY_ADDRESS <= reg_addr < IMAGE_PATH_STRING_MEMORY_ADDRESS + 256 -3 : # -3 to allow full 4-byte write
        # Ensure write is aligned if necessary (typically 4-byte for WRITEREG)
        if reg_addr % 4 != 0: status = STATUS_BAD_ALIGNMENT; logger.warning(f"  Write to Image Path String: Unaligned address 0x{reg_addr:08X}")
        else:
            offset_in_path_area = reg_addr - IMAGE_PATH_STRING_MEMORY_ADDRESS
            packed_value = struct.pack('>I', reg_value) # Value is 4 bytes
            memory_map_data[IMAGE_PATH_STRING_MEMORY_ADDRESS + offset_in_path_area : IMAGE_PATH_STRING_MEMORY_ADDRESS + offset_in_path_area + 4] = packed_value
            logger.debug(f"  Wrote 0x{reg_value:08X} (bytes: {packed_value.hex()}) to image path string area at memory 0x{reg_addr:08X}")

    # 4. Handle writes to other general writable registers in `camera_registers`
    elif reg_addr in camera_registers:
        # Check for Read-Only registers before writing
        # Example RO registers: SCPR (0x0000), GevVersionMajor/Minor (0x0030, 0x0032), String Reg Addrs (0x0048 etc.), AcquisitionStatus (0x0B08), ManifestTableAddr (0x0D00)
        read_only_registers = [0x0000, 0x0030, 0x0032, 0x0048, 0x0068, 0x0088, 0x0B08, 0x0D00, 0xC000]
        if reg_addr in read_only_registers:
             status = STATUS_WRITE_PROTECT
             logger.warning(f"  Attempt to write to read-only register 0x{reg_addr:08X} by {source_ip_port_tuple}.")
        else: # Writable register
            camera_registers[reg_addr] = reg_value
            logger.debug(f"  Register 0x{reg_addr:08X} in camera_registers set to 0x{reg_value:08X}")
    else: # Address not found in direct registers or special memory write areas
        status = STATUS_INVALID_ADDRESS
        logger.warning(f"WRITEREG_CMD: Address 0x{reg_addr:08X} not found or not writable by {source_ip_port_tuple}.")

    # Construct and return ACK
    # WRITEREG_ACK payload is typically empty on success. Header contains status.
    return struct.pack('>HHHH', status, WRITEREG_ACK, 0, request_id)


def start_gvcp_listener():
    logger.info(f"Attempting to start GVCP listener on port {MODULE_GVCP_PORT}...")
    if gvsp_streamer_global is None or image_source_global is None:
        logger.critical("GVCP Listener cannot start: core components (GVSP streamer or Image Source) not initialized. Ensure initialize_memory_map() is called first.")
        return

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', MODULE_GVCP_PORT))
        logger.info(f"GVCP listener started on 0.0.0.0:{MODULE_GVCP_PORT}")
    except Exception as e: logger.critical(f"GVCP Socket/Bind Error: {e}", exc_info=True); return

    while True:
        try:
            data, address = sock.recvfrom(2048) # Buffer for GVCP packets
            logger.debug(f"GVCP: Received {len(data)} bytes from {address}")
            if len(data) < 8: # Minimum GVCP header size (Status/Key, Command, Length, RequestID)
                logger.warning(f"GVCP: Packet too short ({len(data)} bytes) from {address} to be valid GVCP. Ignoring.")
                continue

            # Unpack common GVCP header (assuming Status/Key field is first for CMDs, typically 0x0000 or flags)
            key_flags, cmd_code, length, req_id = struct.unpack('>HHHH', data[:8])
            payload = data[8:] # Remaining data is payload

            if cmd_code != READREG_CMD: # Reduce log spam for frequent READREG polls
                 logger.info(f"GVCP CMD 0x{cmd_code:04X} from {address}, Key/Flags:0x{key_flags:04X}, Len:{length}, ReqID:{req_id}")
            else: # Log READREG at DEBUG level
                 logger.debug(f"GVCP CMD 0x{cmd_code:04X} from {address}, Key/Flags:0x{key_flags:04X}, Len:{length}, ReqID:{req_id}")

            ack_packet = None
            if cmd_code == READREG_CMD:
                ack_packet = handle_readreg_cmd(req_id, payload)
            elif cmd_code == WRITEREG_CMD:
                ack_packet = handle_writereg_cmd(req_id, payload, address) # Pass client address for logging write attempts
            else: # Unsupported command
                logger.warning(f"GVCP: Unsupported CMD code 0x{cmd_code:04X} received from {address}.")
                # Generic ACK for unsupported command: Status=NotImplemented, ACKCode=CMDCode+1 (common pattern), Len=0, ReqID
                ack_packet = struct.pack('>HHHH', STATUS_CMD_NOT_IMPLEMENTED, cmd_code | 1, 0, req_id)

            if ack_packet: sock.sendto(ack_packet, address)

        except Exception as e: logger.error(f"GVCP Loop Error: {e}", exc_info=True) # Log full traceback for unexpected errors in loop

if __name__ == '__main__':
    # This block is for direct testing of gvcp.py.
    # In normal operation, initialize_memory_map() and start_gvcp_listener() are called from core/main.py.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s')
    logger.info("Starting GVCP listener directly for testing...")
    # Provide a dummy default image path when testing gvcp.py standalone
    initialize_memory_map(os.path.join("..", "sample_images", "sample_image.png")) # Adjust path for direct run
    start_gvcp_listener()
```
