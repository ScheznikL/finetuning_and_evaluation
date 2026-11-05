def process_canny(image_path):
    import cv2
    from PIL import Image
    import numpy as np
    from diffusers.utils import load_image

    image = load_image(image_path)

    image = np.array(image)

    low_threshold = 100
    high_threshold = 200

    image = cv2.Canny(image, low_threshold, high_threshold)
    image = image[:, :, None]
    image = np.concatenate([image, image, image], axis=2)
    canny_image = Image.fromarray(image)
    canny_image.save("./tmpcanny.png")
    
    return canny_image