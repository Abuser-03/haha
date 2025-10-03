# GOSTErrorDetector.py
import cv2
import numpy as np
from ultralytics import YOLO
import os


class GOSTErrorDetector:
    def __init__(self, model_path='models/best.pt'):
        """
        Инициализация детектора с обученной моделью
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"❌ Модель не найдена: {model_path}\n"
                f"💡 Обучите модель командой: python train_yolo.py"
            )

        print(f"📥 Загрузка модели: {model_path}")
        self.model = YOLO(model_path)

        # Мапинг классов
        self.class_to_error = {
            0: {'type': 'missing_stamp', 'severity': 'critical',
                'description': 'Отсутствует основная надпись'},
            1: {'type': 'wrong_document_code', 'severity': 'high',
                'description': 'Неправильный код документа'},
            2: {'type': 'code_name_mismatch', 'severity': 'high',
                'description': 'Несоответствие кода и наименования'},
            3: {'type': 'wrong_tt_position', 'severity': 'medium',
                'description': 'ТТ не над основной надписью'},
            4: {'type': 'missing_letter_designation', 'severity': 'medium',
                'description': 'Отсутствует буквенное обозначение'},
            5: {'type': 'missing_asterisks', 'severity': 'low',
                'description': 'Отсутствуют * на чертеже'},
            6: {'type': 'dimension_30deg_violation', 'severity': 'medium',
                'description': 'Размер в зоне 30° без полки'},
            7: {'type': 'missing_tolerance_arrow', 'severity': 'high',
                'description': 'Отсутствует стрелка в допуске'},
            8: {'type': 'missing_general_roughness', 'severity': 'medium',
                'description': 'Отсутствует √ в углу чертежа'}
        }

    def detect_errors(self, image_path, conf_threshold=0.25):
        """
        Детекция ошибок на чертеже

        Args:
            image_path: путь к изображению
            conf_threshold: порог уверенности (0.0-1.0)

        Returns:
            list: список найденных ошибок
        """
        print(f"🔍 Анализ: {os.path.basename(image_path)}")

        # Запускаем inference
        results = self.model(image_path, conf=conf_threshold, verbose=False)[0]

        errors = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            error_info = self.class_to_error.get(class_id, {})

            errors.append({
                'type': error_info.get('type', 'unknown'),
                'severity': error_info.get('severity', 'medium'),
                'description': error_info.get('description', ''),
                'confidence': round(confidence, 3),
                'bbox': {
                    'x': int(bbox[0]),
                    'y': int(bbox[1]),
                    'width': int(bbox[2] - bbox[0]),
                    'height': int(bbox[3] - bbox[1])
                },
                'location': 'drawing'
            })

        print(f"   Найдено ошибок: {len(errors)}")
        return errors

    def visualize_errors(self, image_path, output_path='result.png', conf_threshold=0.25):
        """
        Визуализация найденных ошибок
        """
        results = self.model(image_path, conf=conf_threshold)[0]
        annotated = results.plot()  # Автоматическая аннотация
        cv2.imwrite(output_path, annotated)
        print(f"✅ Визуализация сохранена: {output_path}")
        return output_path


# Тестирование
if __name__ == '__main__':
    import sys

    if not os.path.exists('models/best.pt'):
        print("❌ Модель не найдена!")
        print("💡 Сначала обучите модель: python train_yolo.py")
        sys.exit(1)

    # Тестируем детектор
    detector = GOSTErrorDetector()

    # Найдём тестовое изображение
    test_images = [
        'data/dataset/val/images',
        'data/generated_errors/images'
    ]

    test_img = None
    for folder in test_images:
        if os.path.exists(folder):
            imgs = [f for f in os.listdir(folder) if f.endswith('.png')]
            if imgs:
                test_img = os.path.join(folder, imgs[0])
                break

    if test_img:
        print(f"\n🧪 Тест на изображении: {test_img}\n")
        errors = detector.detect_errors(test_img, conf_threshold=0.3)

        if errors:
            print(f"\n❌ Найдено {len(errors)} ошибок:")
            for i, err in enumerate(errors, 1):
                print(f"   {i}. {err['type']} ({err['severity']}) - уверенность: {err['confidence']:.1%}")
        else:
            print("\n✅ Ошибок не обнаружено")

        # Визуализация
        detector.visualize_errors(test_img, 'test_result.png')
    else:
        print("⚠️  Тестовые изображения не найдены")