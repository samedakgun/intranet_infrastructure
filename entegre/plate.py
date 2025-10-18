import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from PIL import Image
import cv2
import numpy as np

# Import our custom modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from image_processing import ImageNormalizer
from enhanced_detector import EnhancedPlateDetector
from ocr_reader import OCRReader

plate_bp = Blueprint('plate', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_RESOLUTION = 3000

# Global instances
normalizer = ImageNormalizer(target_size=1024)
detector = EnhancedPlateDetector()
ocr_reader = OCRReader(languages=['en', 'tr'])

def allowed_file(filename):
    """Dosya uzantısının izin verilen türde olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(file_path):
    """Görsel dosyasının boyut ve çözünürlük sınırlarını kontrol eder."""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            if width > MAX_RESOLUTION or height > MAX_RESOLUTION:
                return False, f"Çözünürlük çok yüksek. Maksimum: {MAX_RESOLUTION}px"
        return True, "OK"
    except Exception as e:
        return False, f"Görsel dosyası okunamadı: {str(e)}"

def save_detection_results(detections, original_image, output_folder, base_filename):
    """Tespit sonuçlarını dosyalara kaydeder."""
    results = []
    
    for i, detection in enumerate(detections):
        # Kırpılmış plaka görselini kaydet
        warped_filename = f"{base_filename}_plate_{i+1}.png"
        warped_path = os.path.join(output_folder, warped_filename)
        cv2.imwrite(warped_path, detection['warped_plate'])
        
        # OCR ile metin oku
        ocr_results = ocr_reader.read_text(detection['warped_plate'])
        recognized_text = ""
        confidence = 0.0
        if ocr_results:
            # En yüksek güvene sahip metni al
            best_result = max(ocr_results, key=lambda x: x['confidence'])
            recognized_text = best_result['text']
            confidence = best_result['confidence']

        # Sonuç bilgilerini hazırla
        result = {
            'id': i + 1,
            'bbox': {
                'x': int(detection['bbox'][0]),
                'y': int(detection['bbox'][1]),
                'width': int(detection['bbox'][2]),
                'height': int(detection['bbox'][3])
            },
            'corners': detection['corners'],
            'score': float(detection.get('final_score', detection['score'])),
            'confidence': float(detection['score']),
            'area': float(detection['area']),
            'aspect_ratio': float(detection['aspect_ratio']),
            'method': detection.get('method', 'standard'),
            'cropped_plate_path': warped_filename,
            'recognized_text': recognized_text,
            'ocr_confidence': float(confidence)
        }
        results.append(result)
    
    # Overlay görselini kaydet
    if detections:
        overlay_image = detector.draw_detection_overlay(original_image, detections)
        overlay_filename = f"{base_filename}_overlay.jpg"
        overlay_path = os.path.join(output_folder, overlay_filename)
        cv2.imwrite(overlay_path, overlay_image)
        
        return results, overlay_filename
    
    return results, None

@plate_bp.route('/health', methods=['GET'])
def health_check():
    """Sistem sağlık kontrolü endpoint'i."""
    return jsonify({
        'status': 'healthy',
        'message': 'Plaka tanımlama servisi çalışıyor',
        'version': '1.0.0',
        'algorithms': ['standard', 'enhanced', 'color_filtering', 'multi_scale'],
        'ocr_enabled': True
    }), 200

@plate_bp.route('/detect', methods=['POST'])
def detect_plate():
    """Plaka tanımlama endpoint'i."""
    try:
        # Dosya varlığını kontrol et
        if 'image' not in request.files:
            return jsonify({
                'error': 'Dosya bulunamadı',
                'message': 'image alanında dosya gönderilmeli'
            }), 400
        
        file = request.files['image']
        
        # Dosya seçilip seçilmediğini kontrol et
        if file.filename == '':
            return jsonify({
                'error': 'Dosya seçilmedi',
                'message': 'Geçerli bir dosya seçin'
            }), 400
        
        # Dosya türünü kontrol et
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Desteklenmeyen dosya türü',
                'message': f'Desteklenen formatlar: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Dosya boyutunu kontrol et
        file.seek(0, 2)  # Dosyanın sonuna git
        file_size = file.tell()
        file.seek(0)  # Başa dön
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'error': 'Dosya çok büyük',
                'message': f'Maksimum dosya boyutu: {MAX_FILE_SIZE // (1024*1024)} MB'
            }), 400
        
        # Benzersiz dosya adı oluştur
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"plate_detection_{timestamp}_{unique_id}"
        filename = f"{base_filename}.{file_extension}"
        
        # Klasörleri oluştur
        upload_folder = os.path.join(current_app.root_path, '..', '..', 'uploads')
        output_folder = os.path.join(current_app.root_path, '..', '..', 'outputs')
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(output_folder, exist_ok=True)
        
        # Dosyayı kaydet
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Görsel doğrulaması
        is_valid, validation_message = validate_image(file_path)
        if not is_valid:
            os.remove(file_path)  # Geçersiz dosyayı sil
            return jsonify({
                'error': 'Geçersiz görsel',
                'message': validation_message
            }), 400
        
        # Görsel normalizasyonu
        normalized_image, norm_message = normalizer.normalize_image(file_path)
        if normalized_image is None:
            os.remove(file_path)
            return jsonify({
                'error': 'Görsel normalizasyon hatası',
                'message': norm_message
            }), 500
        
        # Plaka tespiti
        detections = detector.detect_plates(normalized_image)
        
        # Sonuçları kaydet
        detection_results, overlay_filename = save_detection_results(
            detections, normalized_image, output_folder, base_filename
        )
        
        # API yanıtını hazırla
        response_data = {
            'success': True,
            'message': f'{len(detections)} plaka adayı tespit edildi' if detections else 'Plaka tespit edilemedi',
            'timestamp': datetime.now().isoformat(),
            'input_file': filename,
            'file_size': file_size,
            'image_dimensions': {
                'width': normalized_image.shape[1],
                'height': normalized_image.shape[0]
            },
            'detection_count': len(detections),
            'detections': detection_results,
            'overlay_image': overlay_filename,
            'processing_info': {
                'normalization': norm_message,
                'algorithm': 'enhanced_multi_method',
                'ocr_enabled': True
            }
        }
        
        # Başarı durumu
        status_code = 200 if detections else 200  # Her durumda 200, sadece detection_count 0 olabilir
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'error': 'Sunucu hatası',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@plate_bp.route('/info', methods=['GET'])
def get_info():
    """API bilgileri endpoint'i."""
    return jsonify({
        'api_name': 'Plaka Tanımlama API',
        'version': '1.0.0',
        'description': 'OpenCV tabanlı plaka tanımlama servisi',
        'endpoints': {
            '/api/health': 'Sistem sağlık kontrolü',
            '/api/detect': 'Plaka tespit işlemi (POST)',
            '/api/info': 'API bilgileri'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_FILE_SIZE // (1024 * 1024),
        'max_resolution': MAX_RESOLUTION,
        'algorithms': [
            'Canny edge detection',
            'Morphological operations',
            'Contour filtering',
            'Perspective correction',
            'Color-based filtering',
            'Multi-scale detection',
            'Non-maximum suppression'
        ],
        'ocr_supported': True,
        'ocr_languages': ['en', 'tr']
    }), 200

