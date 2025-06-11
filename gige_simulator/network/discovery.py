import socket
import struct
import logging
from .gvcp import MODULE_GVCP_PORT as ADVERTISED_GVCP_PORT # Import the GVCP port to advertise

logger = logging.getLogger(__name__)

MODULE_DISCOVERY_PORT = 3956 # Default GigE Vision discovery port

# --- Simulated Device Information ---
# These would be configurable in a real device or more advanced simulator.
DEVICE_IP_ADDRESS = "192.168.1.100" # Static IP for the simulated device
DEVICE_MAC_ADDRESS = "00:11:22:33:44:55" # Simulated MAC address
DEVICE_MODEL_NAME = "PySimCam"
DEVICE_MANUFACTURER_NAME = "PythonSim"
DEVICE_VERSION = "0.0.1" # Firmware/Device version
DEVICE_SERIAL_NUMBER = "PS0001" # Device serial number

# GigE Vision Specification Version this simulator attempts to mimic for discovery
GIGE_VISION_VERSION_MAJOR = 2
GIGE_VISION_VERSION_MINOR = 0

# GVCP Command Codes (from GigE Vision Spec)
CMD_DISCOVERY_CMD = 0x0002 # Command code for DISCOVERY_CMD
ACK_DISCOVERY_ACK = 0x0003 # Command code for DISCOVERY_ACK (the response)

# Simulated Network Configuration (would be dynamic in a real device)
DEFAULT_GATEWAY = "192.168.1.1"
SUBNET_MASK = "255.255.255.0"

def set_discovery_port(port):
    """Allows changing the discovery port from the main application."""
    global MODULE_DISCOVERY_PORT
    MODULE_DISCOVERY_PORT = port
    logger.info(f"Discovery port dynamically set to {MODULE_DISCOVERY_PORT}")

def create_discovery_response(request_packet_data, command_ip):
    """
    Constructs a DISCOVERY_ACK packet in response to a DISCOVERY_CMD.
    The structure and content are based on the GigE Vision Specification v2.0, Table 5-2.
    Args:
        request_packet_data: The raw data from the received DISCOVERY_CMD.
        command_ip: The IP address of the client that sent the command (not used in this simplified ACK).
    Returns:
        bytes: The constructed DISCOVERY_ACK packet.
    """
    parsed_sequence_id = 0
    # Extract sequence ID from request_packet_data (DISCOVERY_CMD)
    # DISCOVERY_CMD structure (simplified): CMD_Code (2B), Length (2B), SequenceID (2B), ...
    if len(request_packet_data) >= 6:
        try:
            parsed_sequence_id = struct.unpack('>H', request_packet_data[4:6])[0]
        except struct.error: # Should not happen if packet format is as expected
            logger.warning("Could not parse sequence ID from discovery request.", exc_info=False)

    # --- DISCOVERY_ACK Payload Construction (264 bytes total) ---
    # Ref: GigE Vision Spec v2.0, Table 5-2 "DISCOVERY_ACK data fields"
    payload = bytearray(264) # Initialize with zeros; ensures correct length

    # Offsets and Sizes are critical as per specification. All multi-byte fields are Big Endian.

    # GigE Vision Version Major (Offset 0, Size 2, uint16_t)
    struct.pack_into('>H', payload, 0, GIGE_VISION_VERSION_MAJOR)
    # GigE Vision Version Minor (Offset 2, Size 2, uint16_t)
    struct.pack_into('>H', payload, 2, GIGE_VISION_VERSION_MINOR)

    # Device Mode (Offset 4, Size 4, uint32_t - bitfield)
    # Example: GenICam data Little Endian (bit 0=1), Stream channel Little Endian (bit 1=1), GVCP Big Endian (bit 2=0), Character Set UTF-8 (bit 29=0)
    device_mode = (1 << 0) | (1 << 1) | (0 << 2) | (0 << 29)
    struct.pack_into('>I', payload, 4, device_mode)

    # MAC Address High (Offset 8, Size 2) & Low (Offset 10, Size 4)
    try:
        mac_parts = DEVICE_MAC_ADDRESS.split(':')
        mac_bytes = b''.join([int(part, 16).to_bytes(1, 'big') for part in mac_parts])
        struct.pack_into('>H', payload, 8, int.from_bytes(mac_bytes[0:2], 'big')) # First 2 bytes of MAC
        struct.pack_into('>I', payload, 10, int.from_bytes(mac_bytes[2:6], 'big'))# Last 4 bytes of MAC
    except Exception as e: # Catch potential errors during MAC parsing/packing
        logger.error(f"Error packing MAC address '{DEVICE_MAC_ADDRESS}': {e}", exc_info=False)
        # Payload for MAC will remain zeros if error

    # Supported IP Configuration (Offset 14, Size 4, uint32_t - bitfield)
    # Bit 0: Persistent IP Supported, Bit 1: DHCP Supported, Bit 2: LLA Supported
    ip_config_supported = (1 << 0) | (1 << 1) | (1 << 2) # Device supports all three
    struct.pack_into('>I', payload, 14, ip_config_supported)

    # Current IP Configuration (Offset 18, Size 4, uint32_t - bitfield)
    # Bit 0: Persistent IP Active, Bit 1: DHCP Active, Bit 2: LLA Active
    ip_config_current = (1 << 0) # Device is currently using Persistent IP
    struct.pack_into('>I', payload, 18, ip_config_current)

    # --- Network Interface 0 Information (Primary Application Interface) ---
    # Current IP Address (Offset 30, Size 4, uint32_t)
    # Current Subnet Mask (Offset 46, Size 4, uint32_t)
    # Current Default Gateway (Offset 62, Size 4, uint32_t)
    try:
        struct.pack_into('!4s', payload, 30, socket.inet_aton(DEVICE_IP_ADDRESS)) # Using '!4s' for IPv4 address bytes
        struct.pack_into('!4s', payload, 46, socket.inet_aton(SUBNET_MASK))
        struct.pack_into('!4s', payload, 62, socket.inet_aton(DEFAULT_GATEWAY))
    except socket.error as e: # If IP address strings are invalid
        logger.error(f"Error packing network IPs (DevIP:{DEVICE_IP_ADDRESS}, SM:{SUBNET_MASK}, GW:{DEFAULT_GATEWAY}): {e}", exc_info=False)
        # IP fields in payload will remain zeros

    # Manufacturer Name (Offset 78, Size 32, string) - Padded with nulls if shorter
    payload[78:78+32] = DEVICE_MANUFACTURER_NAME.encode('utf-8')[:32].ljust(32, b'\x00')
    # Model Name (Offset 110, Size 32, string)
    payload[110:110+32] = DEVICE_MODEL_NAME.encode('utf-8')[:32].ljust(32, b'\x00')
    # Device Version (Offset 142, Size 32, string)
    payload[142:142+32] = DEVICE_VERSION.encode('utf-8')[:32].ljust(32, b'\x00')
    # Manufacturer Specific Information (Offset 174, Size 48, string)
    manuf_specific_info = f"SN:{DEVICE_SERIAL_NUMBER}".encode('utf-8')[:48].ljust(48, b'\x00') # Example: Embed serial number here
    payload[174:174+48] = manuf_specific_info
    # Serial Number (Offset 222, Size 16, string) - Dedicated field
    payload[222:222+16] = DEVICE_SERIAL_NUMBER.encode('utf-8')[:16].ljust(16, b'\x00')

    # ControlChannelPortID (GVCP Port) (Offset 236, Size 2, uint16_t)
    # This is crucial: tells the client which port GVCP is listening on.
    gvcp_port_to_advertise = ADVERTISED_GVCP_PORT # Use the (potentially dynamic) GVCP port
    struct.pack_into('>H', payload, 236, gvcp_port_to_advertise)
    logger.debug(f"GVCP port {gvcp_port_to_advertise} embedded into DISCOVERY_ACK (offset 236).")

    # Number of Network Interfaces (Offset 242, Size 2, uint16_t)
    struct.pack_into('>H', payload, 242, 1) # Simulating one interface

    # --- DISCOVERY_ACK Header (Simplified for UDP transmission) ---
    # Command Code (2B), Length of Payload (2B), Sequence ID (2B) = 6 bytes total
    # This header precedes the 264-byte payload.
    header = struct.pack('>HHH', ACK_DISCOVERY_ACK, len(payload), parsed_sequence_id)

    logger.debug(f"Constructed DISCOVERY_ACK (Header: {header.hex()}, Payload len: {len(payload)}) for SeqID {parsed_sequence_id}")
    return header + payload

def start_discovery_listener():
    logger.info(f"Attempting to start discovery listener on port {MODULE_DISCOVERY_PORT}...")
    try:
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow reuse of the address, helpful for quick restarts
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind to all available interfaces ('0.0.0.0') on the discovery port
        server_address = ('0.0.0.0', MODULE_DISCOVERY_PORT)
        sock.bind(server_address)
        logger.info(f"Discovery listener started successfully on {server_address[0]}:{server_address[1]}")
    except socket.error as e:
        logger.critical(f"Socket error in start_discovery_listener: {e}", exc_info=True)
        return # Cannot proceed if socket fails
    except Exception as e: # Catch any other unexpected errors during setup
        logger.critical(f"An unexpected error occurred in start_discovery_listener setup: {e}", exc_info=True)
        return

    while True: # Main loop to listen for discovery commands
        try:
            data, address = sock.recvfrom(1024) # Buffer size for incoming discovery packets
            logger.debug(f"Discovery: Received {len(data)} bytes from {address[0]}:{address[1]}")
            # For deeper debugging of received packet:
            # logger.debug(f"  Discovery Raw Data (hex): {data.hex()}")

            # Basic validation of the received packet
            if len(data) >= 2: # Minimum length for a command code
                cmd_code_recv = struct.unpack('>H', data[0:2])[0]
                if cmd_code_recv != CMD_DISCOVERY_CMD: # Check if it's actually a DISCOVERY_CMD
                    logger.warning(f"Discovery: Received packet from {address} with unexpected CMD code: 0x{cmd_code_recv:04X}. Expecting 0x{CMD_DISCOVERY_CMD:04X}. Ignoring.")
                    continue # Skip processing this packet
            else: # Packet too short
                logger.warning(f"Discovery: Received short packet ({len(data)} bytes) from {address}. Too small to be a valid command. Ignoring.")
                continue

            logger.debug(f"Processing valid DISCOVERY_CMD (0x{CMD_DISCOVERY_CMD:04X}) from {address[0]}")
            ack_packet = create_discovery_response(data, address[0]) # Construct the ACK

            if ack_packet:
                sock.sendto(ack_packet, address) # Send ACK back to the client
                # Log details of the sent ACK for verification
                # The first 6 bytes of ack_packet are header (CMD, LEN, SEQ_ID)
                # The GVCP port is at offset 236 within the payload part of the ACK
                sent_gvcp_port = struct.unpack('>H', ack_packet[6+236 : 6+236+2])[0]
                logger.info(f"Sent DISCOVERY_ACK to {address}. Advertised Device IP: {DEVICE_IP_ADDRESS}, GVCP Port: {sent_gvcp_port}")
            else: # Should not happen if create_discovery_response is robust
                logger.error("Failed to create DISCOVERY_ACK packet. No response sent.")

        except socket.error as e: # Handle socket errors during receive/send
            logger.error(f"Socket error during discovery recv/send: {e}", exc_info=False) # Less verbose for common socket errors
        except Exception as e: # Catch any other errors in the loop
            logger.error(f"Error in discovery listener loop: {e}", exc_info=True) # Log full traceback for unexpected errors
```
