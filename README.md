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
