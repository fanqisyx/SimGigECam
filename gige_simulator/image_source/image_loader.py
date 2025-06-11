from PIL import Image # Pillow library for image manipulation
import logging

logger = logging.getLogger(__name__)

class StaticImageSource:
    """
    Loads an image from a file using Pillow, converts it to a target pixel format,
    and provides its raw pixel data and metadata.
    """
    def __init__(self, image_path=None, target_pixel_format_str="Mono8"):
        """
        Initializes the StaticImageSource.
        Args:
            image_path (str, optional): Path to the image file to be loaded initially.
            target_pixel_format_str (str, optional): The desired target pixel format string
                                                     (e.g., "Mono8", "RGB8"). Defaults to "Mono8".
        """
        self.image_path = image_path    # Path to the currently loaded image or last attempted
        self.pixel_data = None          # Raw pixel data as bytes
        self.width = 0                  # Image width in pixels
        self.height = 0                 # Image height in pixels
        self.pixel_format_gvsp = None   # GVSP Pixel Format Naming Convention (PFNC) code (integer)
        self.pil_format = None          # Pillow format string (e.g., "L" for grayscale, "RGB")
        self.file_size_bytes = 0        # Size of the raw pixel_data in bytes

        if image_path: # If an initial image path is provided, attempt to load it
            self.load_image(image_path, target_pixel_format_str)

    def load_image(self, image_path, target_pixel_format_str="Mono8"):
        """
        Loads an image from the specified file path and converts it to the target format.
        Updates instance attributes (width, height, pixel_data, formats, etc.).
        Args:
            image_path (str): The path to the image file.
            target_pixel_format_str (str): The desired target pixel format string (e.g., "Mono8").
        Returns:
            bool: True if the image was loaded and converted successfully, False otherwise.
        """
        logger.info(f"Attempting to load image: '{image_path}' as '{target_pixel_format_str}'")
        try:
            img = Image.open(image_path) # Open the image using Pillow
            self.image_path = image_path # Store path of successfully opened image

            # Convert image to the target pixel format
            if target_pixel_format_str == "Mono8":
                img = img.convert("L") # "L" mode is 8-bit grayscale
                self.pil_format = "L"
                self.pixel_format_gvsp = 0x01080001  # PFNC code for Mono8
            elif target_pixel_format_str == "RGB8": # For future use
                img = img.convert("RGB") # "RGB" mode is 24-bit RGB (8 bits per channel)
                self.pil_format = "RGB"
                self.pixel_format_gvsp = 0x02180014  # PFNC code for RGB8Packed
            else:
                logger.error(f"Unsupported target pixel format '{target_pixel_format_str}'. Cannot load image '{image_path}'.")
                self.reset_image_data() # Clear any previous image data
                return False

            # Update image metadata
            self.width = img.width
            self.height = img.height
            self.pixel_data = img.tobytes() # Get raw pixel data as a byte string
            self.file_size_bytes = len(self.pixel_data)

            logger.info(f"Image '{image_path}' loaded successfully.")
            logger.debug(f"  Converted Format (PIL): {self.pil_format}, GVSP PFNC: 0x{self.pixel_format_gvsp:08X}")
            logger.debug(f"  Dimensions: {self.width}x{self.height}")
            logger.debug(f"  Pixel data size: {self.file_size_bytes} bytes")
            return True

        except FileNotFoundError:
            logger.error(f"Image file not found at '{image_path}'.")
            self.reset_image_data()
            return False
        except Exception as e: # Catch other Pillow errors (e.g., corrupt image, unsupported format)
            logger.error(f"Error loading image '{image_path}': {e}", exc_info=True)
            self.reset_image_data()
            return False

    def reset_image_data(self):
        """Resets image-related attributes to their default (empty) state."""
        # self.image_path is not reset here to retain information about the last attempted load.
        self.pixel_data = None
        self.width = 0
        self.height = 0
        self.pixel_format_gvsp = None
        self.pil_format = None
        self.file_size_bytes = 0
        logger.debug("Image data attributes have been reset.")

    def get_frame(self):
        """
        Returns a dictionary containing the current frame's pixel data and metadata.
        If no image is loaded, returns metadata with None/zero values.
        """
        if not self.pixel_data:
            logger.debug("get_frame called but no pixel_data available.")
            return {
                "pixel_data": None, "width": 0, "height": 0,
                "pixel_format_gvsp": None, "size_bytes": 0,
                "image_path": self.image_path # Still useful to know what was attempted
            }

        return {
            "pixel_data": self.pixel_data,
            "width": self.width,
            "height": self.height,
            "pixel_format_gvsp": self.pixel_format_gvsp,
            "size_bytes": self.file_size_bytes,
            "image_path": self.image_path
        }

if __name__ == '__main__':
    # Example Usage for direct testing of this module
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Starting StaticImageSource direct test run...")

    # Create a dummy sample image for testing if one doesn't exist
    dummy_file = "dummy_mono8_sample_loader_test.png"
    try:
        dummy_image = Image.new('L', (32, 16), color='darkgray') # Small test image
        dummy_image.save(dummy_file)
        logger.debug(f"Created dummy image '{dummy_file}' for testing.")
    except Exception as e:
        logger.error(f"Could not create dummy image '{dummy_file}': {e}")

    source = StaticImageSource() # Initialize empty

    logger.info("--- Test loading non-existent file ---")
    source.load_image("non_existent_image.jpg")
    logger.debug(f"Frame info after failed load: {source.get_frame()}")

    logger.info(f"--- Test loading dummy image '{dummy_file}' (Mono8) ---")
    if source.load_image(dummy_file, "Mono8"):
        frame_info = source.get_frame()
        logger.debug(f"Frame Info: {frame_info}")
        if frame_info and frame_info["pixel_data"]:
            logger.debug(f"First 8 bytes of pixel data: {frame_info['pixel_data'][:8].hex(' ')}")
    else:
        logger.error(f"Failed to load '{dummy_file}'")

    # Clean up dummy image
    try:
        import os
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
            logger.debug(f"Cleaned up dummy image '{dummy_file}'.")
    except Exception as e:
        logger.error(f"Could not remove dummy image '{dummy_file}': {e}")
    logger.info("StaticImageSource direct test run finished.")
```
