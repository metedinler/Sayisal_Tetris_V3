# Ogrenme Notu

Evet, mantığın doğru: robot zaten kısmen yenilerek ve hata yaparak öğreniyor. Bu yüzden “hemen davranış değişikliği şart” değil; önce mevcut öğrenmeyi izleyip karar vermek daha doğru yaklaşım.

Şu an öğrenme nasıl işliyor:
1. Robot her hamlede bir karar veriyor.
2. Hamle sonucu aldığı puan, öğrenme için ödül sinyali oluyor.
3. Model o ödüle göre iç parametrelerini güncelliyor.
4. Kötü hamlede düşük ödül aldığı için o karar yolu zamanla zayıflıyor.
5. İyi hamlede yüksek ödül aldığı için o karar yolu zamanla güçleniyor.

Önemli nokta:
1. Ceza, şu an çoğunlukla “ayrı bir eksi puan sayacı” olarak değil, düşük/başarısız ödül olarak dolaylı işliyor.
2. Yani sistem “ödül ağırlıklı öğrenme” yapıyor.
3. Bu nedenle kısa vadede robot bazen riskli ve kötü görünen hamle yapabilir, bu normal.

“Ödül, ceza, toplam skor ekranda görünüyor mu?” sorusunun net cevabı:
1. Toplam skorlar ekranda görünüyor.
2. Öğrenme güncelleme sayısı görünüyor.
3. Son eğitim hatası (error) görünüyor.
4. Strateji havuzu ve öneri motoru sayısı görünüyor.
5. Alttaki akış panelinde robot kararlarının uygulandı/reddedildi bilgisi görünüyor.
6. Ama “ödül puanı” ve “ceza puanı” ayrı iki sayaç olarak şu an doğrudan ayrı başlıkta gösterilmiyor.
7. Ceza etkisi daha çok karar kalitesi, risk ve düşük ödül üzerinden dolaylı takip ediliyor.

Öğrenme durumunu pratikte nasıl takip etmelisin:
1. Kısa vadede:
- Alttaki akış panelinde robotun karar açıklamalarını izle.
- Öneri stratejileri ne sıklıkla reddediliyor/uygulanıyor bak.
2. Orta vadede:
- 5-10 oyun sonunda robot skor trendine bak.
- Aynı senaryoda üste yığılma davranışı azalıyor mu kontrol et.
3. Uzun vadede:
- Log dosyalarında hamle başına puan, risk, karar tipi, öneri sonucu trendini incele.
- Model güncelleme sayısı artarken son eğitim hatasının genel eğilimini karşılaştır.

“Değişiklik yapmaya gerek var mı?” konusunda dengeli öneri:
1. Hemen şart değil, çünkü sistem zaten öğreniyor.
2. Önce birkaç oyunluk gerçek gözlem yap.
3. Eğer ısrarla aynı kötü davranışı sürdürürse, o zaman ödül/ceza tasarımını revize etmek anlamlı olur.
4. Şu an için en doğru yaklaşım: veri topla, trend gör, sonra karar ver.

## Sonraki Oneri
İstersen bir sonraki adımda sadece analiz amaçlı bir “izleme checklisti” hazırlayayım. Kod değiştirmeden, 10 oyun sonunda robotun gerçekten iyileşip iyileşmediğini objektif ölçen kısa bir tablo verebilirim.

## 2026-03-19 - Nasil Oynanir Ekrani Eklendi (Append-Only)

Yeni davranis:
1. Oyun acilisinda `Nasil Oynanir` ekrani otomatik acilir.
2. Ekranda `Bir daha gosterme` checkbox'i vardir.
3. Checkbox isaretlenirse tercih profile yazilir ve sonraki acilislarda ekran otomatik acilmaz.
4. Yardim menusu altina `Nasil Oynanir` secenegi eklendi; buradan her zaman manuel acilabilir.

Ekran icerigi:
1. Sum9 ve kilit patlamasi kurallari.
2. Combo carpanlari ve bomba+joker/kilit ek etkisi.
3. Ozel taslarin (B/J/L) ne yaptigi.
4. Oyunu kazanma kosullari.
5. Robotun genel karar mekanigi.
6. Modlar (Kolay/Normal/Zor/Gazi) ve profil farklari.
7. Robot ajanlarinin gorevleri.
8. Robotun oyun icinde nasil davrandigina dair ozet.

## 2026-03-19 - v3.9.0 Ogrenme Ozeti (Append-Only)

Bu surumde ogrenilen ve sabitlenen noktalar:
1. Bekleme/analiz akisinda kullanici beklentisi hizlidir; `B` ile duraklatip aninda analiz acilmasi daha anlasilir bir deneyim verir.
2. Aciklanabilirlik tek kaynaktan gelmez; rakip-gozlem + robot-gozlem + birlestirme ajanlari birlikte daha iyi karar aciklamasi uretir.
3. `H` penceresinde sadece hamle sonucu degil, stratejinin ne anlama geldigi ve neden secildigi de gosterilmelidir.
4. Oyun icinde `sonraki` ve `2 sonraki` bilgi akisi karar kalitesini arttirir.
5. SID tarafinda tek oynatici standardi (`sidplayfp`) bakim maliyetini dusurur; VLC dagitimdan cikarilmistir.

Yeni moduller ve etkileri:
1. `gazi_mode_agents.py`: 3 ajanli gozlem ve birlestirme.
2. `sid_player.py`: dogal track sonu gecisi + kapanista surec agaci temizligi.
3. `tetris_v3_windows_ai.py`: Gazi entegrasyonu, H analiz genisletmesi, baslangic yardim akisi, yerlesim iyilestirmeleri.
