import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract

# Укажи пути
poppler_path = '/opt/homebrew/bin'
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

# Конвертация PDF


pages = convert_from_path('document.pdf', dpi=200, poppler_path=poppler_path)
image = np.array(pages[0])

# Вырезаем правый нижний угол (например, 1/4 от ширины и высоты)
h, w, _ = image.shape
crop = image[int(h*0.75):, int(w*0.75):]

# Копия для визуализации
vis = crop.copy()

# Преобразуем в оттенки серого
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

# Используем OCR для определения текста
data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

# Проходим по результатам OCR и выделяем текст
n_boxes = len(data['text'])
for i in range(n_boxes):
    if int(data['conf'][i]) > 0:  # уверенность > 0
        (x, y, w_box, h_box) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
        cv2.rectangle(vis, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)

# Показываем результат
cv2.imshow("Text regions in bottom-right corner", vis)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Извлекаем текст
text = pytesseract.image_to_string(gray)
print("Извлеченный текст из правого нижнего угла:")
print(text)