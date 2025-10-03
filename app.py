from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ========== МОДЕЛИ ==========

class User(db.Model):
    """Пользователи системы"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    files = db.relationship('FileEntry', backref='uploader', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class FileEntry(db.Model):
    """Загруженные файлы"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # размер в байтах
    file_type = db.Column(db.String(50))  # pdf, png, jpg

    # Внешний ключ
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Связи
    analysis_results = db.relationship('AnalysisResult', backref='file', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<File {self.filename}>'


class AnalysisResult(db.Model):
    """Результаты проверки чертежей"""
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file_entry.id'), nullable=False)

    # Информация о проверке
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))  # 'completed', 'failed', 'in_progress'
    total_errors = db.Column(db.Integer, default=0)
    critical_errors = db.Column(db.Integer, default=0)
    high_errors = db.Column(db.Integer, default=0)
    medium_errors = db.Column(db.Integer, default=0)
    low_errors = db.Column(db.Integer, default=0)

    # Метаданные
    processing_time = db.Column(db.Float)  # время обработки в секундах
    model_version = db.Column(db.String(50))  # версия модели детекции

    # Связи
    errors = db.relationship('DetectedError', backref='analysis', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AnalysisResult {self.id} - {self.total_errors} errors>'


class DetectedError(db.Model):
    """Найденные ошибки на чертежах"""
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis_result.id'), nullable=False)

    # Тип ошибки
    error_type = db.Column(db.String(100), nullable=False)  # из ERRORS_TAXONOMY
    error_category = db.Column(db.String(100))  # stamp_errors, technical_requirements, etc.
    severity = db.Column(db.String(20))  # critical, high, medium, low

    # Описание
    description = db.Column(db.Text)
    recommendation = db.Column(db.Text)  # как исправить

    # Координаты на чертеже (bbox)
    bbox_x = db.Column(db.Integer)
    bbox_y = db.Column(db.Integer)
    bbox_width = db.Column(db.Integer)
    bbox_height = db.Column(db.Integer)

    # Дополнительные данные (JSON)
    metadata = db.Column(db.Text)  # JSON с доп. информацией

    # Статус
    is_fixed = db.Column(db.Boolean, default=False)
    fixed_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Error {self.error_type} - {self.severity}>'

    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'type': self.error_type,
            'category': self.error_category,
            'severity': self.severity,
            'description': self.description,
            'recommendation': self.recommendation,
            'bbox': {
                'x': self.bbox_x,
                'y': self.bbox_y,
                'width': self.bbox_width,
                'height': self.bbox_height
            } if self.bbox_x is not None else None,
            'is_fixed': self.is_fixed,
            'metadata': json.loads(self.metadata) if self.metadata else None
        }


# Создание таблиц
with app.app_context():
    db.create_all()


# ========== API ENDPOINTS ==========

@app.route('/')
def index():
    files = FileEntry.query.order_by(FileEntry.uploaded_at.desc()).all()
    return render_template('index.html', files=files)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        # Получаем размер файла
        file_size = os.path.getsize(filepath)
        file_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'

        # Сохраняем в БД
        new_entry = FileEntry(
            filename=file.filename,
            filepath=filepath,
            file_size=file_size,
            file_type=file_type,
            user_id=None  # TODO: добавить аутентификацию
        )
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': new_entry.id,
            'path': filepath
        }), 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/analyze/<int:file_id>', methods=['POST'])
def analyze_file(file_id):
    """Запуск анализа чертежа"""
    file_entry = FileEntry.query.get_or_404(file_id)

    # Создаем запись о начале анализа
    analysis = AnalysisResult(
        file_id=file_id,
        status='in_progress',
        model_version='v1.0'
    )
    db.session.add(analysis)
    db.session.commit()

    try:
        # TODO: Здесь вызов вашего GOSTErrorDetector
        # detector = GOSTErrorDetector()
        # errors = detector.detect_errors(file_entry.filepath)

        # MOCK данные для примера
        import time
        start_time = time.time()

        # Симуляция обнаружения ошибок
        mock_errors = [
            {
                'type': 'missing_stamp',
                'category': 'stamp_errors',
                'severity': 'critical',
                'description': 'Отсутствует основная надпись',
                'recommendation': 'Добавьте основную надпись согласно ГОСТ 2.104',
                'bbox': {'x': 1500, 'y': 2000, 'width': 185, 'height': 55}
            },
            {
                'type': 'wrong_tt_position',
                'category': 'technical_requirements',
                'severity': 'medium',
                'description': 'Технические требования расположены неверно',
                'recommendation': 'Переместите ТТ над основной надписью',
                'bbox': {'x': 50, 'y': 50, 'width': 200, 'height': 100}
            }
        ]

        # Сохраняем найденные ошибки
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        for err in mock_errors:
            detected_error = DetectedError(
                analysis_id=analysis.id,
                error_type=err['type'],
                error_category=err['category'],
                severity=err['severity'],
                description=err['description'],
                recommendation=err['recommendation'],
                bbox_x=err['bbox']['x'],
                bbox_y=err['bbox']['y'],
                bbox_width=err['bbox']['width'],
                bbox_height=err['bbox']['height'],
                metadata=json.dumps({'confidence': 0.95})
            )
            db.session.add(detected_error)
            severity_counts[err['severity']] += 1

        # Обновляем результаты анализа
        processing_time = time.time() - start_time
        analysis.status = 'completed'
        analysis.total_errors = len(mock_errors)
        analysis.critical_errors = severity_counts['critical']
        analysis.high_errors = severity_counts['high']
        analysis.medium_errors = severity_counts['medium']
        analysis.low_errors = severity_counts['low']
        analysis.processing_time = processing_time

        db.session.commit()

        return jsonify({
            'message': 'Analysis completed',
            'analysis_id': analysis.id,
            'total_errors': analysis.total_errors,
            'errors_by_severity': severity_counts,
            'processing_time': round(processing_time, 2)
        }), 200

    except Exception as e:
        analysis.status = 'failed'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@app.route('/results/<int:file_id>')
def get_results(file_id):
    """Получить результаты анализа файла"""
    file_entry = FileEntry.query.get_or_404(file_id)

    # Получаем последний анализ
    analysis = AnalysisResult.query.filter_by(file_id=file_id) \
        .order_by(AnalysisResult.checked_at.desc()).first()

    if not analysis:
        return jsonify({'message': 'No analysis found for this file'}), 404

    # Получаем все ошибки
    errors = DetectedError.query.filter_by(analysis_id=analysis.id).all()

    return jsonify({
        'file': {
            'id': file_entry.id,
            'filename': file_entry.filename,
            'uploaded_at': file_entry.uploaded_at.isoformat()
        },
        'analysis': {
            'id': analysis.id,
            'status': analysis.status,
            'checked_at': analysis.checked_at.isoformat(),
            'total_errors': analysis.total_errors,
            'critical_errors': analysis.critical_errors,
            'high_errors': analysis.high_errors,
            'medium_errors': analysis.medium_errors,
            'low_errors': analysis.low_errors,
            'processing_time': analysis.processing_time
        },
        'errors': [error.to_dict() for error in errors]
    }), 200


@app.route('/errors/<int:error_id>/fix', methods=['POST'])
def mark_error_fixed(error_id):
    """Отметить ошибку как исправленную"""
    error = DetectedError.query.get_or_404(error_id)
    error.is_fixed = True
    error.fixed_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Error marked as fixed'}), 200


@app.route('/statistics')
def get_statistics():
    """Общая статистика по всем проверкам"""
    total_files = FileEntry.query.count()
    total_analyses = AnalysisResult.query.count()
    total_errors = DetectedError.query.count()

    # Ошибки по категориям
    errors_by_category = db.session.query(
        DetectedError.error_category,
        db.func.count(DetectedError.id)
    ).group_by(DetectedError.error_category).all()

    # Ошибки по важности
    errors_by_severity = db.session.query(
        DetectedError.severity,
        db.func.count(DetectedError.id)
    ).group_by(DetectedError.severity).all()

    return jsonify({
        'total_files': total_files,
        'total_analyses': total_analyses,
        'total_errors': total_errors,
        'errors_by_category': dict(errors_by_category),
        'errors_by_severity': dict(errors_by_severity)
    }), 200


@app.route('/files')
def list_files():
    """Список всех файлов с результатами анализа"""
    files = FileEntry.query.order_by(FileEntry.uploaded_at.desc()).all()

    result = []
    for file in files:
        latest_analysis = AnalysisResult.query.filter_by(file_id=file.id) \
            .order_by(AnalysisResult.checked_at.desc()).first()

        result.append({
            'id': file.id,
            'filename': file.filename,
            'uploaded_at': file.uploaded_at.isoformat(),
            'file_size': file.file_size,
            'file_type': file.file_type,
            'last_analysis': {
                'total_errors': latest_analysis.total_errors,
                'status': latest_analysis.status,
                'checked_at': latest_analysis.checked_at.isoformat()
            } if latest_analysis else None
        })

    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True)