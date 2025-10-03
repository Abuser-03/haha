
import os
import json
from GOSTErrorGenerator import GOSTErrorGenerator
from tqdm import tqdm
import random
import shutil


def generate_balanced_dataset(clean_images_folder, output_folder,
                              errors_per_variant=2, variants_per_image=1):
    """
    Генерирует сбалансированный датасет:
    - 50% корректных изображений (без ошибок)
    - 50% изображений с ошибками
    """
    os.makedirs(f"{output_folder}/images", exist_ok=True)
    os.makedirs(f"{output_folder}/labels", exist_ok=True)

    clean_images = [f for f in os.listdir(clean_images_folder) if f.endswith('.png')]

    if not clean_images:
        print("❌ Не найдено PNG файлов в", clean_images_folder)
        return

    print(f"📊 Найдено {len(clean_images)} корректных изображений")
    print(f"📋 Генерируем сбалансированный датасет:\n")

    # Мапинг типов ошибок в классы YOLO
    error_to_class = {
        'missing_stamp': 0,
        'wrong_document_code': 1,
        'code_name_mismatch': 2,
        'wrong_tt_position': 3,
        'missing_letter_designation': 4,
        'missing_asterisks': 5,
        'dimension_30deg_violation': 6,
        'missing_tolerance_arrow': 7,
        'missing_general_roughness': 8
    }

    annotations = []
    stats = {
        'clean': 0,
        'with_errors': 0,
        'total_errors': 0,
        'errors_by_type': {k: 0 for k in error_to_class.keys()}
    }

    # ========== 1. КОПИРУЕМ КОРРЕКТНЫЕ ИЗОБРАЖЕНИЯ (50%) ==========
    print("=" * 60)
    print("1️⃣  КОПИРОВАНИЕ КОРРЕКТНЫХ ИЗОБРАЖЕНИЙ (без ошибок)")
    print("=" * 60)

    for img_name in tqdm(clean_images, desc="Корректные"):
        img_path = os.path.join(clean_images_folder, img_name)

        # Копируем оригинал как есть
        output_name = f"clean_{img_name}"
        output_path = os.path.join(output_folder, 'images', output_name)
        shutil.copy2(img_path, output_path)

        # Создаём ПУСТУЮ аннотацию (нет ошибок = пустой .txt файл)
        label_path = os.path.join(output_folder, 'labels', f"{output_name[:-4]}.txt")
        open(label_path, 'w').close()  # Пустой файл

        annotations.append({
            'image': output_name,
            'errors': [],
            'is_clean': True
        })

        stats['clean'] += 1

    print(f"\n✅ Скопировано {stats['clean']} корректных изображений\n")

    # ========== 2. ГЕНЕРИРУЕМ ИЗОБРАЖЕНИЯ С ОШИБКАМИ (50%) ==========
    print("=" * 60)
    print("2️⃣  ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ С ОШИБКАМИ")
    print("=" * 60)

    for img_name in tqdm(clean_images, desc="С ошибками"):
        img_path = os.path.join(clean_images_folder, img_name)

        # Для каждого изображения создаём несколько вариантов с ошибками
        for variant in range(variants_per_image):
            try:
                generator = GOSTErrorGenerator(img_path)

                # Все доступные методы генерации ошибок
                error_methods = [
                    ('remove_stamp', generator.remove_stamp),
                    ('corrupt_document_code', generator.corrupt_document_code),
                    ('misplace_technical_requirements', generator.misplace_technical_requirements),
                    ('remove_letter_designation', generator.remove_letter_designation),
                    ('remove_asterisk', generator.remove_asterisk),
                    ('create_30deg_violation', generator.create_30deg_violation),
                    ('remove_tolerance_arrow', generator.remove_tolerance_arrow),
                    ('remove_general_roughness_mark', generator.remove_general_roughness_mark)
                ]

                # Случайно выбираем 1-3 типа ошибок
                num_errors = random.randint(1, min(errors_per_variant, len(error_methods)))
                selected_errors = random.sample(error_methods, num_errors)

                image_annotations = []
                output_name = f"error_{img_name[:-4]}_v{variant}.png"

                # Применяем выбранные ошибки
                for error_name, error_func in selected_errors:
                    error_info = error_func()

                    if error_info:
                        image_annotations.append({
                            'class': error_to_class.get(error_info['type'], 0),
                            'bbox': error_info['bbox'],
                            'type': error_info['type'],
                            'severity': error_info['severity']
                        })

                        stats['total_errors'] += 1
                        stats['errors_by_type'][error_info['type']] += 1

                # Сохраняем изображение
                output_path = os.path.join(output_folder, 'images', output_name)
                generator.save(output_path)

                # Сохраняем YOLO-аннотацию (если есть ошибки)
                if image_annotations:
                    save_yolo_annotation(
                        image_annotations,
                        generator.width,
                        generator.height,
                        os.path.join(output_folder, 'labels', f"{output_name[:-4]}.txt")
                    )

                    annotations.append({
                        'image': output_name,
                        'errors': image_annotations,
                        'is_clean': False
                    })

                    stats['with_errors'] += 1
                else:
                    # Если ошибки не создались, создаём пустой .txt
                    label_path = os.path.join(output_folder, 'labels', f"{output_name[:-4]}.txt")
                    open(label_path, 'w').close()

            except Exception as e:
                print(f"\n⚠️  Ошибка при обработке {img_name}: {e}")
                continue

    # ========== 3. СОХРАНЯЕМ ОБЩУЮ СТАТИСТИКУ ==========
    print(f"\n{'=' * 60}")
    print("📊 СТАТИСТИКА ДАТАСЕТА")
    print("=" * 60)
    print(f"✅ Корректных изображений: {stats['clean']}")
    print(f"❌ Изображений с ошибками: {stats['with_errors']}")
    print(f"📈 Всего изображений: {stats['clean'] + stats['with_errors']}")
    print(f"🔍 Всего ошибок: {stats['total_errors']}")
    print(f"\n📋 Ошибки по типам:")
    for error_type, count in sorted(stats['errors_by_type'].items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"   • {error_type}: {count}")
    print("=" * 60)

    # Сохраняем JSON с аннотациями
    with open(f"{output_folder}/annotations.json", 'w', encoding='utf-8') as f:
        json.dump({
            'statistics': stats,
            'annotations': annotations
        }, f, ensure_ascii=False, indent=2)

    # Сохраняем статистику отдельно
    with open(f"{output_folder}/dataset_stats.txt", 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("СТАТИСТИКА ДАТАСЕТА\n")
        f.write("=" * 60 + "\n")
        f.write(f"Корректных изображений: {stats['clean']}\n")
        f.write(f"Изображений с ошибками: {stats['with_errors']}\n")
        f.write(f"Всего изображений: {stats['clean'] + stats['with_errors']}\n")
        f.write(f"Всего ошибок: {stats['total_errors']}\n")
        f.write(f"\nОшибки по типам:\n")
        for error_type, count in sorted(stats['errors_by_type'].items(), key=lambda x: -x[1]):
            if count > 0:
                f.write(f"  {error_type}: {count}\n")

    print(f"\n✅ Датасет сохранён в: {output_folder}")
    print(f"📄 Статистика: {output_folder}/dataset_stats.txt")
    print(f"📄 Аннотации: {output_folder}/annotations.json\n")

    return annotations


def save_yolo_annotation(annotations, img_width, img_height, output_path):
    """
    Сохраняет аннотацию в формате YOLO:
    <class_id> <x_center> <y_center> <width> <height> (нормализованные 0-1)
    """
    with open(output_path, 'w') as f:
        for ann in annotations:
            class_id = ann['class']
            bbox = ann['bbox']

            # Конвертируем [x, y, w, h] → нормализованные координаты центра
            x_center = (bbox[0] + bbox[2] / 2) / img_width
            y_center = (bbox[1] + bbox[3] / 2) / img_height
            width = bbox[2] / img_width
            height = bbox[3] / img_height

            # YOLO формат: class x_center y_center width height
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🎨 ГЕНЕРАТОР СБАЛАНСИРОВАННОГО ДАТАСЕТА")
    print("=" * 60 + "\n")

    # Параметры
    CLEAN_IMAGES = './data/original_clean'
    OUTPUT_FOLDER = './data/generated_errors'

    # Проверяем наличие исходных изображений
    if not os.path.exists(CLEAN_IMAGES):
        print(f"❌ Папка не найдена: {CLEAN_IMAGES}")
        print(f"💡 Создайте папку и скопируйте туда PNG чертежи")
        exit(1)

    num_images = len([f for f in os.listdir(CLEAN_IMAGES) if f.endswith('.png')])

    if num_images == 0:
        print(f"❌ В папке {CLEAN_IMAGES} нет PNG файлов")
        exit(1)

    print(f"📁 Найдено изображений: {num_images}")
    print(f"📊 Будет создано:")
    print(f"   • {num_images} корректных (без ошибок)")
    print(f"   • {num_images} с ошибками (1-3 ошибки на изображение)")
    print(f"   • Итого: ~{num_images * 2} изображений\n")

    response = input("❓ Начать генерацию? (y/n): ")

    if response.lower() not in ['y', 'yes', 'д', 'да']:
        print("⏭️  Отменено")
        exit(0)

    print("\n🚀 Начинаем генерацию...\n")

    # Генерируем датасет
    generate_balanced_dataset(
        clean_images_folder=CLEAN_IMAGES,
        output_folder=OUTPUT_FOLDER,
        errors_per_variant=2,  # 1-2 ошибки на изображение
        variants_per_image=1  # 1 вариант = будет 80 корректных + 80 с ошибками = 160 всего
    )

    print("\n" + "=" * 60)
    print("🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"\n📋 Следующий шаг:")
    print(f"   python split_dataset.py")
    print("=" * 60 + "\n")