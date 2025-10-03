from GOSTErrorDetector import GOSTErrorDetector


def main_pipeline(pdf_folder):
    """
    Полный пайплайн обработки чертежей
    """

    # 1. Конвертация PDF → PNG
    print("📄 Шаг 1: Конвертация PDF в изображения...")
    convert_pdfs_to_images(pdf_folder, 'images_clean/', dpi=300)

    # 2. Генерация синтетических ошибок
    print("\n⚙️ Шаг 2: Генерация датасета с ошибками...")
    generate_gost_dataset('images_clean/', 'dataset_errors/', 'annotations.json')

    # 3. Обучение модели
    print("\n🧠 Шаг 3: Обучение модели...")
    # (здесь код обучения YOLOv8)

    # 4. Проверка новых чертежей
    print("\n🔍 Шаг 4: Проверка чертежей...")
    detector = GOSTErrorDetector()

    for pdf in os.listdir(pdf_folder):
        if pdf.endswith('.pdf'):
            # Конвертируем
            images = convert_from_path(os.path.join(pdf_folder, pdf))

            # Проверяем каждую страницу
            for i, img in enumerate(images):
                img.save(f'temp_page_{i}.png')
                errors = detector.detect_errors(f'temp_page_{i}.png')

                if errors:
                    print(f"\n❌ {pdf} - страница {i + 1}:")
                    for error in errors:
                        print(f"  • {error['type']} (важность: {error['severity']})")
                else:
                    print(f"\n✅ {pdf} - страница {i + 1}: ошибок не найдено")


# Запуск
main_pipeline('your_pdfs/')