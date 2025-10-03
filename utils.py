import os
from pdf2image import convert_from_path


def convert_pdfs_to_images(pdf_folder, output_folder, dpi=300):
    """Конвертация всех PDF в папке в PNG"""
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(pdf_folder):
        if filename.endswith('.pdf'):
            pdf_path = os.path.join(pdf_folder, filename)
            pages = convert_from_path(pdf_path, dpi=dpi)

            for i, page in enumerate(pages):
                output_path = os.path.join(
                    output_folder,
                    f"{filename[:-4]}_page_{i}.png"
                )
                page.save(output_path, 'PNG')
                print(f"✅ Сохранено: {output_path}")