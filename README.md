# BIST ML Analyzer — ilk çalışan prototip

Borsa İstanbul hisse kodu girerek 1, 5 veya 20 işlem günlük yön olasılığı hesaplayan Streamlit + scikit-learn prototipi.

## Gereksinimler
- Python 3.10–3.12 önerilir
- İnternet bağlantısı
- Yahoo Finance'ta bulunan BIST sembolleri genellikle `ASELS.IS` biçimindedir.

## Kurulum

### Windows
```powershell
cd bist_ml_analyzer
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### macOS / Linux
```bash
cd bist_ml_analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Tarayıcıda Streamlit'in gösterdiği yerel adres açılır (çoğunlukla http://localhost:8501).

## Nasıl kullanılır?
1. Hisse kodu alanına `ASELS`, `THYAO` veya `YYLGD` yazın.
2. Tahmin süresini 1, 5 ya da 20 işlem günü seçin.
3. **Analiz et** düğmesine basın.
4. Olasılıklar ve zaman sıralı test doğruluğu gösterilir.

## Modelin tanımı
- Veri: tarihsel günlük OHLCV verisi
- Özellikler: gecikmeli getiriler, hareketli ortalamaya göre fiyat, volatilite, RSI benzeri momentum ve hacim özellikleri
- Etiket: seçilen ufkun sonunda kapanışın mevcut kapanıştan yüksek olup olmadığı
- Algoritma: Random Forest
- Değerlendirme: zamana göre ayrılmış test kümesi; eğitim/test sınırı çevresinde tahmin ufku kadar boşluk bırakılır.

Bu ilk prototipte model analiz isteği sırasında yeniden eğitilir. Üretim sürümünde modeller zamanlanmış işlerle eğitilmeli, sürümlenmeli ve tahminler önbelleğe alınmalıdır.

## Önemli sınırlamalar
- Yahoo Finance/yfinance verisi bu projede yalnızca prototip içindir. Veri doğruluğu, gecikme, kullanım koşulları ve ticari yeniden dağıtım hakkı ayrıca doğrulanmalıdır. Ücretli bir üründe uygun lisanslı veri sağlayıcı kullanın.
- Model çıktıları yatırım tavsiyesi veya getiri garantisi değildir.
- Sadece doğruluk oranı model kalitesini açıklamaz. Üretime geçmeden önce Brier skoru, log loss, kalibrasyon, farklı piyasa dönemlerinde walk-forward testleri, işlem maliyetleri ve karşılaştırma baz çizgileri eklenmelidir.
- Bu prototipte giriş/üyelik, e-posta gönderimi, ödeme, abonelik kontrolü, veritabanı, yönetici paneli, izleme ve üretim güvenliği bulunmaz.
- Ücretli hizmete açmadan önce Türkiye sermaye piyasası mevzuatı, veri lisansları, KVKK ve tüketici/mesafeli hizmet yükümlülükleri konusunda uzman görüşü alın.

## Önerilen üretim mimarisi
- Frontend: React/Next.js veya Streamlit'in yerine daha gelişmiş web paneli
- API: FastAPI
- Veritabanı: PostgreSQL
- Arka plan işleri: Celery/RQ + Redis
- Model deposu: sürümlenmiş model artefaktları
- Kimlik doğrulama: güvenli e-posta doğrulaması ve oturum yönetimi
- Ödeme: Türkiye'de kullanılabilir bir ödeme sağlayıcısı; webhook ile abonelik durumunu doğrulama
- Dağıtım: Docker + HTTPS + log/izleme + yedekleme
