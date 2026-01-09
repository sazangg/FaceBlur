from face_blur.services.blur_service import process_image_blur

if __name__ == "__main__":
    with open(".examples/sample_img.jpg", "rb") as f:
        image_bytes = f.read()

    blurred_bytes = process_image_blur(image_bytes)

    with open(".examples/blurred_image.jpg", "wb") as f:
        f.write(blurred_bytes)
