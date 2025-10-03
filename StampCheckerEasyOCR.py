import easyocr
import numpy as np
from pdf2image import convert_from_path

from anal import poppler_path


class StampCheckerEasyOCR:
    def __init__(self, pdf_path, dpi=300):
        pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
        self.image = np.array(pages[0])
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False)

    def extract_text_easyocr(self, crop):
        """EasyOCR часто работает лучше Tesseract для русского"""
        results = self.reader.readtext(crop)

        formatted_results = []
        for (bbox, text, conf) in results:
            # bbox = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            x_coords = [pt[0] for pt in bbox]
            y_coords = [pt[1] for pt in bbox]

            x = int(min(x_coords))
            y = int(min(y_coords))
            w = int(max(x_coords) - x)
            h = int(max(y_coords) - y)

            formatted_results.append({
                'text': text,
                'conf': int(conf * 100),
                'bbox': (x, y, w, h)
            })

        return formatted_results