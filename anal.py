import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import config

# Используем пути из config
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


def analyze_document(pdf_path):
    """Анализ документа"""
    pages = convert_from_path(
        pdf_path,
        dpi=config.PDF_DPI,
        poppler_path=config.POPPLER_PATH
    )

    image = np.array(pages[0])
    h, w, _ = image.shape
    crop = image[int(h * 0.75):, int(w * 0.75):]

    vis = crop.copy()
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

    data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 0:
            (x, y, w_box, h_box) = (
                data['left'][i],
                data['top'][i],
                data['width'][i],
                data['height'][i]
            )
            cv2.rectangle(vis, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)

    text = pytesseract.image_to_string(gray, lang='rus')

    return {
        'text': text,
        'visualization': vis
    }