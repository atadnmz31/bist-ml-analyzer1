import streamlit as st
from market_model import analyze_ticker, TickerDataError

st.set_page_config(page_title="BIST ML Analyzer", page_icon="📈", layout="centered")

st.title("BIST Hisse Analiz Paneli")
st.caption("Makine öğrenmesi tabanlı araştırma prototipi · Yatırım tavsiyesi değildir")

with st.sidebar:
    st.header("Analiz ayarları")
    ticker = st.text_input("BIST hisse kodu", value="ASELS").strip().upper()
    horizon = st.selectbox(
        "Tahmin süresi",
        options=[1, 5, 20],
        format_func=lambda x: f"{x} işlem günü"
    )
    st.info("Veri kaynağı: Yahoo Finance üzerinden alınan tarihsel günlük veriler. Ticari yayına almadan önce veri lisansını doğrulayın.")

if st.button("Analiz et", type="primary", use_container_width=True):
    if not ticker or not ticker.replace(".", "").isalnum():
        st.error("Lütfen geçerli bir hisse kodu girin (ör. ASELS).")
    else:
        with st.spinner("Geçmiş veriler indiriliyor, model eğitiliyor ve test ediliyor..."):
            try:
                result = analyze_ticker(ticker, horizon)
                st.session_state["analysis_result"] = result
            except TickerDataError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Analiz sırasında beklenmeyen bir hata oluştu: {exc}")

result = st.session_state.get("analysis_result")
if result:
    if result["ticker"] != ticker or result["horizon"] != horizon:
        st.caption("Görüntülenen sonuç önceki seçime ait. Yeni seçim için “Analiz et” düğmesine basın.")
    st.divider()
    st.subheader(f'{result["ticker"]} · {result["horizon"]} işlem günü')
    c1, c2 = st.columns(2)
    c1.metric("Yükseliş olasılığı", f'{result["up_probability"]:.1%}')
    c2.metric("Düşüş olasılığı", f'{result["down_probability"]:.1%}')
    st.write(f'**Model yorumu:** {result["direction"]}')
    st.write(f'**Son kapanış:** {result["last_close"]:,.2f}')
    st.write(f'**Veri tarihi:** {result["data_date"]}')
    st.write(f'**Zaman sıralı test doğruluğu:** {result["test_accuracy"]:.1%}' if result["test_accuracy"] is not None else "**Test doğruluğu:** Hesaplanamadı")
    st.write(f'**Test örneği sayısı:** {result["test_samples"]}')
    st.caption(
        "Olasılıklar model çıktısıdır; garanti veya kesinlik ifade etmez. Geçmiş performans gelecekteki sonuçları garanti etmez. "
        "Test doğruluğu, olasılıkların kalibrasyonu ile aynı şey değildir."
    )
    with st.expander("Model hakkında"):
        st.markdown(
            "- Model: Random Forest sınıflandırıcısı\n"
            "- Özellikler: geçmiş getiriler, hareketli ortalamalar, volatilite, RSI benzeri momentum ve hacim değişimleri\n"
            "- Hedef: seçilen ufkun sonunda kapanışın bugünkü kapanıştan yüksek olup olmadığı\n"
            "- Değerlendirme: zaman sıralı eğitim/test ayrımı; gelecek verisi eğitim örneklerine karıştırılmaz\n"
            "- Bu prototip haber, bilanço, temettü etkisi veya işlem maliyetlerini modellemez."
        )

st.divider()
st.caption("Ticari kullanım öncesi: lisanslı piyasa verisi, kullanıcı kimlik doğrulama, abonelik/ödeme altyapısı, güvenlik, kayıt/audit ve mevzuat incelemesi eklenmelidir.")
