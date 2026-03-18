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
- Robot kayitlari secilir. kullanicinin oyunlarinin loglari menuden analiz yap ile yapilir.
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

## 12. Telif ve Not
Zuhtu Mete DINLER
@2026
Tum Haklari Saklidir.
zmetedinler@gmail.com

VAO dan ogrendiklerim, kendi bildigim, biraz eski oyunlar, birazda arastirma, ve gpt codex 5.3 yardimiyla yazildi.

## 13. Surum Sonrasi Teknik Ekler (Append-Only)

Bu bolum son guncellemeleri silmeden, sadece ekleyerek takip etmek icin ayrilmistir.

### 13.1 Son Eklenen Sistem Davranislari
- Oyun sonu ayni oturumda yeniden baslatma (`R` ve menu komutu) eklendi.
- Pencere boyutlandirma aktif edildi; panel yerlesimi pencere boyutuna gore dinamik hale getirildi.
- Alt akis panelinde satir sarma ve sinir hesaplari iyilestirildi.
- Bekleme modundaki replay egitimine insan loglari da dahil edildi.
- Kalici oyuncu profil sistemi eklendi (`ai_memory/player_profile.json`).
- Mac board metrikleri kalici hale geldi: toplam mac, W/L, berabere, en yuksek skorlar, en yuksek seviye.

### 13.2 Patlama Efekti Iyilestirmeleri
- Insan ve robot patlamalari icin farkli ses kaliplari eklendi.
- Patlayan hucrelerde yanip sonen hucre bazli lokal efekt guclendirildi.
- Taraf bazli tahtaya lokal overlay flash uygulandi (global tum ekran yerine ilgili tahta).
- Hucre icinde +X / X+ marker efekti ile patlama oncesi/ani gorunurluk arttirildi.

### 13.3 Arayuz Sadeleştirme
- "Planlanan Ozellik Kontrolu" paneli kaldirildi.
- Alt akis paneli, sag bilgi panelindeki metinlerin bittigi satirdan sonra baslayacak sekilde konumlandirildi.

### 13.4 Dokumantasyon Kurali
- README ve Programci El Kitabi metinleri append-only bakim modeli ile guncellenir.
- Yeni degisiklikler silme olmadan yeni baslik/alt baslik eklenerek yazilir.
- Kalici degisiklik gunlugu `CHANGELOG.md` dosyasinda tutulur ve yeni kayitlar sona eklenir.

## 14. Oyun Sonu Sonuc Gosterimi ve Puanlama Notlari (Append-Only)

### 14.1 Kazanan metni
- Oyun sonu durumunda `status` alani kisa ve net kazanan metni verir:
	- `Tebrikler <OyuncuAdi> kazandi`
	- `Tebrikler Robot kazandi`
	- `Mac berabere bitti`
- Ayrica `game_end_reason` metni ile bitis nedeni (`Neden:` satiri) ayri gosterilir.
- Bu ayirim, "skor daha dusuk ama kazandi" gibi durumlari aciklar; kazanan bitis kurali ile belirlenir.

### 14.2 Merkezi puan sabitleri
Puanlama degerleri kodun basinda sabitlenmistir:
- `SUM9_PAIR_POINTS`
- `LOCK_PATTERN_POINTS`
- `LOCK_EXTRA_CELL_POINTS`
- `UP_PUSH_LOCK_BONUS`
- `UP_PUSH_COLLISION_BASE`
- `UP_PUSH_COLLISION_EXTRA`
- `JOKER_BASE_POINTS`
- `JOKER_AROUND_POINTS`
- `BOMB_BASE_POINTS`
- `BOMB_PER_CELL_POINTS`
- `COMBO_MULT_TWO`, `COMBO_MULT_THREE`, `COMBO_MULT_FOUR_PLUS`

Bu yapi ile puan dagilimi tek yerden degistirilebilir.

### 14.3 Ogrenme etkisi
- Puan sabitleri degistiginde odul fonksiyonu da degismis olur.
- Robot online ogrenme ve replay analizi ile yeni odul dagilimina yeniden adapte olur.
- Erken oyunda top-2 kesif mekanizmasi hizli yeniden uyumlanmayi destekler.

## 15. Arayuz Yerlesim Guncellemesi (Append-Only)

### 15.1 Orta bilgi paneli
- Tur/seviye ve gelen-sonraki sayi kutulari sag panelden alinarak iki tahta arasindaki orta bolgeye tasindi.
- Kontroller basligi orta bolumde en ust satira yerlestirildi.

### 15.2 Akil yurutme paneli konumu
- Robot Akil Yurutme Akisi paneli saga dogru daraltilmis ve dikeyde yukari alinmistir.
- Amaç: ust uste binmeyi azaltmak ve alt panelin daha erken gorunmesini saglamak.

### 15.3 Strateji acik/kapali gorunurlugu
- Ekranda su alanlar eklendi:
	- `Strateji Slotlari: ACIK n / KAPALI m`
	- `Oneri Kapisi: ACIK/KAPALI`
- Bu alanlar robotun o anki strateji kullanim durumunu gozlenebilir yapar.

## 16. SID Muzik ve Ses Modlari (Append-Only)

### 16.1 Ses modlari
- `silent`: muzik ve efekt kapali.
- `no_music`: efekt acik, muzik kapali.
- `no_effects`: muzik acik, efekt kapali.
- `warning_only`: mevcut bip tabanli uyari efektleri acik.
- `full`: SID muzik + gelismis dalga (wave) tabanli efekt sesleri acik.

### 16.2 SID playlist yonetimi
- SID dizini: EXE yaninda `sid/`.
- Playlist dosyasi: `ai_memory/sid_playlist.txt`.
- Durum dosyasi: `ai_memory/sid_state.json`.
- Her acilista dizin taranir; yeni SID dosyalari liste sonuna eklenir.
- Son calinan track kaydedilir; sonraki acilista bir sonraki track ile devam edilir.
- Liste bitince dairesel olarak basa doner.

### 16.3 Teknik not
- SID calicisi `python-vlc` kutuphanesi ile yonetilir.
- Ses modu degisimi menuden aninda uygulanir ve `ai_memory/audio_settings.json` icinde saklanir.

### 16.4 Modul ayrimi ve player secimi
- SID calma mantigi ana oyundan ayrilarak `sid_player.py` modulune tasinmistir.
- HVSC players listesinden komut satiri playlist icin secilen player: `sidplay-fp` (`sidplayfp`).
- Uygulama Tam Ses modunda `sidplayfp <dosya.sid>` cagrisi ile sarkilari tek tek calistirir.

## 17. SID Surec ve Panel Hotfixleri (Append-Only)

### 17.1 SID surec yonetimi
- Windows ortaminda `sidplayfp` sureci terminal penceresi acmadan (hidden/no-window) baslatilir.
- Oyun kapanisinda SID ana sureci ve olasi alt surecleri kapatilir; kapanis sonrasi muzik devam etmez.
- Cikis akisinda ek guvenlik icin surec temizligi zorlamali olarak uygulanir.

### 17.2 SID playlist akisi
- SID parcalarinin tek parca uzerinde kalmasini engellemek icin parca basi sure limiti uygulanir.
- Sure doldugunda bir sonraki parcaya gecilir ve playlist dairesel devam eder.
- Bu davranis `Tam Ses` modunda otomatik akisin kesintisiz devam etmesini hedefler.

### 17.3 Robot bildirim paneli boyutu
- `Robot Akil Yurutme Akisi` panelinin baslangic Y konumu iki sayi yuksekligi kadar daha asagi alinmistir.
- Boylece panelin gorunen yuksekligi azaltilarak ust panelle cakisma riski dusurulmustur.

### 17.4 SID parca sonu gecis duzeltmesi
- 25 saniye zorunlu parca degistirme davranisi kaldirildi.
- SID gecisi yalnizca aktif parca dogal olarak bittiginde tetiklenir.
- Oynatici cagrisi tek-parca davranisi icin `-os` secenegi ile yapilir.
