# train_yolo.py
from ultralytics import YOLO
import torch
import os


def train_gost_detector():
    """
    Обучение YOLOv8 для детекции ошибок ГОСТ
    """
    print("\n" + "=" * 60)
    print("🧠 ОБУЧЕНИЕ YOLO ДЛЯ ДЕТЕКЦИИ ОШИБОК ГОСТ")
    print("=" * 60 + "\n")

    # Проверяем наличие data.yaml
    if not os.path.exists('data.yaml'):
        print("❌ Файл data.yaml не найден!")
        print("💡 Создайте data.yaml с конфигурацией датасета")
        return

    # Проверяем GPU
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🖥️  Устройство: {device}")

    if device == 'cpu':
        print("⚠️  GPU не обнаружен, обучение будет медленным")
        print("💡 Для ускорения используйте Google Colab с GPU\n")

    # Загружаем предобученную модель
    print("📥 Загрузка базовой модели YOLOv8...")
    model = YOLO('yolov8n.pt')  # nano - самая быстрая

    print("\n🚀 Начинаем обучение...\n")

    # Обучаем
    results = model.train(
        data='data.yaml',
        epochs=50,  # Для начала 50 эпох (можно увеличить до 100)
        imgsz=640,  # Размер входного изображения
        batch=8,  # Batch size (уменьшите до 4 если мало RAM)
        patience=15,  # Early stopping после 15 эпох без улучшения
        device=device,

        # Аугментации (подходят для чертежей)
        hsv_h=0.0,  # Отключаем изменение цвета
        hsv_s=0.0,
        hsv_v=0.0,
        degrees=0.0,  # Не поворачиваем чертежи
        translate=0.1,  # Небольшие сдвиги
        scale=0.1,  # Небольшое масштабирование
        flipud=0.0,  # Не переворачиваем
        fliplr=0.0,
        mosaic=0.5,  # Мозаика

        # Сохранение
        project='runs/gost_detector',
        name='exp',
        exist_ok=True,
        save=True,
        save_period=10,  # Сохранять каждые 10 эпох

        # Визуализация
        plots=True,
        verbose=True
    )

    print("\n" + "=" * 60)
    print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    print("=" * 60)
    print(f"📁 Результаты: {results.save_dir}")
    print(f"🎯 Лучшая модель: {results.save_dir}/weights/best.pt")
    print("=" * 60 + "\n")

    # Валидация на тестовой выборке
    print("📊 Валидация модели...\n")
    metrics = model.val()

    print("\n" + "=" * 60)
    print("📈 МЕТРИКИ:")
    print("=" * 60)
    print(f"mAP50: {metrics.box.map50:.3f}")
    print(f"mAP50-95: {metrics.box.map:.3f}")
    print("=" * 60 + "\n")

    # Копируем лучшую модель в папку models
    import shutil
    os.makedirs('models', exist_ok=True)
    best_model_path = f"{results.save_dir}/weights/best.pt"
    shutil.copy(best_model_path, 'models/best.pt')
    print(f"✅ Лучшая модель скопирована в: models/best.pt\n")

    return results


if __name__ == '__main__':
    # Проверяем датасет
    if not os.path.exists('data/dataset/train'):
        print("❌ Датасет не найден!")
        print("💡 Сначала запустите:")
        print("   1. python generate_dataset.py")
        print("   2. python split_dataset.py\n")
        exit(1)

    # Считаем количество изображений
    train_imgs = len([f for f in os.listdir('data/dataset/train/images') if f.endswith('.png')])
    val_imgs = len([f for f in os.listdir('data/dataset/val/images') if f.endswith('.png')])

    print(f"\n📊 Датасет:")
    print(f"   Train: {train_imgs} изображений")
    print(f"   Val: {val_imgs} изображений")
    print(f"   Всего: {train_imgs + val_imgs}\n")

    response = input("❓ Начать обучение? (y/n): ")

    if response.lower() not in ['y', 'yes', 'д', 'да']:
        print("⏭️  Отменено")
        exit(0)

    train_gost_detector()