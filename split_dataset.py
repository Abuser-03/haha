# split_dataset.py
import os
import shutil
from sklearn.model_selection import train_test_split
from tqdm import tqdm


def split_dataset(source_folder, output_folder, val_split=0.2):
    """
    Разделяет датасет на train/val (80/20)
    """
    images_folder = os.path.join(source_folder, 'images')
    labels_folder = os.path.join(source_folder, 'labels')

    # Получаем список всех изображений
    all_images = [f for f in os.listdir(images_folder) if f.endswith('.png')]

    if not all_images:
        print(f"❌ Нет изображений в {images_folder}")
        return

    print(f"📊 Всего изображений: {len(all_images)}")

    # Разделяем 80/20
    train_images, val_images = train_test_split(
        all_images,
        test_size=val_split,
        random_state=42
    )

    print(f"📈 Train: {len(train_images)} изображений")
    print(f"📉 Val: {len(val_images)} изображений\n")

    # Создаём структуру
    for split, images in [('train', train_images), ('val', val_images)]:
        print(f"📁 Копирование {split}...")

        os.makedirs(f"{output_folder}/{split}/images", exist_ok=True)
        os.makedirs(f"{output_folder}/{split}/labels", exist_ok=True)

        for img in tqdm(images, desc=split):
            # Копируем изображение
            shutil.copy(
                os.path.join(images_folder, img),
                f"{output_folder}/{split}/images/{img}"
            )

            # Копируем аннотацию
            label_file = img.replace('.png', '.txt')
            label_path = os.path.join(labels_folder, label_file)

            if os.path.exists(label_path):
                shutil.copy(
                    label_path,
                    f"{output_folder}/{split}/labels/{label_file}"
                )
            else:
                # Если нет аннотации, создаём пустой файл
                open(f"{output_folder}/{split}/labels/{label_file}", 'w').close()

    print("\n" + "=" * 60)
    print("✅ Датасет разделён на train/val!")
    print("=" * 60)
    print(f"📁 Train: {output_folder}/train/")
    print(f"📁 Val: {output_folder}/val/")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("📊 РАЗДЕЛЕНИЕ ДАТАСЕТА НА TRAIN/VAL")
    print("=" * 60 + "\n")

    split_dataset(
        source_folder='./data/generated_errors',
        output_folder='./data/dataset',
        val_split=0.2  # 20% на валидацию
    )

    print("📋 Следующий шаг: создайте data.yaml")