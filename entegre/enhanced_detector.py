import cv2
import numpy as np
import os
from typing import List, Tuple, Optional
from plate_detector import PlateDetector

class EnhancedPlateDetector(PlateDetector):
    """Gelişmiş plaka tespit algoritması - çoklu yaklaşım kullanır."""
    
    def __init__(self):
        super().__init__()
        # Ek parametreler
        self.use_adaptive_threshold = True
        self.use_color_filtering = True
        self.use_multiple_scales = True
        
        # Renk filtreleme için HSV aralıkları (mavi plakalar için)
        self.blue_lower = np.array([100, 50, 50])
        self.blue_upper = np.array([130, 255, 255])
        
        # Beyaz plakalar için
        self.white_lower = np.array([0, 0, 200])
        self.white_upper = np.array([180, 30, 255])
    
    def adaptive_threshold_processing(self, gray_image):
        """Adaptif eşikleme ile görsel işleme."""
        # Gaussian adaptif eşikleme
        adaptive = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Morfolojik işlemler
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)
        
        return processed
    
    def color_based_filtering(self, image):
        """Renk tabanlı plaka bölgesi filtreleme."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Mavi plaka maskesi
        blue_mask = cv2.inRange(hsv, self.blue_lower, self.blue_upper)
        
        # Beyaz plaka maskesi
        white_mask = cv2.inRange(hsv, self.white_lower, self.white_upper)
        
        # Maskeleri birleştir
        combined_mask = cv2.bitwise_or(blue_mask, white_mask)
        
        # Morfolojik temizleme
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_OPEN, kernel)
        
        return cleaned_mask
    
    def multi_scale_detection(self, image, scales=[0.8, 1.0, 1.2]):
        """Çoklu ölçekte tespit yapar."""
        all_detections = []
        original_height, original_width = image.shape[:2]
        
        for scale in scales:
            # Görseli ölçekle
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            scaled_image = cv2.resize(image, (new_width, new_height))
            
            # Tespit yap
            detections = super().detect_plates(scaled_image)
            
            # Koordinatları orijinal boyuta geri ölçekle
            for detection in detections:
                x, y, w, h = detection['bbox']
                detection['bbox'] = (
                    int(x / scale), int(y / scale),
                    int(w / scale), int(h / scale)
                )
                
                # Köşe noktalarını da ölçekle
                detection['corners'] = detection['corners'] / scale
                
                # Ölçek bilgisini ekle
                detection['scale'] = scale
                
            all_detections.extend(detections)
        
        return all_detections
    
    def non_max_suppression(self, detections, overlap_threshold=0.3):
        """Çakışan tespitleri filtreler."""
        if not detections:
            return []
        
        # Skorlara göre sırala
        detections.sort(key=lambda x: x['score'], reverse=True)
        
        filtered = []
        
        for current in detections:
            x1, y1, w1, h1 = current['bbox']
            
            # Mevcut filtrelenmiş tespitlerle çakışma kontrolü
            is_overlapping = False
            
            for existing in filtered:
                x2, y2, w2, h2 = existing['bbox']
                
                # Intersection over Union (IoU) hesapla
                intersection_x = max(x1, x2)
                intersection_y = max(y1, y2)
                intersection_w = min(x1 + w1, x2 + w2) - intersection_x
                intersection_h = min(y1 + h1, y2 + h2) - intersection_y
                
                if intersection_w > 0 and intersection_h > 0:
                    intersection_area = intersection_w * intersection_h
                    union_area = w1 * h1 + w2 * h2 - intersection_area
                    iou = intersection_area / union_area
                    
                    if iou > overlap_threshold:
                        is_overlapping = True
                        break
            
            if not is_overlapping:
                filtered.append(current)
        
        return filtered
    
    def enhanced_detect_plates(self, image):
        """Gelişmiş plaka tespit ana fonksiyonu."""
        try:
            all_detections = []
            
            # 1. Standart tespit
            standard_detections = super().detect_plates(image)
            all_detections.extend(standard_detections)
            
            # 2. Adaptif eşikleme ile tespit
            if self.use_adaptive_threshold:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
                adaptive_processed = self.adaptive_threshold_processing(gray)
                
                # Adaptif işlenmiş görsel üzerinde tespit
                adaptive_image = cv2.cvtColor(adaptive_processed, cv2.COLOR_GRAY2BGR)
                adaptive_detections = super().detect_plates(adaptive_image)
                
                # Skorları biraz düşür (çünkü daha az güvenilir)
                for detection in adaptive_detections:
                    detection['score'] *= 0.8
                    detection['method'] = 'adaptive'
                
                all_detections.extend(adaptive_detections)
            
            # 3. Renk tabanlı filtreleme ile tespit
            if self.use_color_filtering and len(image.shape) == 3:
                color_mask = self.color_based_filtering(image)
                
                # Maskeyi uygula
                masked_image = cv2.bitwise_and(image, image, mask=color_mask)
                color_detections = super().detect_plates(masked_image)
                
                # Renk tabanlı tespitlerin skorunu artır
                for detection in color_detections:
                    detection['score'] *= 1.2
                    detection['method'] = 'color'
                
                all_detections.extend(color_detections)
            
            # 4. Çoklu ölçek tespiti
            if self.use_multiple_scales:
                multi_scale_detections = self.multi_scale_detection(image)
                
                for detection in multi_scale_detections:
                    detection['method'] = f"scale_{detection['scale']}"
                
                all_detections.extend(multi_scale_detections)
            
            # 5. Non-maximum suppression uygula
            filtered_detections = self.non_max_suppression(all_detections)
            
            # 6. Final skorlama ve sıralama
            for detection in filtered_detections:
                # Yöntem bonusu
                method_bonus = 1.0
                if detection.get('method') == 'color':
                    method_bonus = 1.1
                elif detection.get('method') == 'adaptive':
                    method_bonus = 0.9
                
                detection['final_score'] = detection['score'] * method_bonus
            
            # Final skora göre sırala
            filtered_detections.sort(key=lambda x: x.get('final_score', x['score']), reverse=True)
            
            return filtered_detections
            
        except Exception as e:
            print(f"Gelişmiş plaka tespit hatası: {e}")
            return []
    
    def detect_plates(self, image):
        """Ana tespit fonksiyonu - gelişmiş algoritma kullanır."""
        return self.enhanced_detect_plates(image)

def test_enhanced_detection():
    """Gelişmiş plaka tespit algoritmasını test eder."""
    detector = EnhancedPlateDetector()
    
    # Test görseli oluştur
    test_image = np.zeros((400, 600, 3), dtype=np.uint8)
    
    # Mavi plaka benzeri
    test_image[150:250, 200:500] = [255, 100, 0]  # Mavi renk
    cv2.rectangle(test_image, (200, 150), (500, 250), (0, 0, 0), 2)
    
    # Tespit yap
    detections = detector.detect_plates(test_image)
    
    if detections:
        print(f"✓ {len(detections)} plaka adayı bulundu (gelişmiş algoritma)")
        for i, detection in enumerate(detections):
            method = detection.get('method', 'standard')
            score = detection.get('final_score', detection['score'])
            print(f"  Aday {i+1}: Skor={score:.2f}, Yöntem={method}")
        return True
    else:
        print("✗ Plaka tespit edilemedi (gelişmiş algoritma)")
        return False

if __name__ == "__main__":
    test_enhanced_detection()

