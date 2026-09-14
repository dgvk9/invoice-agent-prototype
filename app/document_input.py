import base64
import mimetypes
from pathlib import Path

import fitz


IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp"
}


def file_to_data_url(file_path):
    file_path = Path(file_path)

    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type is None:
        mime_type = "image/png"

    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def pdf_to_images(file_path):
    document = fitz.open(file_path)

    images = []

    # Prototype limit: first 5 pages
    for page_number in range(min(len(document), 5)):

        page = document[page_number]

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        image_bytes = pix.tobytes("png")

        encoded = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        images.append(
            f"data:image/png;base64,{encoded}"
        )

    document.close()

    return images


def extract_pdf_text(file_path):
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text() + "\n"

    document.close()

    return text.strip()


def build_document_content(file_path, instructions):

    extension = Path(file_path).suffix.lower()

    # Normal text-based PDF
    if extension == ".pdf":

        text = extract_pdf_text(file_path)

        # If enough text exists, use it.
        if len(text) > 50:

            return [
                {
                    "type": "input_text",
                    "text": (
                        instructions
                        + "\n\nDOCUMENT TEXT:\n"
                        + text
                    )
                }
            ]

        # Otherwise treat PDF as a scan
        images = pdf_to_images(file_path)

        content = [
            {
                "type": "input_text",
                "text": instructions
            }
        ]

        for image in images:
            content.append({
                "type": "input_image",
                "image_url": image
            })

        return content

    # PNG/JPG/etc.
    if extension in IMAGE_EXTENSIONS:

        return [
            {
                "type": "input_text",
                "text": instructions
            },
            {
                "type": "input_image",
                "image_url": file_to_data_url(file_path)
            }
        ]

    raise ValueError(
        f"Unsupported file type: {extension}"
    )