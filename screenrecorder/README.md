\# Windows Ekran Kaydedici (Python)



Bu depoya `screen\_recorder.py` adlı basit bir ekran kayıt aracı eklendi.



\## Özellikler

\- Tüm monitörü video olarak kaydetme

\- FPS ayarı

\- Monitör seçimi

\- İsteğe bağlı süre (`--duration`)

\- `Ctrl+C` ile manuel durdurma

\- Kayıt başında ve sonunda videonun tam dosya yolunu yazdırma



\## Kurulum



```bash

python -m pip install -r requirements.txt

```



\## Kullanım



Varsayılan ayarlarla kayıt başlatma:



```bash

python screen\_recorder.py

```



Belirli bir dosyaya, 60 FPS ile ve 10 saniye kayıt:



```bash

python screen\_recorder.py --output kayit.mp4 --fps 60 --duration 10

```



İkinci monitörü kaydetme:



```bash

python screen\_recorder.py --monitor 2

```



\## Kaydedilen videoya nasıl ulaşırım?



\- `--output` parametresi vermezsen dosya, komutu çalıştırdığın klasöre kaydedilir.

\- Program kayıt başında ve sonunda video dosyasının \*\*tam yolunu\*\* yazdırır.

\- Örnek çıktı:



```text

Kayıt başladı: C:\\Users\\Kullanici\\Desktop\\recording\_20260101\_120000.mp4

...

Video dosyası: C:\\Users\\Kullanici\\Desktop\\recording\_20260101\_120000.mp4

```



İstersen doğrudan Masaüstüne kaydetmek için şöyle çalıştırabilirsin:



```bash

python screen\_recorder.py --output "%USERPROFILE%\\Desktop\\kayit.mp4"

```



\## Notlar

\- Bu araç Windows üzerinde çalışacak şekilde hedeflenmiştir.

\- Bazı sistemlerde `mp4v` codec'i sınırlı olabilir. Gerekirse codec değiştirilebilir.



