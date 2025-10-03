from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import random

class GOSTErrorGenerator:
    """Генератор ошибок согласно вашим требованиям"""

    def __init__(self, image_path):
        self.image = Image.open(image_path)
        self.img_cv = cv2.cvtColor(np.array(self.image), cv2.COLOR_RGB2BGR)
        self.width, self.height = self.image.size

    # ====== 1. ОШИБКИ ОСНОВНОЙ НАДПИСИ ======

    def remove_stamp(self):
        """Удаляет основную надпись (правый нижний угол)"""
        # Типовой размер штампа по ГОСТ 2.104
        stamp_width = int(self.width * 0.25)  # ~185мм
        stamp_height = int(self.height * 0.15)  # ~55мм

        x = self.width - stamp_width
        y = self.height - stamp_height

        draw = ImageDraw.Draw(self.image)
        draw.rectangle([x, y, self.width, self.height], fill='white')

        return {
            'type': 'missing_stamp',
            'bbox': [x, y, stamp_width, stamp_height],
            'severity': 'critical'
        }

    def corrupt_document_code(self):
        """Искажает код документа в штампе (СБ → XX)"""
        # Находим область с кодом (обычно верхняя часть штампа)
        stamp_x = int(self.width * 0.75)
        stamp_y = int(self.height * 0.87)

        # Закрашиваем область с кодом
        draw = ImageDraw.Draw(self.image)
        draw.rectangle(
            [stamp_x, stamp_y, stamp_x + 100, stamp_y + 30],
            fill='white'
        )

        # Пишем неправильный код
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        draw.text((stamp_x + 10, stamp_y + 5), "XX", fill='black', font=font)

        return {
            'type': 'wrong_document_code',
            'bbox': [stamp_x, stamp_y, 100, 30],
            'severity': 'high'
        }

    # ====== 2. ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ ======

    def misplace_technical_requirements(self):
        """Перемещает ТТ не над основной надписью"""
        # Типичное расположение ТТ - над штампом
        # Перемещаем их в другое место

        tt_area_x = int(self.width * 0.75)
        tt_area_y = int(self.height * 0.60)  # Правильное положение

        # Закрашиваем правильное положение
        draw = ImageDraw.Draw(self.image)
        draw.rectangle(
            [tt_area_x, tt_area_y, self.width - 10, tt_area_y + 150],
            fill='white'
        )

        # Рисуем ТТ в неправильном месте (слева)
        wrong_x = 50
        wrong_y = 50
        draw.text((wrong_x, wrong_y), "1. Технические требования...", fill='black')

        return {
            'type': 'wrong_tt_position',
            'bbox': [wrong_x, wrong_y, 200, 100],
            'severity': 'medium'
        }

    def remove_letter_designation(self):
        """Удаляет буквенное обозначение с чертежа"""
        # Случайная позиция, где может быть обозначение (например, "А")
        x = random.randint(100, self.width - 200)
        y = random.randint(100, self.height - 300)

        # Закрашиваем область
        draw = ImageDraw.Draw(self.image)
        draw.ellipse([x, y, x + 40, y + 40], fill='white')

        return {
            'type': 'missing_letter_designation',
            'bbox': [x, y, 40, 40],
            'severity': 'high'
        }

    def remove_asterisk(self):
        """Удаляет *, **, *** с поля чертежа"""
        # Находим и удаляем символы звездочек
        positions = self._find_asterisks()

        draw = ImageDraw.Draw(self.image)
        for pos in positions[:random.randint(1, 3)]:
            x, y = pos
            draw.rectangle([x - 5, y - 5, x + 20, y + 20], fill='white')

        return {
            'type': 'missing_asterisks',
            'bbox': positions,
            'severity': 'medium'
        }

    # ====== 3. РАЗМЕРЫ В ЗОНЕ 30° ======

    def create_30deg_violation(self):
        """Создает размер в зоне 30° без полки"""
        # Ищем размерные линии под углом ~30°
        gray = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

                # Если линия в зоне 30° (±5°)
                if 25 <= angle <= 35:
                    # Удаляем полку (если есть)
                    cv2.line(self.img_cv, (x2, y2), (x2 + 30, y2), (255, 255, 255), 3)

                    self.image = Image.fromarray(cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2RGB))

                    return {
                        'type': 'dimension_30deg_violation',
                        'bbox': [x1, y1, abs(x2 - x1), abs(y2 - y1)],
                        'severity': 'medium'
                    }

        return None

    # ====== 4. ДОПУСКИ ФОРМЫ ======

    def remove_tolerance_arrow(self):
        """Удаляет дополнительную стрелку в допуске формы"""
        # Ищем прямоугольные рамки допусков
        tolerance_frames = self._find_tolerance_frames()

        if tolerance_frames:
            frame = random.choice(tolerance_frames)
            x, y, w, h = frame

            # Удаляем стрелку рядом с рамкой
            cv2.rectangle(self.img_cv, (x + w, y), (x + w + 30, y + h), (255, 255, 255), -1)
            self.image = Image.fromarray(cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2RGB))

            return {
                'type': 'missing_tolerance_arrow',
                'bbox': [x + w, y, 30, h],
                'severity': 'high'
            }

        return None

    # ====== 5. ШЕРОХОВАТОСТЬ ======

    def remove_general_roughness_mark(self):
        """Удаляет знак √ в скобках в углу чертежа"""
        # Обычно в правом верхнем углу
        corner_x = self.width - 100
        corner_y = 50

        draw = ImageDraw.Draw(self.image)
        draw.rectangle([corner_x, corner_y, corner_x + 80, corner_y + 60], fill='white')

        return {
            'type': 'missing_general_roughness',
            'bbox': [corner_x, corner_y, 80, 60],
            'severity': 'medium'
        }

    # ====== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ======

    def _find_asterisks(self):
        """Находит позиции звездочек на чертеже"""
        # Упрощенная версия - случайные позиции
        # В реальности нужно OCR
        return [
            (random.randint(100, self.width - 100), random.randint(100, self.height - 100))
            for _ in range(random.randint(2, 5))
        ]

    def _find_tolerance_frames(self):
        """Находит рамки допусков на чертеже"""
        gray = cv2.cvtColor(self.img_cv, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frames = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Рамки обычно прямоугольные, ~3:1 соотношение
            if 50 < w < 200 and 15 < h < 40 and 2 < w / h < 5:
                frames.append((x, y, w, h))

        return frames

    def save(self, output_path):
        """Сохраняет модифицированное изображение"""
        self.image.save(output_path)