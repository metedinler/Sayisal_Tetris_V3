# Programci El Kitabi - Sayisal Tetris V3

## 1. Sistem Amaci
Sayisal Tetris V3, Windows GUI tabanli bir insan-robot karsilastirma oyunudur.
Mimari hedefleri:
- Eski surumlerden bagimsiz calisma
- Kurallarin korunmasi ve genisletilebilirligi
- Ogrenme motorunun kalici bellekle surekliligi
- Strateji uretimi ve karar gecidi ile adaptif robot davranisi

## 2. Ust Seviye Mimari
Ana moduller:
- Oyun motoru: tahta durumu, tas birakma, patlama ve puanlama
- Arayuz katmani: Tkinter canvas cizimi, menu, kisa yol tuslari
- Log katmani: benzersiz adli JSONL hamle kaydi
- Ogrenme katmani: mini ileri beslemeli sinir agi + online guncelleme
- Strateji katmani: aktif strateji havuzu + onerisi motorlari + karar mekanizmasi

Veri akisi:
1. Oyun turu baslar, ortak gelen/sonraki sayi belirlenir.
2. Insan ve robot kendi tahtalarinda hamle karari verir.
3. Taslar birakir, patlamalar ve puan hesaplanir.
4. Log yazilir, robot odulle online ogrenme adimi yapar.
5. Robot bellegi diske kaydedilir.

## 3. Oyun Kurallari ve Teknik Uygulama
Korunan kural seti:
- Sum-9 patlama (yatay/dikey komsu toplam 9)
- Kilit patlama (2x2 esit blok veya 4'lu dizi)
- Joker (cevre etkili secici patlatma)
- Bomba (yaricap 1 veya 2 alan etkisi)
- Combo carpani (2x, 3x, 4+)
- Yukari itme (seviye tabanli tetik)

Teknik uygulama detaylari:
- Tahta `ROWS x COLS` matrisidir, bos hucre `EMPTY=None` ile temsil edilir.
- Patlama dalgalari set tabanli hucre toplama ve tek geciste temizleme ile yapilir.
- Yercekimi sutun bazinda stack yeniden yerlestirme ile uygulanir.
- Gorsel patlama efekti, temizlenen hucrelerin kisa sureli beyaz flaş cizimi ile verilir.

## 4. Robot Mimarisi
Robot iki katmanli karar sistemi kullanir:

### 4.1 Ogrenme Motoru (MiniNN)
Model:
- Tip: Tek gizli katmanli ileri beslemeli yapay sinir agi
- Giris boyutu: 12 ozellik
- Gizli katman: 16 nöron, `tanh` aktivasyonu
- Cikis: Tek skaler hamle degeri (Q-benzeri degerleme)

Giris ozellikleri (ornek):
- Sutun indeksi (normalize)
- Mevcut sayi ve sonraki sayi (normalize)
- Sutun yuksekligi, tahta doluluk dengesi
- Bosluk (hole) orani
- Sum-9 ve kilit potansiyeli
- Dusuk yukseklik ve dusuk risk ozellikleri

Egitim:
- Online geri yayilim (backpropagation)
- Hata: `y - target`
- Hedef: hamle odulunden normalize edilmis hedef
- Ogrenme hizi: sabit katsayi ile adimli guncelleme
- Kesif/somuru dengesi: epsilon-greedy

Kalicilik:
- Agirliklar, biaslar, epsilon ve sayaçlar `ai_memory/robot_brain.json` dosyasina yazilir.
- Sonraki acilista model ayni dosyadan geri yuklenir.

### 4.2 Strateji Motoru
Yapi:
- 10 aktif strateji (agirlik vektoru tabanli)
- Her strateji, heuristik ozellikleri agirlikli toplayarak skor üretir.
- Strateji skorlari odul geri beslemesi ile guncellenir (exponential moving update).

Standart 10 strateji:
1. safe_stack: Guvenli yigma ve tasma riskini azaltma odakli.
2. max_potential: Patlama olasiligini yuksek tutma odakli.
3. balance: Risk ve puan dengesini orta noktada tutar.
4. combo_hunter: Zincirleme (combo) firsatlarini kovalar.
5. low_risk: Dusuk riskli sutunlari onceliklendirir.
6. center_control: Merkez sutun dengesini korumaya calisir.
7. edge_pressure: Kenar sutunlarda kontrollu baski kurar.
8. lock_builder: Kilit patlama kurulumlarini arttirmaya odaklanir.
9. sum9_focus: Toplam 9 patlamalarini onceliklendirir.
10. survival_mix: Tahta dolulugu arttiginda hayatta kalma agirlikli davranir.

Oneri Motorlari:
- 5 farkli onerisi motoru vardir.
- Her motor, baz stratejiyi farkli jitter ve focus katsayilari ile mutasyona ugratarak aday strateji üretir.
- Oneri sonucunda aday strateji + hedef sutun + guven degeri uretilir.

Oneri motoru yeni stratejiyi nasil gelistirir:
1. Once en iyi performans gosteren baz strateji secilir.
2. Secilen baz stratejinin agirliklari uzerine kucuk oynama (sapma (jitter)) uygulanir.
3. Motorun odagina gore agirliklar odak carpani (focus factor) ile guclendirilir veya zayiflatilir.
4. Ortaya cikan yeni agirlik seti aday strateji olarak adlandirilir.
5. Aday strateji tum uygun sutunlarda denenir ve tahmini hamle skoru hesaplanir.
6. En iyi sutun + guven puani ile robotun karar gecidine gonderilir.

Karar Gecidi (Decision Gate):
- Oneri skoru ile mevcut skor farki hesaplanir.
- Riske bagli esik degeri ile karsilastirilir.
- Guven + skor kazanci + risk kosullari saglanirsa onerilen strateji uygulanir.
- Saglanmazsa onerisi reddedilir.

Robot kararlarini nasil alir:
1. Her sutun icin ozellik cikartimi (feature extraction) yapar.
2. Ogrenme modeli her sutun icin hamle degeri uretir.
3. Strateji motoru ayni sutunlar icin kural tabanli skor uretir.
4. Iki skor birlestirilerek tek hamle puani elde edilir.
5. Kesif-somuru dengesi (exploration-exploitation) ile bazen yeni hamle dener, bazen en iyi hamleyi secer.
6. Oneri motorundan gelen yeni strateji varsa karar gecidi ile karsilastirma yapar.
7. Son karari verir, hamleyi uygular, odulu alir ve modeli gunceller.

Robot onerilen stratejiyi nasil degerlendirir:
1. Mevcut stratejinin puani baz puan olarak tutulur.
2. Onerilen strateji ayni durumda yeniden puanlanir.
3. Iki puan farki net kazanc olarak hesaplanir.
4. Durum riski kullanilarak dinamik esik belirlenir.
5. Oneri guveni, net kazanc ve risk birlikte kosul denetiminden gecirilir.
6. Kosullar gecerse "uygulandi", gecmezse "reddedildi" olarak kayitlanir.
7. Sonuc hem ekranda hem log kaydinda gorulecek sekilde tutulur.

## 5. Karar Agaci Mantigi
Robot karar agaci pratikte su sekilde isler:
1. Tum sutunlar icin ozellik vektoru olustur.
2. Her sutunda MiniNN cikisi al.
3. Aktif en iyi strateji ile heuristik skor hesapla.
4. Birlesik skorla baz hamleyi sec.
5. Oneri motorundan aday strateji al.
6. Adayin olasi hamle skorunu hesapla.
7. Decision gate ile uygula/reddet karari ver.
8. Hamleyi uygula, odulu al, modeli guncelle.

Bu yapi klasik karar agaci siniflandirmasi degildir; kural tabanli asamali karar agaci + ogrenmeli degerleme katmaninin hibritidir.

## 6. Bekleme Modu ve Arka Plan Analizi
Bekleme modu davranislari:
- `B` tusu veya menu ile ac/kapat.
- Kullanici 5 saniye hareketsizse log replay analizi tetiklenir.
- Bekleme modu acikse sadece analiz yapilir.
- Bekleme modu kapaliyse analiz sonrasi otomatik hamle akisi devam eder.

Log replay teknigi:
- Son log dosyalari taranir.
- Robot kayitlari secilir.
- Kayitli ozellik vektorleri ve oduller yeniden egitime verilir.
- Boylece offline benzeri pekistirme etkisi elde edilir.

## 7. Loglama Sistemi
Format:
- Her oyun icin benzersiz adli `.jsonl` dosyasi
- Her satir bir hamle kaydi

Kayit alanlari:
- tur, oyuncu, gelen/sonraki sayi
- tahta snapshot
- secilen strateji, acik strateji sayisi
- hamle karari (sutun, hiz modu, kaydirma)
- patlama sonucu ve puan
- risk, potansiyel patlama, oncelik
- onerisi detaylari ve uygulanma karari
- robot ozellik vektoru

## 8. Arayuz ve Gozlemlenebilirlik
Panel bileşenleri:
- Sol: insan tahtasi
- Sag: robot tahtasi
- Yanda: skor, seviye, kontrol yardimi, son onerisi, durum
- Alt panel: asagi akan robot akil yurutme akis gunlugu

Filtreleme:
- Tum akis
- Sadece oneriler
- Sadece reddedilen oneriler
- Sadece uygulanan oneriler

Bu sayede robotun canli calismasi ve karar mekanizmasi gozle gorulur hale gelir.

## 9. Kritik Fonksiyonlar
- `StrategyGenerator.suggest`: aday strateji uretimi
- `StrategyGenerator.decide_apply`: onerisi karar gecidi
- `RobotLearner.choose_action`: hibrit hamle secimi
- `RobotLearner.learn_from_move`: online ogrenme adimi
- `RobotLearner.analyze_previous_logs`: replay tabanli gecmis analiz egitimi
- `VersusGame.perform_turn`: oyun turu orkestrasyonu
- `VersusGame.get_filtered_reason_feed`: panel filtreleme mantigi

## 10. Performans ve Dayaniklilik
- Matris islemleri kucuk sabit boyutta oldugu icin tek thread GUI dongusunde yeterli performans verir.
- Replay analizinde dosya/hamle limiti kullanilarak donma riski azaltilir.
- Model kaydi her tur sonu yapilarak olasi kapanmalarda veri kaybi azaltilir.

## 11. Gelistirme Onerileri
### 11.1 Ogrenme modelini hedef ag (target network) ile stabilize etmek
Amac:
- Ogrenme adimlari arasinda ani yon degisimi sorununu azaltmak.

Neden gerekli:
- Ayni model hem karar verip hem kendini hemen guncellediginde hedef deger oynak olabilir.
- Bu durum ogrenmenin dalgali (unstable) ilerlemesine neden olur.

Onerilen yontem:
1. Iki ayri model tut: ana ag (online network) ve hedef ag (target network).
2. Karar verirken ana ag kullan.
3. Egitim hedefi hesaplarken hedef ag kullan.
4. Belirli aralikla yavas kopyalama (soft update) veya tam kopyalama (hard update) yap.

Beklenen sonuc:
- Daha duzgun kayip egrisi (loss curve), daha tutarli hamle kalitesi.

### 11.2 Strateji havuzu budama/yukseltme (pruning/promotion) mekanizmasi eklemek
Amac:
- Strateji havuzunun kontrolsuz buyuyup kaliteyi dusurmesini engellemek.

Neden gerekli:
- Her yeni oneri uzun vadede faydali olmayabilir.
- Dusuk kaliteli stratejiler karar alanini gereksiz sisirir.

Onerilen yontem:
1. Her strateji icin basari gostergesi (performance score) tut.
2. Alt esigin altinda kalanlari buda (pruning).
3. Ust esigi gecenleri ana havuza yukselterek terfi ettir (promotion).
4. Havuz boyutu ust limiti koy ve periyodik temizlik calistir.

Beklenen sonuc:
- Daha temiz strateji havuzu, daha hizli ve daha isabetli karar.

### 11.3 Log replay'i mini-grup (mini-batch) ve onceliklendirmeli ornekleme (prioritized sampling) ile guclendirmek
Amac:
- Gecmis deneyimlerden daha verimli ogrenmek.

Neden gerekli:
- Tum kayitlar esit degerde degildir; bazi hamleler daha ogreticidir.

Onerilen yontem:
1. Tek tek yerine mini-grup (mini-batch) halinde egitim yap.
2. Hata buyuklugune gore ornek onceligi (priority) belirle.
3. Onceligi yuksek kayitlardan daha sik ogren.
4. Sapma duzeltmesi (importance correction) ile dengeyi koru.

Beklenen sonuc:
- Ayni surede daha yuksek ogrenme verimi ve daha hizli adaptasyon.

### 11.4 Deterministik test senaryolari icin tohum (seed) sabitleme modu eklemek
Amac:
- Testleri tekrar edilebilir (reproducible) hale getirmek.

Neden gerekli:
- Rastgelelik nedeniyle ayni testte farkli sonuclar alinabilir.

Onerilen yontem:
1. Baslangicta rastgelelik tohumu (random seed) sabitleme secenegi ekle.
2. Test modunda sayi uretimi, oneriler ve karar adimlarini ayni seed ile calistir.
3. Loglara seed degerini yaz.
4. Hata tekrari icin "seed ile tekrar calistir" komutu sagla.

Beklenen sonuc:
- Hata ayiklama (debugging) ve karsilastirma testlerinde yuksek guvenilirlik.
