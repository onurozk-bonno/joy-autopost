---
name: publish-draft
description: Bir taslağı GitHub onay akışıyla Instagram'da yayınlama adımları.
---
1. `drafts/<id>.(jpg|mp4)` + `drafts/<id>.json` main dalında olmalı (id: YYYYMMDD-HHMM).
2. Onur'un AÇIK onayını al (görsel + caption gösterilerek).
3. `gh issue create --title "Taslak <id>" --label onay --body "<kısa açıklama>"`
4. `publish.yml` tetiklenir: görsel → publish_image, reel → publish_reel (video işlenmesi birkaç dk).
5. Bitince Issue'ya "Paylaşıldı: <link>" yorumu düşer ve Issue kapanır. Link'i Onur'a ilet.
6. Reels'te Instagram AI etiketini kontrol ettir (API ekleyemiyor).
Hata ayıklama: `gh run view --log-failed`. Sık hatalar: görsel oranı 4:5 dışında, video ses izi yok,
token süresi dolmuş (maintenance.yml ile test et).

## Kendini iyileştir
Bitirdiğinde `.claude/LEARNINGS.md`'yi oku ve `retro` skill'ine göre yeni dersi ekle; bu dosyada gerekli küçük düzeltmeyi PR ile öner.
