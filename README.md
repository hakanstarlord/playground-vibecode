# Tavla (2 Oyuncu, Mouse Kontrollü)

Bu proje `tavla.py` içinde Tkinter ile geliştirilmiş 2 kişilik tavla oyununu içerir.

## Özellikler
- Mouse ile taş seçme ve hedef haneye taşıma.
- Standart başlangıç dizilimi (15 taş).
- Zarlar her tur başlangıcında otomatik atılır.
- Oyuncu isterse **Hamleyi Bitir** butonuyla turu bitirir ve
  "Hamlen bitti mi?" onayı sorulur.
- Vurma (hit), bar'a gönderme, bar'dan geri giriş.
- Uygun durumda taş toplama (bear-off).

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
