import socket
import struct
import time
import logging

logger = logging.getLogger(__name__)

# --- Simplified GVSP Packet Type Indicators ---
# These are custom values for a simplified header's "packet type" field.
# A standard GVSP header is more complex.
# - Leader Packet: Indicates the start of a new frame (block of data).
# - Payload Packet: Carries a chunk of the actual pixel data.
# - Trailer Packet: Indicates the end of a frame.
PACKET_TYPE_LEADER = 0x01
PACKET_TYPE_PAYLOAD = 0x03
PACKET_TYPE_TRAILER = 0x02

DEFAULT_PAYLOAD_SIZE = 1440  # Max bytes of pixel data per payload packet.
                             # Chosen to typically fit within a standard Ethernet MTU (around 1500 bytes)
                             # minus IP/UDP headers and our simplified GVSP payload header.
GVSP_VERSION = 0x01 # Using a simplified GVSP version indicator for our custom header.

class GVSPStreamer:
    def __init__(self, image_source_provider_func):
        self.image_source_provider_func = image_source_provider_func # Function to get the current image source
        self.client_ip_str = None      # Client IP address (string) to send stream to
        self.client_port_int = None    # Client port (integer)
        self.streaming_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP socket for sending
        self.streaming_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_streaming = False      # Flag to control streaming state
        self.block_id_counter = 0      # Frame counter (uint16), also known as Block ID in GVSP
        self.current_frame_packet_id_counter = 0 # Packet counter within the current frame (uint_bigger_than_16)

    def update_client_destination(self, ip_int, port_int):
        """Updates the client IP address and port for the GVSP stream."""
        old_ip = self.client_ip_str
        old_port = self.client_port_int

        if ip_int is not None and ip_int != 0 and port_int is not None and port_int != 0:
            try:
                new_ip_str = socket.inet_ntoa(struct.pack('!I', ip_int)) # Convert integer IP to string
                self.client_ip_str = new_ip_str
                self.client_port_int = port_int
                logger.info(f"GVSP Destination updated. Old: {old_ip}:{old_port}, New: {self.client_ip_str}:{self.client_port_int}")
            except Exception as e:
                self.client_ip_str = None
                self.client_port_int = None
                logger.error(f"Error setting GVSP client destination from IP int 0x{ip_int:08X}, port {port_int}: {e}", exc_info=False)
        else:
            self.client_ip_str = None
            self.client_port_int = None
            logger.info(f"GVSP Destination cleared (was {old_ip}:{old_port}). IP/Port was 0 or None.")

    def start_streaming(self):
        """Enables the streaming flag if a valid client destination is set."""
        if self.client_ip_str and self.client_port_int:
            self.is_streaming = True
            logger.info(f"GVSP Streaming started to {self.client_ip_str}:{self.client_port_int}.")
        else:
            self.is_streaming = False # Ensure it's false
            logger.warning("GVSP Streaming cannot start: Client IP or Port not set.")

    def stop_streaming(self):
        """Disables the streaming flag."""
        self.is_streaming = False
        logger.info("GVSP Streaming stopped.")

    def send_single_frame(self):
        """Constructs and sends one full frame (Leader, Payloads, Trailer) to the client."""
        if not self.is_streaming:
            logger.debug("GVSP: Not currently streaming (is_streaming=False), frame not sent.")
            return
        if not self.client_ip_str or not self.client_port_int:
            logger.warning("GVSP: No client destination set for streaming, frame not sent.")
            return

        image_source = self.image_source_provider_func()
        if not image_source:
            logger.error("GVSP: No image source available (provider function returned None). Frame not sent.")
            return

        frame_info = image_source.get_frame() # Get data from the image source
        if not frame_info or frame_info.get("pixel_data") is None:
            logger.warning("GVSP: No frame data available from image source. Frame not sent.")
            return

        # Unpack frame information
        pixel_data = frame_info['pixel_data']
        width = frame_info['width']
        height = frame_info['height']
        pixel_format_gvsp = frame_info['pixel_format_gvsp'] # GVSP Pixel Format Code (e.g., Mono8 = 0x01080001)
        size_bytes = frame_info['size_bytes']               # Total size of pixel data in bytes

        if not all([pixel_data, width, height, pixel_format_gvsp is not None, size_bytes > 0]):
            logger.error(f"GVSP: Incomplete frame data from source, cannot send. W:{width}, H:{height}, PF:0x{pixel_format_gvsp:X if pixel_format_gvsp else 'N/A'}, Size:{size_bytes}")
            return

        logger.info(f"GVSP: Preparing to stream frame. Image: {image_source.image_path}, W:{width}, H:{height}, PF:0x{pixel_format_gvsp:08X}, Size:{size_bytes} bytes.")

        self.block_id_counter = (self.block_id_counter + 1) & 0xFFFF # Increment frame ID (Block ID), wrap at 16 bits
        self.current_frame_packet_id_counter = 0 # Reset packet ID for this new frame

        timestamp_ns = int(time.time() * 1_000_000_000) # Example nanosecond timestamp

        # --- Leader Packet Construction (Simplified Structure from Prompt) ---
        # This structure is a simplification for the simulator.
        # Real GVSP Leader has a more complex header (e.g., status field, specific payload type for image data).
        # Header: BlockID (2B), CustomType (1B), Reserved (1B), PacketID (2B), Timestamp (8B) = 14 bytes
        # Data: PixelFormat (4B), SizeX (4B), SizeY (4B), OffsetX (4B), OffsetY (4B) = 20 bytes
        # Total: 34 bytes
        self.current_frame_packet_id_counter = 1 # Leader is typically packet 1
        leader_header = struct.pack('>H B B H Q',  # Big Endian
                                    self.block_id_counter,
                                    PACKET_TYPE_LEADER, # Custom type field indicating leader
                                    0, # Reserved/flags field
                                    self.current_frame_packet_id_counter,
                                    timestamp_ns)
        leader_data = struct.pack('>I I I I I',   # Big Endian
                                  pixel_format_gvsp, width, height, 0, 0) # OffsetX, OffsetY = 0

        try:
            self.streaming_socket.sendto(leader_header + leader_data, (self.client_ip_str, self.client_port_int))
            logger.debug(f"GVSP: Leader packet for frame BID {self.block_id_counter}, PID {self.current_frame_packet_id_counter} sent to {self.client_ip_str}:{self.client_port_int}")
        except socket.error as e:
            logger.error(f"GVSP: Socket error sending leader packet: {e}", exc_info=False)
            self.stop_streaming() # Stop streaming on send error
            return

        # --- Payload Packets Construction (Simplified Structure from Prompt) ---
        # Header: BlockID (2B), CustomType (1B), Reserved (1B), PacketID (2B) = 6 bytes
        # Data: Pixel data chunk
        bytes_sent = 0
        payload_packets_count = 0
        while bytes_sent < size_bytes:
            self.current_frame_packet_id_counter += 1
            payload_packets_count +=1
            chunk_size = min(DEFAULT_PAYLOAD_SIZE, size_bytes - bytes_sent)
            chunk = pixel_data[bytes_sent : bytes_sent + chunk_size]
            payload_header = struct.pack('>H B B H', # Big Endian
                                         self.block_id_counter,
                                         PACKET_TYPE_PAYLOAD, # Custom type field
                                         0, # Reserved
                                         self.current_frame_packet_id_counter)
            try:
                self.streaming_socket.sendto(payload_header + chunk, (self.client_ip_str, self.client_port_int))
                # Log first few payloads and then periodically to avoid spamming for large images
                if payload_packets_count <= 3 or (payload_packets_count % 100 == 0) :
                     logger.debug(f"GVSP: Payload packet for frame BID {self.block_id_counter}, PID {self.current_frame_packet_id_counter} (chunk# {payload_packets_count}, size {len(chunk)}) sent.")
            except socket.error as e:
                logger.error(f"GVSP: Socket error sending payload packet PID {self.current_frame_packet_id_counter}: {e}", exc_info=False)
                self.stop_streaming()
                return
            bytes_sent += chunk_size
        logger.debug(f"GVSP: Sent {payload_packets_count} payload packets for frame BID {self.block_id_counter}.")

        # --- Trailer Packet Construction (Simplified Structure from Prompt) ---
        # Header: BlockID (2B), CustomType (1B), Reserved (1B), PacketID (2B) = 6 bytes
        # Data: Expected SizeY (4B) - a common field in trailers, though spec might define others.
        # Total: 10 bytes
        self.current_frame_packet_id_counter += 1
        trailer_header = struct.pack('>H B B H', # Big Endian
                                     self.block_id_counter,
                                     PACKET_TYPE_TRAILER, # Custom type field
                                     0, # Reserved
                                     self.current_frame_packet_id_counter)
        trailer_data = struct.pack('>I', height) # Example: Trailer carries vertical size of frame.

        try:
            self.streaming_socket.sendto(trailer_header + trailer_data, (self.client_ip_str, self.client_port_int))
            logger.debug(f"GVSP: Trailer packet for frame BID {self.block_id_counter}, PID {self.current_frame_packet_id_counter} sent.")
        except socket.error as e:
            logger.error(f"GVSP: Socket error sending trailer packet: {e}", exc_info=False)
            self.stop_streaming()
            return

        logger.info(f"GVSP: Frame BID {self.block_id_counter} sent to {self.client_ip_str}:{self.client_port_int} ({self.current_frame_packet_id_counter} total packets).")
