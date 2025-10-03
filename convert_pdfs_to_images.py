import os
from pdf2image import convert_from_path
from pathlib import Path


def convert_pdfs_to_images_recursive(root_folder, output_folder, dpi=300, poppler_path=None):
    """Рекурсивная конвертация всех PDF в папке и подпапках в PNG"""
    os.makedirs(output_folder, exist_ok=True)

    # Проверяем существование папки
    if not os.path.exists(root_folder):
        print(f"❌ Папка не найдена: {root_folder}")
        return

    # Ищем все PDF файлы рекурсивно
    pdf_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"⚠️ В папке {root_folder} не найдено PDF файлов")
        return

    print(f"📁 Найдено {len(pdf_files)} PDF файлов в {root_folder}")
    print(f"📂 Результаты будут сохранены в: {output_folder}\n")

    total_pages = 0
    successful_files = 0
    failed_files = 0

    for idx, pdf_path in enumerate(pdf_files, 1):
        # Получаем относительный путь для сохранения структуры папок
        rel_path = os.path.relpath(pdf_path, root_folder)
        rel_dir = os.path.dirname(rel_path)
        filename = os.path.basename(pdf_path)

        # Создаем подпапку в выходной директории
        if rel_dir:
            output_subfolder = os.path.join(output_folder, rel_dir)
            os.makedirs(output_subfolder, exist_ok=True)
        else:
            output_subfolder = output_folder

        print(f"[{idx}/{len(pdf_files)}] 📄 {rel_path}")

        try:
            # Конвертация с учетом poppler_path для macOS
            if poppler_path:
                pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
            else:
                pages = convert_from_path(pdf_path, dpi=dpi)

            for i, page in enumerate(pages):
                output_filename = f"{filename[:-4]}_page_{i + 1}.png"
                output_path = os.path.join(output_subfolder, output_filename)
                page.save(output_path, 'PNG')
                print(f"  ✅ Страница {i + 1}/{len(pages)} → {output_filename}")

            total_pages += len(pages)
            successful_files += 1
            print(f"  ✓ Готово: {len(pages)} страниц\n")

        except Exception as e:
            failed_files += 1
            print(f"  ❌ Ошибка: {str(e)}\n")

    print("=" * 60)
    print(f"🎉 Конвертация завершена!")
    print(f"   ✅ Успешно обработано: {successful_files} файлов")
    print(f"   ❌ Ошибок: {failed_files} файлов")
    print(f"   📄 Всего страниц: {total_pages}")
    print(f"   📂 Результаты в: {output_folder}")
    print("=" * 60)


def convert_pdfs_flat(root_folder, output_folder, dpi=300, poppler_path=None):
    """Конвертация всех PDF в одну плоскую папку (без сохранения структуры)"""
    os.makedirs(output_folder, exist_ok=True)

    if not os.path.exists(root_folder):
        print(f"❌ Папка не найдена: {root_folder}")
        return

    # Ищем все PDF файлы рекурсивно
    pdf_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"⚠️ В папке {root_folder} не найдено PDF файлов")
        return

    print(f"📁 Найдено {len(pdf_files)} PDF файлов")
    print(f"📂 Результаты будут сохранены в: {output_folder}\n")

    total_pages = 0
    successful_files = 0
    failed_files = 0

    for idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        rel_path = os.path.relpath(pdf_path, root_folder)

        print(f"[{idx}/{len(pdf_files)}] 📄 {rel_path}")

        try:
            if poppler_path:
                pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
            else:
                pages = convert_from_path(pdf_path, dpi=dpi)

            for i, page in enumerate(pages):
                # Используем полный путь в имени файла для уникальности
                safe_name = rel_path.replace('/', '_').replace('\\', '_')
                output_filename = f"{safe_name[:-4]}_page_{i + 1}.png"
                output_path = os.path.join(output_folder, output_filename)
                page.save(output_path, 'PNG')
                print(f"  ✅ Страница {i + 1}/{len(pages)} → {output_filename}")

            total_pages += len(pages)
            successful_files += 1
            print(f"  ✓ Готово: {len(pages)} страниц\n")

        except Exception as e:
            failed_files += 1
            print(f"  ❌ Ошибка: {str(e)}\n")

    print("=" * 60)
    print(f"🎉 Конвертация завершена!")
    print(f"   ✅ Успешно обработано: {successful_files} файлов")
    print(f"   ❌ Ошибок: {failed_files} файлов")
    print(f"   📄 Всего страниц: {total_pages}")
    print(f"   📂 Результаты в: {output_folder}")
    print("=" * 60)


if __name__ == '__main__':
    # Настройки
    PDF_FOLDER = '/Users/georgewashington/Downloads/Для отправки_02102025'
    OUTPUT_FOLDER = './converted_images'
    DPI = 300

    # Для macOS с Homebrew Poppler
    POPPLER_PATH = '/opt/homebrew/bin'

    # Выберите режим:

    # # Вариант 1: Сохранить структуру папок
    # print("🔄 Режим: Сохранение структуры папок\n")
    # convert_pdfs_to_images_recursive(
    #     root_folder=PDF_FOLDER,
    #     output_folder=OUTPUT_FOLDER,
    #     dpi=DPI,
    #     poppler_path=POPPLER_PATH
    # )

    # Вариант 2: Все файлы в одну папку (раскомментируйте если нужно)
    print("🔄 Режим: Все файлы в одну папку\n")
    convert_pdfs_flat(
        root_folder=PDF_FOLDER,
        output_folder=OUTPUT_FOLDER,
        dpi=DPI,
        poppler_path=POPPLER_PATH
    )