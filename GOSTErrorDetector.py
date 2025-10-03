import cv2
import numpy as np
import easyocr
from ultralytics import YOLO


class GOSTErrorDetector:
    def __init__(self):
        # 1. Детектор объектов (YOLOv8)
        self.object_detector = YOLO('yolov8n.pt')

        # 2. OCR для текста (Tesseract/EasyOCR)
        self.ocr_reader = easyocr.Reader(['ru', 'en'])

        # 3. Классификатор для проверки штампа
        self.stamp_classifier = self._load_stamp_classifier()

    def detect_errors(self, image_path):
        """Комплексная проверка чертежа"""
        image = cv2.imread(image_path)
        errors = []

        # 1. Проверка основной надписи
        errors.extend(self._check_stamp(image))

        # 2. Проверка технических требований
        errors.extend(self._check_technical_requirements(image))

        # 3. Проверка размеров и допусков
        errors.extend(self._check_dimensions(image))

        # 4. Проверка обозначений
        errors.extend(self._check_designations(image))

        return errors

    def _check_stamp(self, image):
        """Проверка основной надписи"""
        errors = []
        h, w = image.shape[:2]

        # Вырезаем область штампа (правый нижний угол)
        stamp_region = image[int(h * 0.85):h, int(w * 0.70):w]

        # OCR для извлечения кода документа
        text_results = self.ocr_reader.readtext(stamp_region)

        # Проверка наличия кода (СБ, Э5, и т.д.)
        codes = ['СБ', 'ВО', 'ТЧ', 'ГЧ', 'МЭ', 'Э1', 'Э2', 'Э3', 'Э4', 'Э5']
        found_code = False

        for (bbox, text, prob) in text_results:
            if any(code in text for code in codes):
                found_code = True
                break

        if not found_code:
            errors.append({
                'type': 'missing_document_code',
                'severity': 'critical',
                'location': 'stamp'
            })

        return errors

    def _check_technical_requirements(self, image):
        """Проверка расположения технических требований"""
        errors = []
        h, w = image.shape[:2]

        # Ищем текст "Технические требования" или просто нумерацию "1. 2. 3."
        tt_region = image[int(h * 0.5):int(h * 0.85), int(w * 0.70):w]

        text_results = self.ocr_reader.readtext(tt_region)

        # Проверка ширины блока (должна быть ~185мм = ~25% ширины)
        for (bbox, text, prob) in text_results:
            if 'требования' in text.lower() or text.strip().startswith('1.'):
                x_min = min(pt[0] for pt in bbox)
                x_max = max(pt[0] for pt in bbox)
                width_ratio = (x_max - x_min) / w

                if width_ratio > 0.30:  # Больше 30% ширины
                    errors.append({
                        'type': 'wrong_tt_width',
                        'severity': 'medium',
                        'location': bbox
                    })

        return errors

    def _check_dimensions(self, image):
        """Проверка размеров в зоне 30°"""
        errors = []

        # Детекция линий
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                # Зона 30° (25-35°)
                if 25 <= angle <= 35:
                    # Проверка наличия полки (горизонтальная линия в конце)
                    has_shelf = self._detect_dimension_shelf(image, x2, y2)

                    if not has_shelf:
                        errors.append({
                            'type': 'dimension_30deg_violation',
                            'severity': 'medium',
                            'location': [x1, y1, x2, y2]
                        })

        return errors

    def _check_designations(self, image):
        """Проверка буквенных обозначений и звездочек"""
        errors = []

        # OCR всего изображения
        text_results = self.ocr_reader.readtext(image)

        # Поиск звездочек
        asterisks_found = sum(1 for (_, text, _) in text_results if '*' in text)

        if asterisks_found == 0:
            errors.append({
                'type': 'missing_asterisks',
                'severity': 'low',
                'location': 'drawing'
            })

        return errors

    def _load_stamp_classifier(self):
        """Загрузка классификатора штампа"""
        # Пока заглушка, потом можно обучить отдельную модель
        return None

    def _detect_dimension_shelf(self, image, x, y, radius=30):
        """Проверка наличия полки у размерной линии"""
        h, w = image.shape[:2]

        # Вырезаем область вокруг конца размерной линии
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        x2 = min(w, x + radius)
        y2 = min(h, y + radius)

        region = image[y1:y2, x1:x2]

        # Ищем горизонтальные линии (полка)
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 20, minLineLength=10, maxLineGap=5)

        if lines is not None:
            for line in lines:
                x1_line, y1_line, x2_line, y2_line = line[0]
                angle = abs(np.arctan2(y2_line - y1_line, x2_line - x1_line) * 180 / np.pi)

                # Если линия почти горизонтальная (±10°)
                if angle < 10 or angle > 170:
                    return True

        return False