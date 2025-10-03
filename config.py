import os

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
TEMP_FOLDER = os.path.join(BASE_DIR, 'temp')
DATASET_FOLDER = os.path.join(BASE_DIR, 'dataset_errors')
MODEL_WEIGHTS = os.path.join(BASE_DIR, 'models', 'best.pt')

# Параметры обработки
PDF_DPI = 300
OCR_LANGUAGES = ['ru', 'en']
OCR_GPU = False

# Параметры детектора
CONFIDENCE_THRESHOLD = 0.5
NMS_THRESHOLD = 0.4

# Пути к системным утилитам (для macOS)
POPPLER_PATH = '/opt/homebrew/bin'
TESSERACT_CMD = '/opt/homebrew/bin/tesseract'

# Создание папок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(DATASET_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'models'), exist_ok=True)