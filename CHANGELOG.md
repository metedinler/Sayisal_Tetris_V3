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
