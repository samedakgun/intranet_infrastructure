import cv2
import numpy as np
import os
from typing import List, Tuple, Optional

class PlateDetector:
    """OpenCV tabanlı plaka tespit sınıfı."""
    
    def __init__(self):
        """Plaka tespit parametrelerini başlatır."""
        # Kenar bulma parametreleri
        self.canny_low = 50
        self.canny_high = 150
        
        # Morfoloji parametreleri
        self.morph_kernel_size = (3, 3)
        self.close_iterations = 2
        self.dilate_iterations = 1
        
        # Kontur filtreleme parametreleri
        self.min_area = 500
        self.max_area = 50000
        self.min_aspect_ratio = 2.0
        self.max_aspect_ratio = 6.5
        self.min_rectangularity = 0.6
        
        # Perspektif düzeltme parametreleri
        self.plate_width = 300
        self.plate_height = 100
    
    def preprocess_image(self, image):
        """Görsel ön işleme adımları."""
        # Gri tonlamaya dönüştür
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Gürültü azaltma
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        return gray, blurred
    
    def detect_edges(self, image):
        """Kenar tespiti yapar."""
        # Canny kenar tespiti
        edges = cv2.Canny(image, self.canny_low, self.canny_high)
        
        # Morfolojik işlemler
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, self.morph_kernel_size)
        
        # Closing - kenarları birleştir
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=self.close_iterations)
        
        # Dilate - kenarları kalınlaştır
        dilated = cv2.dilate(closed, kernel, iterations=self.dilate_iterations)
        
        return edges, dilated
    
    def find_contours(self, edge_image):
        """Konturları bulur ve filtreler."""
        # Konturları bul
        contours, _ = cv2.findContours(edge_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Konturları filtrele
        filtered_contours = []
        
        for contour in contours:
            # Alan kontrolü
            area = cv2.contourArea(contour)
            if area < self.min_area or area > self.max_area:
                continue
            
            # Bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # En-boy oranı kontrolü
            aspect_ratio = w / h
            if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                continue
            
            # Dikdörtgensellik kontrolü (kontur alanı / bounding rect alanı)
            rectangularity = area / (w * h)
            if rectangularity < self.min_rectangularity:
                continue
            
            filtered_contours.append({
                'contour': contour,
                'area': area,
                'bbox': (x, y, w, h),
                'aspect_ratio': aspect_ratio,
                'rectangularity': rectangularity
            })
        
        return filtered_contours
    
    def order_points(self, pts):
        """4 köşe noktasını sıralar: sol-üst, sağ-üst, sağ-alt, sol-alt."""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Sol-üst noktası en küçük toplama sahip
        # Sağ-alt noktası en büyük toplama sahip
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Sol-alt noktası en küçük farka sahip
        # Sağ-üst noktası en büyük farka sahip
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def get_perspective_transform(self, contour):
        """Konturdan perspektif dönüşüm matrisi hesaplar."""
        # Konturun yaklaşık dörtgenini bul
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Eğer 4 köşe bulunamazsa, bounding rectangle kullan
        if len(approx) != 4:
            x, y, w, h = cv2.boundingRect(contour)
            approx = np.array([
                [[x, y]],
                [[x + w, y]],
                [[x + w, y + h]],
                [[x, y + h]]
            ])
        
        # Köşeleri düzenle
        src_points = self.order_points(approx.reshape(4, 2))
        
        # Hedef noktalar (düzeltilmiş plaka)
        dst_points = np.array([
            [0, 0],
            [self.plate_width, 0],
            [self.plate_width, self.plate_height],
            [0, self.plate_height]
        ], dtype="float32")
        
        # Perspektif dönüşüm matrisi
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        
        return matrix, src_points
    
    def warp_plate(self, image, matrix):
        """Perspektif düzeltme uygular."""
        warped = cv2.warpPerspective(image, matrix, (self.plate_width, self.plate_height))
        return warped
    
    def calculate_score(self, contour_data, edge_image):
        """Plaka adayı için skor hesaplar."""
        x, y, w, h = contour_data['bbox']
        
        # ROI'deki kenar yoğunluğu
        roi = edge_image[y:y+h, x:x+w]
        edge_density = np.sum(roi > 0) / (w * h)
        
        # Temel skor bileşenleri
        area_score = min(contour_data['area'] / 10000, 1.0)  # Alan skoru
        aspect_score = 1.0 - abs(contour_data['aspect_ratio'] - 4.0) / 4.0  # İdeal oran 4:1
        rect_score = contour_data['rectangularity']  # Dikdörtgensellik
        edge_score = edge_density  # Kenar yoğunluğu
        
        # Ağırlıklı toplam
        total_score = (
            area_score * 0.2 +
            aspect_score * 0.3 +
            rect_score * 0.3 +
            edge_score * 0.2
        )
        
        return total_score
    
    def detect_plates(self, image):
        """Ana plaka tespit fonksiyonu."""
        try:
            # Ön işleme
            gray, blurred = self.preprocess_image(image)
            
            # Kenar tespiti
            edges, processed_edges = self.detect_edges(blurred)
            
            # Kontur bulma ve filtreleme
            contour_candidates = self.find_contours(processed_edges)
            
            if not contour_candidates:
                return []
            
            # Skorlama ve sıralama
            results = []
            for candidate in contour_candidates:
                score = self.calculate_score(candidate, edges)
                
                # Perspektif düzeltme
                try:
                    matrix, corners = self.get_perspective_transform(candidate['contour'])
                    warped_plate = self.warp_plate(image, matrix)
                    
                    results.append({
                        'bbox': candidate['bbox'],
                        'corners': corners,
                        'score': score,
                        'warped_plate': warped_plate,
                        'area': candidate['area'],
                        'aspect_ratio': candidate['aspect_ratio']
                    })
                except Exception as e:
                    print(f"Perspektif düzeltme hatası: {e}")
                    continue
            
            # Skora göre sırala (yüksekten düşüğe)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return results
            
        except Exception as e:
            print(f"Plaka tespit hatası: {e}")
            return []
    
    def draw_detection_overlay(self, image, detections, max_detections=3):
        """Tespit sonuçlarını görsel üzerine çizer."""
        overlay = image.copy()
        
        for i, detection in enumerate(detections[:max_detections]):
            # Bounding box
            x, y, w, h = detection['bbox']
            color = (0, 255, 0) if i == 0 else (0, 255, 255)  # En iyi yeşil, diğerleri sarı
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)
            
            # Köşe noktaları
            corners = detection['corners'].astype(int)
            cv2.polylines(overlay, [corners], True, color, 2)
            
            # Skor etiketi
            score_text = f"Score: {detection['score']:.2f}"
            cv2.putText(overlay, score_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return overlay

def test_plate_detection():
    """Plaka tespit algoritmasını test eder."""
    detector = PlateDetector()
    
    # Test görseli oluştur (basit plaka benzeri)
    test_image = np.zeros((400, 600, 3), dtype=np.uint8)
    test_image[150:250, 200:500] = [255, 255, 255]  # Beyaz dikdörtgen (plaka benzeri)
    cv2.rectangle(test_image, (200, 150), (500, 250), (0, 0, 0), 2)  # Siyah çerçeve
    
    # Tespit yap
    detections = detector.detect_plates(test_image)
    
    if detections:
        print(f"✓ {len(detections)} plaka adayı bulundu")
        for i, detection in enumerate(detections):
            print(f"  Aday {i+1}: Skor={detection['score']:.2f}, Alan={detection['area']}, Oran={detection['aspect_ratio']:.2f}")
        return True
    else:
        print("✗ Plaka tespit edilemedi")
        return False

if __name__ == "__main__":
    test_plate_detection()

