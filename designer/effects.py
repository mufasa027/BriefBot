from PIL import Image


def dark_gradient(height, width):

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0),
    )

    pixels = overlay.load()

    for y in range(height):

        alpha = int(
            255 * (y / height) * 0.85
        )

        for x in range(width):
            pixels[x, y] = (
                0,
                0,
                0,
                alpha,
            )

    return overlay