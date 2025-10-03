from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import json
import time
from GOSTErrorDetector import GOSTErrorDetector

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Настройка базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    analysis_results = db.relationship('AnalysisResult', backref='file', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<File {self.filename}>'


class AnalysisResult(db.Model):
    """Результаты проверки чертежей"""
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file_entry.id'), nullable=False)

    checked_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))
    total_errors = db.Column(db.Integer, default=0)
    critical_errors = db.Column(db.Integer, default=0)
    high_errors = db.Column(db.Integer, default=0)
    medium_errors = db.Column(db.Integer, default=0)
    low_errors = db.Column(db.Integer, default=0)

    processing_time = db.Column(db.Float)
    model_version = db.Column(db.String(50))

    errors = db.relationship('DetectedError', backref='analysis', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AnalysisResult {self.id} - {self.total_errors} errors>'


class DetectedError(db.Model):
    """Найденные ошибки на чертежах"""
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analysis_result.id'), nullable=False)

    error_type = db.Column(db.String(100), nullable=False)
    error_category = db.Column(db.String(100))
    severity = db.Column(db.String(20))

    description = db.Column(db.Text)
    recommendation = db.Column(db.Text)

    bbox_x = db.Column(db.Integer)
    bbox_y = db.Column(db.Integer)
    bbox_width = db.Column(db.Integer)
    bbox_height = db.Column(db.Integer)

    extra_data = db.Column(db.Text)

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
            'extra_data': json.loads(self.extra_data) if self.extra_data else None
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

        file_size = os.path.getsize(filepath)
        file_type = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'

        final_filepath = filepath
        final_filename = file.filename

        if file_type == 'pdf':
            try:
                from pdf2image import convert_from_path
                import config

                print(f"📄 Конвертация PDF в PNG: {file.filename}")

                pages = convert_from_path(
                    filepath,
                    dpi=config.PDF_DPI,
                    poppler_path=config.POPPLER_PATH
                )

                png_filename = file.filename.rsplit('.', 1)[0] + '.png'
                png_filepath = os.path.join(UPLOAD_FOLDER, png_filename)
                pages[0].save(png_filepath, 'PNG')

                final_filepath = png_filepath
                final_filename = png_filename
                file_type = 'png'
                file_size = os.path.getsize(png_filepath)

                print(f"✅ Конвертировано: {png_filename}")

            except Exception as e:
                print(f"❌ Ошибка конвертации PDF: {str(e)}")
                return jsonify({'error': f'PDF conversion failed: {str(e)}'}), 500

        new_entry = FileEntry(
            filename=final_filename,
            filepath=final_filepath,
            file_size=file_size,
            file_type=file_type,
            user_id=None
        )
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': new_entry.id,
            'filename': final_filename,
            'file_type': file_type,
            'path': final_filepath,
            'converted_from_pdf': file.filename.endswith('.pdf')
        }), 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route('/analyze/<int:file_id>', methods=['POST'])
def analyze_file(file_id):
    file_entry = FileEntry.query.get_or_404(file_id)

    analysis = AnalysisResult(
        file_id=file_id,
        status='in_progress',
        model_version='v1.0'
    )
    db.session.add(analysis)
    db.session.commit()

    try:
        start_time = time.time()

        detector = GOSTErrorDetector('models/best.pt')
        detected_errors = detector.detect_errors(file_entry.filepath, conf_threshold=0.25)

        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}

        for err in detected_errors:
            detected_error = DetectedError(
                analysis_id=analysis.id,
                error_type=err['type'],
                error_category='auto_detected',
                severity=err['severity'],
                description=err['description'],
                recommendation=get_recommendation(err['type']),
                bbox_x=err['bbox']['x'],
                bbox_y=err['bbox']['y'],
                bbox_width=err['bbox']['width'],
                bbox_height=err['bbox']['height'],
                extra_data=json.dumps({'confidence': err['confidence']})
            )
            db.session.add(detected_error)
            severity_counts[err['severity']] += 1

        processing_time = time.time() - start_time
        analysis.status = 'completed'
        analysis.total_errors = len(detected_errors)
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


def get_recommendation(error_type):
    """Возвращает рекомендацию по исправлению ошибки"""
    recommendations = {
        'missing_stamp': 'Добавьте основную надпись согласно ГОСТ 2.104',
        'wrong_document_code': 'Исправьте код документа согласно ГОСТ 2.102',
        'wrong_tt_position': 'Переместите технические требования над основной надписью',
        'missing_letter_designation': 'Добавьте буквенное обозначение на чертёж',
        'missing_asterisks': 'Добавьте символы *, **, *** на поле чертежа',
        'dimension_30deg_violation': 'Добавьте полку к размеру в зоне 30°',
        'missing_tolerance_arrow': 'Добавьте дополнительную стрелку в допуске',
        'missing_general_roughness': 'Добавьте знак √ в скобках в углу чертежа'
    }
    return recommendations.get(error_type, 'Проверьте соответствие ГОСТ')


# ========== HTML СТРАНИЦА С ВИЗУАЛИЗАЦИЕЙ ==========
@app.route('/results/<int:file_id>')
def show_results(file_id):
    """Страница с визуализацией результатов"""
    file_entry = FileEntry.query.get_or_404(file_id)
    analysis = AnalysisResult.query.filter_by(file_id=file_id) \
        .order_by(AnalysisResult.checked_at.desc()).first()

    if not analysis:
        return "Анализ не найден. Сначала запустите проверку.", 404

    errors = DetectedError.query.filter_by(analysis_id=analysis.id).all()

    return render_template('results.html',
                           file=file_entry,
                           analysis=analysis,
                           errors=errors)


# ========== JSON API ==========
@app.route('/api/results/<int:file_id>')
def get_results_json(file_id):
    """API: Получить результаты в JSON формате"""
    file_entry = FileEntry.query.get_or_404(file_id)

    analysis = AnalysisResult.query.filter_by(file_id=file_id) \
        .order_by(AnalysisResult.checked_at.desc()).first()

    if not analysis:
        return jsonify({'message': 'No analysis found for this file'}), 404

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

    errors_by_category = db.session.query(
        DetectedError.error_category,
        db.func.count(DetectedError.id)
    ).group_by(DetectedError.error_category).all()

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