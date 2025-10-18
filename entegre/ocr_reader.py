import easyocr
import cv2
import numpy as np

class OCRReader:
    """EasyOCR kullanarak plaka metni okuma sınıfı."""
    
    def __init__(self, languages=["en"], gpu=False):
        """
        Args:
            languages (list): Tanınacak dillerin listesi (örn. ["en", "tr"]).
            gpu (bool): GPU kullanımı için True, CPU için False.
        """
        self.reader = easyocr.Reader(languages, gpu=gpu)
    
    def read_text(self, image):
        """Görselden metin okur."""
        # EasyOCR, doğrudan NumPy dizilerini kabul eder
        # Gerekirse, görseli gri tonlamaya dönüştürme veya eşikleme gibi ön işleme adımları eklenebilir.
        # Ancak EasyOCR genellikle bu tür işlemleri kendi içinde halleder.
        
        # Metin tespiti ve tanıma
        results = self.reader.readtext(image)
        
        detected_texts = []
        for (bbox, text, prob) in results:
            detected_texts.append({
                "text": text,
                "confidence": prob,
                "bbox": bbox.tolist() # NumPy dizisini listeye dönüştür
            })
        
        return detected_texts

def test_ocr_reader():
    """OCR okuyucu modülünü test eder."""
    # Basit bir test görseli oluştur (örneğin, "TEST123" yazan bir görsel)
    img = np.zeros((100, 300, 3), dtype=np.uint8)
    cv2.putText(img, "TEST123", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    
    ocr_reader = OCRReader(languages=["en"])
    detected_texts = ocr_reader.read_text(img)
    
    if detected_texts:
        print("✓ OCR testi başarılı:")
        for text_info in detected_texts:
            print(f"  Metin: {text_info['text']}, Güven: {text_info['confidence']:.2f}")
        return True
    else:
        print("✗ OCR testi başarısız: Metin tespit edilemedi.")
        return False

if __name__ == "__main__":
    test_ocr_reader()

