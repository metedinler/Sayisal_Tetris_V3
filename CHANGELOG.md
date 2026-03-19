# CHANGELOG - Sayisal Tetris V3

Bu dosya append-only tutulur.

Kurallar:
- Yeni kayitlar dosyanin sonuna eklenir.
- Mevcut kayitlar silinmez.
- Guncellemeler tarih + surum + ozet formatinda yazilir.

## 2026-03-18 - v3.8.1 Hotfix
- Acilis sirasinda `self.root` olusmadan oyuncu adi dialogu acildigi icin olusan hata duzeltildi.
- Hata: `AttributeError: 'VersusGame' object has no attribute 'root'`.
- `self.root = root` atamasi oyuncu adi alma akisindan onceye alindi.

## 2026-03-18 - v3.8
- Kalici oyuncu profil sistemi eklendi (`ai_memory/player_profile.json`).
- Oyuncu adi bir kez sorulup tekrar kullanilacak sekilde saklandi.
- Mac board istatistikleri eklendi: toplam mac, W/L, berabere, en yuksek skorlar, en yuksek seviye.

## 2026-03-18 - Son Oyun Iyilestirmeleri
- Oyun sonu yeniden baslatma (`R`) eklendi.
- Pencere boyutlandirma ve dinamik panel yerlestirme iyilestirildi.
- Bekleme modunda replay analizine insan loglari da dahil edildi.
- Insan/robot icin farkli patlama ses ve flash efektleri eklendi.
- "Planlanan Ozellik Kontrolu" alani ekrandan kaldirildi.
- Patlayan hucrelerde lokal +X/X+ hucre efekti guclendirildi.

## 2026-03-18 - Oyun Sonu Sonuc + Puanlama Iyilestirme
- Oyun sonu kazanan metni netlestirildi: `Tebrikler <OyuncuAdi> kazandi`, `Tebrikler Robot kazandi`, `Mac berabere bitti`.
- Oyun sonu paneline `Neden:` satiri eklendi; bitis kosulu acikca gosterilir.
- Kazananin skordan degil bitis kuralindan gelebilecegi durumlar icin aciklayici not eklendi.
- Coklu patlama puanlamasi merkezi sabitlere tasindi (sum9/kilit/joker/bomba/combo carpani).
- Puanlama sabitleri degistiginde robotun online + replay ile yeniden uyumlanacagi dokumante edildi.

## 2026-03-18 - Arayuz Yerlesim Duzeni
- Robot akil yurutme akisi paneli saga dogru daraltildi.
- Ayni panel daha yukari konuma cekildi.
- Tur/seviye + gelen/sonraki sayi bloklari iki tahta arasindaki orta panele tasindi.
- Kontroller basligi orta panelde en uste alindi.
- Robot strateji gorunurlugune `ACIK/KAPALI` durum metinleri eklendi.

## 2026-03-18 - Ses Modlari ve SID Muzik
- Kontroller bolumu sag panelde Profil ve Robot Durumu alaninin ustune tasindi.
- Oyun acilisinda ekran boyutu ekran cozumune gore hesaplanarak ilk yerlesim tasmasi azaltildi.
- Ses modu secenekleri eklendi: Sesiz, Muziksiz, Efektsiz, Sadece Uyari, Tam Ses.
- Tam Ses modunda EXE yanindaki `sid/` klasorunden SID dosyalari sira ile calinir.
- SID playlist ve son calinan kaydi kalici dosyalarda tutulur; bir sonraki acilista bir sonraki SID'den devam edilir.
- Yeni SID dosyalari playlist bozulmadan sona eklenir, liste bitince basa doner.

## 2026-03-18 - SID Modulu Ayrimi
- SID oynatma kodu ayri modulde toplandi: `sid_player.py`.
- HVSC player listesinden komut satiri playlist icin secilen player `sidplay-fp` (`sidplayfp`) olarak sabitlendi.
- Tam Ses modunda SID dosyalari harici player sureci ile track-track oynatilir.

## 2026-03-18 - SID Surec Hotfix + Panel Ince Ayar
- SID sureci Windows'ta gizli pencere ile baslatildi; oyun sirasinda ayri terminal penceresi gorunmesi engellendi.
- Oyun kapanisinda SID surec agaci zorla kapatilarak muzik surecinin artakta kalmasi duzeltildi.
- SID parca akisina parca basi sure limiti eklendi; sure dolunca otomatik olarak bir sonraki parcaya gecis saglandi.
- Robot Akil Yurutme Akisi paneli iki sayi yuksekligi kadar daha asagi alinip panel gorunen alani kucultuldu.
- Guncel kod ile EXE yeniden derlendi.

## 2026-03-18 - SID Parca Sonu Gecis Duzeltmesi
- 25 saniye zorunlu parca degistirme kaldirildi.
- SID gecisi artik sadece calan parcasi dogal olarak bittiginde yapilir.
- Oynatici cagrisi `-os` secenegi ile tek parca davranisina alindi.
- EXE yeniden derlendi ve dist artefacti olusturuldu.

## 2026-03-19 - Surekli Dusus + AI Mod/Profil Guncellemesi
- Surekli dusus mekanigi oyun genelinde aktif hale getirildi.
- Asagi tusu aktif turde hem insan hem robot tasini bir adim hizlandirir.
- Oyun modu menusu `Kolay / Normal / Zor` AI ogrenme zorlugu olacak sekilde duzenlendi.
- Robot profil secimi eklendi: `Dengeli / Agresif / Savunmaci`.
- Ogrenme verisi silinmeden odul-ceza ve kural bonusu mode bagli sekilde uygulanmaya baslandi.
- `Tum Loglari Isle (Uzun Surer)` menusu ile toplu replay egitimi eklendi.
- Yukari itme davranisi sutun bazli fiziksel kaydirma mantigina yaklastirildi.

## 2026-03-19 - Zor Mod Skor Maksimizasyonu ve Profil Gorunurlugu
- Zor modda robot karar puanina acik skor-itkisi biasi eklendi (patlama potansiyeli + skor odakli agirliklandirma).
- Agresif/savunmaci/dengeli profil farklari secim skoruna dogrudan yansitildi; davranis ayrimi daha belirgin hale getirildi.
- Oneri degerlendirmesinde zor mod ek puanlama katsayilari guclendirildi; uygun durumda onerinin uygulanma olasiligi arttirildi.
- Tur sonu `guided_reward` zor modda skor farki ve profil odakli ceza/bonuslarla guncellendi.
- Sag panelde oyun modu, robot profili, aktif hedef, profil davranisi ve skor/guvenlik itkisi canli olarak gosterilmeye baslandi.

## 2026-03-19 - v3.9.0 Gazi Modu, Aciklanabilir AI ve Dagitim
- `Gazi` modu eklendi; mevcut modlarla birlikte secilebilir yapida sunuldu.
- Yeni 3-ajan mimarisi eklendi (`gazi_mode_agents.py`): rakip gozlem, robot gozlem, karar birlestirme.
- `B` tusu davranisi guclendirildi: oyun akisi beklemeye alinip analiz aninda baslatilir.
- `H` analiz penceresi genisletildi: strateji anlami, onerinin kaynagi, ajan birlesim ciktilari ve karar gerekcesi gorunur.
- Oyun arayuzunde `sonraki` + `2 sonraki` bilgi akisi netlestirildi.
- Tahta baslik cizimi ust bantta yeniden duzenlenerek alan cakismasi duzeltildi.
- SID oynatma altyapisi `sidplayfp` standardina baglandi; dagitimdaki `Sid/vlc-3.0.23-win64.exe` kaldirildi.
- Dokumantasyon guncellendi: README, ogrenme notu ve programci el kitabi yeni moduller/gorevler ve surum davranislari ile senkronize edildi.
- EXE yeniden derlenip yeni dagitim artefakti olusturuldu.
