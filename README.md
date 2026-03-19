# Sayisal Tetris V3 (Windows AI Versus)

## Turkce

### Ozet
Bu surum, eski oyundan ayri bir klasorde gelistirildi.
Insan ve robot ayni turda ayni gelen sayi ve ayni sonraki sayi bilgisi ile oynar.
Oyun pencereli (Windows GUI) calisir.

### Ana Ozellikler
- Buyuk tahta: 18x8 (onceki Windows oyunu ile ayni boyut)
- Insan ve robot icin iki ayri tahta
- Ayni sayi akisi: her turda her ikisi de ayni sayiyi alir
- Sayi araligi: `0-9` (0 dahil)
- Kurallar: sum-9 patlama, kilit patlama, joker, bomba, combo, yukari itme
- Patlama gorsel efekti
- Robot online ogrenir ve onceki ogrendiklerini kaydeder
- 5 saniye kullanici beklerse robot gecmis loglari tekrar ederek analiz yapar
- Loglar benzersiz adlarla `logs/` klasorune yazilir
- Ogrenme motoruna ek olarak strateji onerici motoru vardir
- 10 aktif robot stratejisi bulunur
- 5 farkli strateji onerisi motoru bulunur
- Robotun onerisi ekranda gorulur (uygulandi / reddedildi)
- Oyunun altinda akan robot akil yurutme paneli vardir
- Ozellikler menusu + Hakkinda penceresi vardir
- Bekleme modu `B` tusu veya menuden acilip kapanir

### Kontroller
- `A` veya `Sol Ok`: sola kaydir
- `D` veya `Sag Ok`: saga kaydir
- `Space` veya `Enter`: normal birak
- `S` veya `Asagi Ok`: hizli birak
- `B`: bekleme modu ac/kapat
- `Q` veya `Esc`: cikis

### Oyun Sonu Kurallari
- Ekranin en ust satirina ilk ulasan kaybeder.
- Tahtasinda 1 veya 0 tas kalan taraf kazanir.
- Iki taraf ayni anda ust satira ulasirsa berabere olur.
- Iki taraf ayni anda 1/0 tasa inerse berabere olur.

### Menu
- `Ozellikler` -> `Bekleme Modu (B)`
- `Ozellikler` -> `Simdi Log Analizi`
- `Yardim` -> `Hakkinda`

### Calistirma
```bat
run_v3_windows.bat
```
veya
```bat
py tetris_v3_windows_ai.py
```

### Deneme Akisi
1. Oyunu acin.
2. `A` / `D` ile konumu secin.
3. `S` ile hizli, `Space` ile normal birakma yapin.
4. `B` ile bekleme modunu acip 5 saniye bekleyin.
5. Alt panelde robot akil yurutme akisini izleyin.
6. `Ozellikler -> Akil Yurutme Filtresi` ile filtre deneyin.

### Dosya Yapisi
- `tetris_v3_windows_ai.py`: Ana oyun
- `run_v3_windows.bat`: Baslatici
- `logs/`: Oyun loglari (benzersiz isimli)
- `ai_memory/`: Robot ogrenme durumu

## English

### Summary
This version is developed in a separate folder to avoid mixing with older versions.
Human and robot play in parallel with the same current and next numbers per turn.
The game runs in a Windows GUI window.

### Main Features
- Large board: 18x8 (same size as previous Windows version)
- Separate boards for human and robot
- Same number stream for both players each turn
- Number range: `0-9` (including 0)
- Rules: sum-9 explosion, lock explosion, joker, bomb, combo, upward push
- Visual explosion effect
- Robot learns online and persists memory across sessions
- If user is idle for 5 seconds, robot replays previous logs for self-analysis
- Logs are saved with unique names under `logs/`
- Strategy proposal engine works together with learning engine
- 10 active robot strategies are available
- 5 distinct strategy proposal engines are available
- Proposal status is shown on screen (applied / rejected)
- A scrolling robot reasoning feed is shown at the bottom
- Features menu + About dialog are included
- Wait mode can be toggled with `B` key or from menu

### Controls
- `A` or `Left`: move left
- `D` or `Right`: move right
- `Space` or `Enter`: normal drop
- `S` or `Down`: fast drop
- `B`: toggle wait mode
- `Q` or `Esc`: quit

### End Conditions
- The side that reaches the top row first loses.
- The side that remains with 1 or 0 pieces on its board wins.
- If both reach the top row simultaneously, the match is a draw.
- If both reach 1/0 pieces simultaneously, the match is a draw.

### Run
```bat
run_v3_windows.bat
```
or
```bat
py tetris_v3_windows_ai.py
```

### Quick Test Flow
1. Launch the game.
2. Move with `A` / `D`.
3. Drop with `S` (fast) or `Space` (normal).
4. Toggle wait mode with `B` and stay idle for 5 seconds.
5. Watch the robot reasoning stream in the bottom panel.
6. Test filters from `Features -> Reasoning Filter`.

## Dokumantasyon Eki (Append-Only)

Asagidaki maddeler son surumlerde eklenen davranislari aciklar. Bu bolum append mantigi ile buyutulur, mevcut metin silinmez.

### Son Eklenen Davranislar (TR)
- Oyun sonrasinda uygulamayi kapatmadan yeni maca gecis eklendi (`R` / menu).
- Pencere yeniden boyutlandirmaya acildi ve panel yerlesimi dinamik hale getirildi.
- Robot akil yurutme panelinde yazi tasmasini azaltmak icin satir sarma uygulandi.
- Bekleme modu replay analizine robot kayitlarina ek olarak insan kayitlari da dahil edildi.
- Kalici oyuncu profili eklendi: oyuncu adi, toplam mac, kazanma/kaybetme, en yuksek skor ve seviye.
- Patlama geri bildirimi gelistirildi: ses + hucre bazli flash + taraf bazli (insan/robot) farkli efekt.
- "Planlanan Ozellik Kontrolu" bolumu ekrandan kaldirildi.

### Recent Additions (EN)
- In-session restart after game over was added (`R` / menu).
- Window resizing was enabled and panel layout was made dynamic.
- Reasoning feed wrapping was improved to reduce overlap.
- Idle replay analysis now learns from both robot and human logs.
- Persistent player profile was added: name, total matches, wins/losses, best score and level.
- Explosion feedback was improved with sound + cell-local flash + side-specific (human/robot) effects.
- The on-screen "Planned Features Check" block was removed.

### Degisiklik Gunlugu
- Bu proje icin kalici degisiklik gunlugu dosyasi: `CHANGELOG.md`
- Kural: Yeni kayitlar dosyanin sonuna append edilir; mevcut kayitlar silinmez.

## Oyun Sonu ve Puanlama Eki (Append-Only)

### Kazanan Belirleme (TR)
- Oyun sonunda ekranda acik sonuc metni gosterilir:
	- `Tebrikler <OyuncuAdi> kazandi`
	- `Tebrikler Robot kazandi`
	- `Mac berabere bitti`
- Sonuc satirinin altinda `Neden:` alani ile bitis kurali gosterilir.
- Bu oyunda kazanan her zaman en yuksek skora gore belirlenmez; bitis kurallari (ust satir / 1-0 tas) onceliklidir.

### Multi-Patlama Puanlama (TR)
- Sum-9 eslesmesi: `SUM9_PAIR_POINTS`
- Kilit patlama temel puani: `LOCK_PATTERN_POINTS`
- Kilit ekstra hucre puani: `LOCK_EXTRA_CELL_POINTS`
- Joker puani: `JOKER_BASE_POINTS + JOKER_AROUND_POINTS * cevre_hucre`
- Bomba puani: `BOMB_BASE_POINTS + BOMB_PER_CELL_POINTS * temizlenen_hucre`
- Combo carpani:
	- 2 patlama: `COMBO_MULT_TWO`
	- 3 patlama: `COMBO_MULT_THREE`
	- 4+ patlama: `COMBO_MULT_FOUR_PLUS`

### Puan Degisirse Robot Tekrar Ogrenir mi? (TR)
- Evet. Odul dagilimi degistiginde robot yeni puanlara gore online olarak tekrar uyumlanir.
- Bekleme modu replay analizi de yeni odul dagilimini pekistirir.
- Ilk oyunlarda hizli adaptasyon icin ilk iki iyi secenekten kesif mekanizmasi acik kalir.

### Winner and Scoring Note (EN)
- End-of-match now shows explicit winner text and reason line.
- Winner may differ from score leader because rule-based end conditions have priority.
- Explosion scoring constants are centralized for easier tuning; changing them will cause the learner to adapt again over time.

## Arayuz Yerlesim Eki (Append-Only)

### Son guncelleme (TR)
- Robot Akil Yurutme Akisi paneli saga dogru daraltildi ve yukariya cekildi.
- Tur/seviye/anlik sayi (Gelen/Sonraki) gostergeleri insan ve robot tahtalari arasindaki orta panele alindi.
- Kontroller metni orta panelde en ustte konumlandirildi.
- Robot strateji durumu ekranda acik/kapali olarak gosterilir:
	- Strateji slotlari: `ACIK x / KAPALI y`
	- Oneri Kapisi: `ACIK` veya `KAPALI`

### Latest layout update (EN)
- Reasoning feed panel was narrowed toward the right and moved upward.
- Turn/level/current-next number indicators were moved into a centered middle panel between boards.
- Controls header is now placed at the top of that middle panel.
- Robot strategy usage visibility now includes OPEN/CLOSED style labels on screen.

## Ses ve Muzik Eki (Append-Only)

### Yeni ses modlari (TR)
- Sesiz: muzik yok, efekt yok.
- Muziksiz: efekt var, SID muzik yok.
- Efektsiz: SID muzik var, efekt yok.
- Sadece Uyari: mevcut bip/uyari efektleri aktif, SID muzik yok.
- Tam Ses: SID muzik + gelismis efekt sesleri aktif.

### SID calisma kurali (TR)
- EXE ile ayni klasorde `sid/` altindaki `.sid` dosyalari okunur.
- Her acilista liste yenilenir ve `ai_memory/sid_playlist.txt` dosyasina yazilir.
- Yeni gelen SID dosyalari mevcut liste bozulmadan sona eklenir.
- Son calinan SID bilgisi `ai_memory/sid_state.json` dosyasina yazilir.
- Uygulama yeniden acildiginda son calinandan degil, bir sonrakinden devam eder.
- Liste sonuna gelince basa doner.

### Arayuz notu (TR)
- Kontroller bolumu sag panelde, Profil ve Robot Durumu alaninin ustune tasinmistir.
- Orta panelde tur/seviye ve gelen-sonraki sayi kutulari korunmustur.

### SID player secimi (TR)
- SID oynatma artik ayri modulde yonetilir: `sid_player.py`.
- HVSC player listesine gore komut satiri playlist icin secilen player: `sidplay-fp` (`sidplayfp`).
- Tam Ses modunda `sidplayfp` komutu ile SID dosyalari sira ile oynatilir.

## SID ve Panel Hotfix Eki (Append-Only)

### 2026-03-18 - Son hotfixler (TR)
- SID oynatici sureci Windows tarafinda gizli pencere ile baslatilir; oyun acikken ayri terminal penceresi gorunmez.
- Oyun kapanisinda SID sureci ve alt surecleri zorla kapatilarak muzik artakta kalmasi engellenir.
- SID parcalari tek parcada kalmayacak sekilde otomatik ilerler; her parcada sure siniri uygulanip bir sonraki parcaya gecilir.
- Robot Akil Yurutme Akisi paneli iki sayi yuksekligi kadar daha asagi alinip gorunur yukseklik kucultuldu.

### 2026-03-18 - Latest hotfixes (EN)
- SID player now starts with hidden console window on Windows.
- On game exit, SID process tree is force-closed to prevent lingering background music.
- SID playback now rotates to the next track automatically with a bounded per-track duration.
- Robot reasoning feed panel was lowered further by about two-number height and its visible area reduced.

### 2026-03-18 - SID transition adjustment (TR/EN)
- TR: 25 saniye zorunlu parca gecisi kaldirildi. Gecis artik sadece SID parcasi dogal olarak bittiginde yapilir.
- EN: The forced 25-second track switch was removed. Transition now occurs only when the current SID track ends naturally.

## Oynanis ve AI Mod Eki (Append-Only)

### 2026-03-19 - Oynanis akisi (TR)
- Surekli dusus mantigi oyun genelinde aktiftir: insan ve robot taslari ayni tur akisi icinde adim adim asagi iner.
- Dusus sirasinda insan tasi saga/sola yonlendirilebilir.
- Asagi tusu normal mod akisinda hem insan hem robot aktif tasina bir adim hizlandirma uygular.
- Yukari itme davranisi sutun bazli fiziksel kaydirma ile duzeltildi; tek hucre hafiza kaymasi etkisi azaltildi.

### 2026-03-19 - Oyun modu ve robot profili (TR)
- Menüde oyun modu `Kolay / Normal / Zor` olarak AI egitim zorlugu secimi icin kullanilir.
- Robot profili ayri menuden secilir: `Dengeli / Agresif / Savunmaci`.
- Mod secimi surekli dususu kapatmaz; sadece AI ogrenme/karar davranisini degistirir.

### 2026-03-19 - Ogrenme notlari (TR)
- Mevcut ogrenme belleği korunur; `ai_memory` dosyalari silinmez.
- Kolay mod agirlikli odul odaklidir.
- Normal mod odul + orta seviye ceza (geri kalma/risk) ile egitilir.
- Zor mod odul + daha guclu ceza + kural bonusu (patlama/risk) ile egitilir.
- `Ozellikler -> Tum Loglari Isle (Uzun Surer)` ile loglar toplu replay egitimine alinabilir.

## Zor Mod ve Profil Davranisi Eki (Append-Only)

### 2026-03-19 - Davranis netlestirmesi (TR)
- Zor modda robot secimi dogrudan skor maksimizasyonuna biaslanmistir.
- Karar puani icine patlama potansiyeli + skor itkisi + risk duzeltmesi birlikte eklenmistir.
- Agresif profil daha cok patlama/skor baskisi uygular.
- Savunmaci profil daha dusuk riskli kurulumlari onceliklendirir.
- Dengeli profil iki yaklasimi orta duzeyde birlestirir.
- Sag panelde `Hedef`, `Profil davranisi`, `Skor itkisi` ve `Guvenlik itkisi` canli gorunur.
