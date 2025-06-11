from PIL import Image, ImageDraw

def create_sample_image(path="sample_image.png", width=64, height=64, format="PNG"):
    """
    Creates a simple grayscale image with a diagonal line for testing.
    """
    try:
        # Create a grayscale image
        img = Image.new('L', (width, height), color='gray')
        draw = ImageDraw.Draw(img)

        # Draw a white diagonal line
        draw.line([(0, 0), (width - 1, height - 1)], fill='white', width=2)
        # Draw a black X
        draw.line([(0, height -1), (width -1, 0)], fill='black', width=1)
        draw.line([(width//2, 0), (width//2, height-1)], fill=100, width=1) # vertical line
        draw.line([(0, height//2), (width-1, height//2)], fill=200, width=1) # horizontal line


        img.save(path, format)
        print(f"Sample image saved to {path} (Format: {format}, Size: {width}x{height})")
    except Exception as e:
        print(f"Error creating sample image: {e}")

if __name__ == "__main__":
    # The script will be run from /app directory, so path should be relative to that
    create_sample_image(path="gige_simulator/sample_images/sample_image.png")
    create_sample_image(path="gige_simulator/sample_images/sample_image.jpeg", format="JPEG") # Also a JPEG version
    create_sample_image(path="gige_simulator/sample_images/sample_image_rgb.png", width=80, height=60) # A slightly different one

    # Create an RGB image for future testing
    img_rgb = Image.new('RGB', (32, 32), color='blue')
    draw_rgb = ImageDraw.Draw(img_rgb)
    draw_rgb.rectangle([(8,8), (24,24)], fill='red')
    img_rgb.save("gige_simulator/sample_images/sample_rgb.png", "PNG")
    print("Sample RGB image 'sample_rgb.png' created.")
