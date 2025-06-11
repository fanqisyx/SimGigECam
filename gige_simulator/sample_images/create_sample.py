from PIL import Image, ImageDraw
import logging
import os

# Configure basic logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_image(save_path="sample_image.png", width=64, height=64, img_format="PNG"):
    """
    Creates a simple grayscale image with some patterns for testing.
    """
    try:
        img = Image.new('L', (width, height), color='gray') # Grayscale
        draw = ImageDraw.Draw(img)

        # Draw patterns
        draw.line([(0, 0), (width - 1, height - 1)], fill='white', width=2) # White diagonal
        draw.line([(0, height -1), (width -1, 0)], fill='black', width=1)   # Black diagonal (X)
        draw.line([(width//2, 0), (width//2, height-1)], fill=100, width=1) # Vertical gray line
        draw.line([(0, height//2), (width-1, height//2)], fill=200, width=1) # Horizontal light gray line

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        img.save(save_path, img_format)
        logger.info(f"Sample image saved to {save_path} (Format: {img_format}, Size: {width}x{height})")
    except Exception as e:
        logger.error(f"Error creating sample image at {save_path}: {e}", exc_info=True)

def create_rgb_sample_image(save_path="sample_rgb.png", width=32, height=32, img_format="PNG"):
    """
    Creates a simple RGB image.
    """
    try:
        img_rgb = Image.new('RGB', (width, height), color='blue')
        draw_rgb = ImageDraw.Draw(img_rgb)
        draw_rgb.rectangle([(width//4, width//4), (width*3//4, height*3//4)], fill='red')

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        img_rgb.save(save_path, img_format)
        logger.info(f"Sample RGB image saved to {save_path} (Format: {img_format}, Size: {width}x{height})")
    except Exception as e:
        logger.error(f"Error creating sample RGB image at {save_path}: {e}", exc_info=True)


if __name__ == "__main__":
    # Base path for saving images, assumes script is run from project root or /app
    base_save_dir = "gige_simulator/sample_images"

    create_sample_image(save_path=os.path.join(base_save_dir, "sample_image.png"))
    create_sample_image(save_path=os.path.join(base_save_dir, "sample_image.jpeg"), img_format="JPEG")
    create_sample_image(save_path=os.path.join(base_save_dir, "sample_image_large.png"), width=128, height=96)

    create_rgb_sample_image(save_path=os.path.join(base_save_dir, "sample_rgb.png"))
    create_rgb_sample_image(save_path=os.path.join(base_save_dir, "sample_rgb_small.jpeg"), width=16, height=16, img_format="JPEG")

    logger.info("Sample image creation script finished.")
