# Tavla (2 Oyuncu, Mouse Kontrollü)

Bu proje `tavla.py` içinde Tkinter ile geliştirilmiş, masaüstünde çalışan 2 kişilik tavla oyununu içerir.

## Özellikler
- Mouse ile taş seçme ve hedef haneye taşıma.
- Ahşap görünümlü tavla tahtası (referans görsele yakın stil) ve pencereye göre daha ortalı yerleşim.
- Standart başlangıç dizilimi (15 taş).
- Zarlar her tur başlangıcında otomatik atılır.
- Metin yerine zar yüzleri için görsel zar arayüzü.
- Tur başında **zar GIF benzeri animasyonlu atış efekti**.
- Vurulan taşlar için orta BAR üzerinde görsel taş gösterimi.
- BAR'daki taşlara tıklayıp yeniden oyuna giriş (re-entry) yapılabilir.
- Hamle başına tek tek onay yok; oyuncu tüm hamlelerini yaptıktan sonra
  **HAMLELERİ ONAYLA** ile toplu onay verir.
- Tur onayı reddedilirse o tur yapılan hamlelerin tamamı geri alınır.
- Vurma (hit), bar'a gönderme, bar'dan geri giriş, taş toplama (bear-off).

## Çalıştırma
```bash
python3 tavla.py
```

## EXE üretme (Windows)
Önce PyInstaller kur:
```bash
pip install pyinstaller
```

Sonra tek dosya exe oluştur:
```bash
pyinstaller --onefile --windowed tavla.py
```

Oluşan dosya:
- `dist/tavla.exe`
