import cv2
import numpy as np
from PIL import Image, ExifTags
import os

class ImageNormalizer:
    """Görsel normalizasyon işlemlerini gerçekleştiren sınıf."""
    
    def __init__(self, target_size=1024):
        """
        Args:
            target_size (int): Hedef boyut (uzun kenar için)
        """
        self.target_size = target_size
    
    def fix_exif_rotation(self, image_path):
        """EXIF verilerine göre görsel rotasyonunu düzeltir."""
        try:
            image = Image.open(image_path)
            
            # EXIF verilerini kontrol et
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    for tag, value in exif.items():
                        if tag in ExifTags.TAGS:
                            if ExifTags.TAGS[tag] == 'Orientation':
                                if value == 3:
                                    image = image.rotate(180, expand=True)
                                elif value == 6:
                                    image = image.rotate(270, expand=True)
                                elif value == 8:
                                    image = image.rotate(90, expand=True)
                                break
            
            # OpenCV formatına dönüştür
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            return opencv_image
            
        except Exception as e:
            print(f"EXIF rotasyon düzeltme hatası: {e}")
            # Hata durumunda normal yükleme
            return cv2.imread(image_path)
    
    def resize_image(self, image, target_size=None):
        """Görseli oranını koruyarak yeniden boyutlandırır."""
        if target_size is None:
            target_size = self.target_size
            
        height, width = image.shape[:2]
        
        # Uzun kenarı bul
        max_dimension = max(height, width)
        
        # Eğer görsel zaten hedef boyuttan küçükse, olduğu gibi bırak
        if max_dimension <= target_size:
            return image
        
        # Ölçekleme oranını hesapla
        scale = target_size / max_dimension
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Yeniden boyutlandır
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return resized
    
    def enhance_contrast(self, image, clip_limit=2.0, tile_grid_size=(8, 8)):
        """CLAHE (Contrast Limited Adaptive Histogram Equalization) uygular."""
        try:
            # Gri tonlamaya dönüştür
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # CLAHE uygula
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            enhanced = clahe.apply(gray)
            
            # Eğer orijinal görsel renkli ise, sadece parlaklık kanalını güncelle
            if len(image.shape) == 3:
                # BGR'den LAB'a dönüştür
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                lab[:, :, 0] = enhanced
                # LAB'dan BGR'ye geri dönüştür
                enhanced_color = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
                return enhanced_color
            else:
                return enhanced
                
        except Exception as e:
            print(f"Kontrast iyileştirme hatası: {e}")
            return image
    
    def reduce_noise(self, image, method='bilateral'):
        """Gürültü azaltma işlemi uygular."""
        try:
            if method == 'bilateral':
                # Bilateral filter - kenarları koruyarak gürültüyü azaltır
                denoised = cv2.bilateralFilter(image, 9, 75, 75)
            elif method == 'gaussian':
                # Gaussian blur
                denoised = cv2.GaussianBlur(image, (5, 5), 0)
            else:
                return image
            
            return denoised
            
        except Exception as e:
            print(f"Gürültü azaltma hatası: {e}")
            return image
    
    def convert_to_grayscale(self, image):
        """Görseli gri tonlamaya dönüştürür."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    def validate_image_properties(self, image):
        """Görsel özelliklerini kontrol eder."""
        if image is None:
            return False, "Görsel yüklenemedi"
        
        if len(image.shape) < 2:
            return False, "Geçersiz görsel boyutu"
        
        height, width = image.shape[:2]
        if height < 50 or width < 50:
            return False, "Görsel çok küçük (minimum 50x50 piksel)"
        
        # Kanal sayısını kontrol et
        if len(image.shape) == 3 and image.shape[2] not in [1, 3, 4]:
            return False, "Desteklenmeyen kanal sayısı"
        
        return True, "OK"
    
    def normalize_image(self, image_path, output_path=None, enhance_contrast=True, reduce_noise=True):
        """Tam görsel normalizasyon pipeline'ı."""
        try:
            # 1. EXIF rotasyon düzeltme ile yükle
            image = self.fix_exif_rotation(image_path)
            
            # 2. Görsel özelliklerini doğrula
            is_valid, message = self.validate_image_properties(image)
            if not is_valid:
                return None, message
            
            # 3. Boyutlandırma
            image = self.resize_image(image)
            
            # 4. Kontrast iyileştirme (opsiyonel)
            if enhance_contrast:
                image = self.enhance_contrast(image)
            
            # 5. Gürültü azaltma (opsiyonel)
            if reduce_noise:
                image = self.reduce_noise(image, method='bilateral')
            
            # 6. Çıktıyı kaydet (eğer yol belirtilmişse)
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                cv2.imwrite(output_path, image)
            
            return image, "Normalizasyon başarılı"
            
        except Exception as e:
            return None, f"Normalizasyon hatası: {str(e)}"

def test_normalization():
    """Normalizasyon modülünü test eder."""
    normalizer = ImageNormalizer(target_size=1024)
    
    # Test görseli oluştur
    test_image = np.random.randint(0, 255, (800, 600, 3), dtype=np.uint8)
    test_path = "/tmp/test_image.jpg"
    cv2.imwrite(test_path, test_image)
    
    # Normalizasyon testi
    normalized, message = normalizer.normalize_image(test_path)
    
    if normalized is not None:
        print(f"✓ Normalizasyon testi başarılı: {message}")
        print(f"  Orijinal boyut: {test_image.shape}")
        print(f"  Normalize boyut: {normalized.shape}")
        return True
    else:
        print(f"✗ Normalizasyon testi başarısız: {message}")
        return False

if __name__ == "__main__":
    test_normalization()

