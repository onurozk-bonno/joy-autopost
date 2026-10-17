---
name: make-reel
description: Bir görselden yazı katmanlı ve özgün müzikli 9:16 Reels videosu yapma tarifi (ffmpeg + numpy).
---
1. Kaydırma: `reel.py` → `make_reel(image, out, seconds=10)`; görsel 2112 yüksekliğe ölçeklenir,
   1080x1920 pencere x ekseninde %40→%100 kayar, 0.8 sn fade in/out, sessiz AAC izi.
2. Yazı katmanı (16 Ekim Cuma Reels'i referans): üstte `drawbox` y=ih*0.10 h=ih*0.28 black@0.28;
   satırlar DejaVuSerif-Italic 46px, sırayla 0.5 / 2.3 / 4.1 sn'de 0.8 sn fade ile; vurgu satırı
   DejaVuSerif-BoldItalic 72px 6.0 sn'de. Metni `textfile=` ile ver (Türkçe karakter/kesme işareti güvenli).
3. Müzik: numpy ile Am–F–C–G pad (2.5 sn/akor, yumuşak atak) + pentatonik pluck melodi + basit
   delay-reverb, 1 sn fade in / 1.2 sn fade out, tepe 0.6; `-map 0:v -map 1:a -c:v copy -c:a aac`.
4. Kontrol: ffprobe (1080x1920, h264, aac, süre), birkaç kareyi görüntüle — yazı kenara taşmamalı.
5. JSON: media_type "reel", caption + 5 hashtag.

## Kendini iyileştir
Bitirdiğinde `.claude/LEARNINGS.md`'yi oku ve `retro` skill'ine göre yeni dersi ekle; bu dosyada gerekli küçük düzeltmeyi PR ile öner.
