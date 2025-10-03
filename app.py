from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from pdf2image import convert_from_path
from GOSTErrorDetector import GOSTErrorDetector
import config

app = Flask(__name__)
UPLOAD_FOLDER = config.UPLOAD_FOLDER
TEMP_FOLDER = config.TEMP_FOLDER

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class FileEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, completed, error
    errors_found = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<File {self.filename}>'


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    files = FileEntry.query.all()
    return render_template('index.html', files=files)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files allowed'}), 400

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Сохраняем в БД
        new_entry = FileEntry(filename=file.filename, filepath=filepath)
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': new_entry.id,
            'path': filepath
        }), 200


@app.route('/check/<int:file_id>', methods=['POST'])
def check_file(file_id):
    """Проверка файла на ошибки"""
    file_entry = FileEntry.query.get_or_404(file_id)

    try:
        file_entry.status = 'processing'
        db.session.commit()

        # Конвертируем PDF в изображения
        pages = convert_from_path(
            file_entry.filepath,
            dpi=config.PDF_DPI,
            poppler_path=config.POPPLER_PATH
        )

        detector = GOSTErrorDetector()
        all_errors = []

        for i, page in enumerate(pages):
            temp_path = os.path.join(TEMP_FOLDER, f'temp_page_{file_id}_{i}.png')
            page.save(temp_path)

            errors = detector.detect_errors(temp_path)
            all_errors.extend(errors)

            # Удаляем временный файл
            os.remove(temp_path)

        file_entry.status = 'completed'
        file_entry.errors_found = len(all_errors)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'errors_count': len(all_errors),
            'errors': all_errors
        }), 200

    except Exception as e:
        file_entry.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True)