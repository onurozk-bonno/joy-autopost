# Joy Autopost — Handover (16 Ekim 2026)

## 1. Yapılanlar
| Alan | Durum |
|---|---|
| Instagram | Professional hesap, kategori "Dijital İçerik Üreticisi", profil AI etiketi KAPALI (gerçek+AI karışık akış) |
| Meta | Uygulama `joytry` (App ID 1082242791476971), Instagram API with Instagram Login, `instagram_business_content_publish` izni, @joytheafghanhound Instagram Tester (kabul edildi) |
| Token | IG long-lived token ~14 Ekim'de alındı → ~60 gün geçerli (~13 Aralık). GitHub Secrets'ta. |
| GitHub | Repo public, 3 workflow, onay-Issue akışı uçtan uca çalışıyor |
| Görsel | Gemini referanslı üretim kodu hazır; `refs/joy_01_trail.jpg`. İlk gerçek Gemini çalıştırması `common.py` hatası yüzünden düştü, düzeltildi, YENİDEN TEST EDİLMEDİ |
| Reels | `reel.py` (ffmpeg kaydırma+fade+ses izi), `publish_reel` — ilk Reels başarıyla paylaşıldı |
| Paylaşımlar | Patika (DefYh00gfKU, AI etiketli, caption'da 9-11 hashtag var), Sahil (Dehg5hwmk6-), Hayırlı Cumalar Reels (DehsCB8CQ-e) |
| Doküman | Claude Doc "Joy Autopost: Durum ve Reels Planı" + Hashtag stratejisi |

## 2. Bekleyen hazır taslaklar
- `drafts/20261015-2001` ayçiçeği (görsel), `20261015-2003` şelale (görsel), `20261015-2004` göl Reels (yazısız).
- Yerel: Masaüstü/JOYAI → joyvideo.mp4, ormanvideo.mp4 (10 sn dikey, gerçek mi AI mı → Onur'a sor),
  JOYsunset.jpeg == joygolkenari.jpeg (aynı dosya, gün batımı eksik).

## 3. Bilinen sorunlar / riskler
- Repo kökünde çöp: `joy-autopost.zip`, `__pycache__/` → sil, `.gitignore` ekle.
- `daily.yml` Gemini ile hiç başarıyla koşmadı → manuel `Run workflow` ile test et, logu oku.
- Token yenileme: `maintenance.yml` yeniler ama secret'ı yazmak için GH_ADMIN_TOKEN gerek; yoksa ~13 Aralık'ta paylaşım durur.
- API ile yüklenen Reels'e Instagram AI etiketi otomatik gelmeyebilir → kontrol listesi.
- Fallback caption'daki `hash()` Python'da süreçten sürece değişir (rotasyon rastgele) — sorun değil ama deterministik yapılabilir.

## 4. Yol haritası
**Hafta 1 — Sağlamlaştırma**
1. Repo düzeni: src/, config/, state/ klasörlerine taşı; zip ve __pycache__ sil; .gitignore.
2. Gemini taslağını uçtan uca test et; QC olmadan çıkan görselleri onay modunda değerlendir.
3. GH_ADMIN_TOKEN (fine-grained, sadece bu repo, Secrets: write) → token yenileme otomatik.
4. Bekleyen taslakları (2001, 2003, 2004) Onur'un seçtiği günlere planla.

**Hafta 2 — Reels otomasyonu**
5. `daily.yml`'a haftada 2-3 gün Reels modu: görsel → `reel.py` → reel taslağı.
6. Yazı katmanı + özgün müzik üretimini `reel.py`'a taşı (bugün elle yapıldı: drawtext + numpy ambient).
7. Opsiyonel: Veo ile görselden gerçek hareketli video (ücretli, faturalandırma gerekir).

**Hafta 3 — Kalite ve ton**
8. ANTHROPIC_API_KEY ile Claude QC + sahneye özel caption'ı aç.
9. Özel gün takvimi: Cuma, bayramlar, mevsim geçişleri → özel caption/yazı katmanı.

**Hafta 4+ — Büyüme**
10. Insights: haftalık rapor (erişim, kaydetme, hashtag'den gelen görüntülenme) → Issue veya Doc.
11. Hashtag 3. ve 5. yuvayı veriye göre değiştir.
12. Paylaşım saatini veriye göre optimize et; auto moda geçişi değerlendir.

## 5. Claude Code ile paralel çalışma
`.claude/agents/` altında 5 alt ajan, `.claude/skills/` altında 4 skill var. Başlangıç promptu:
`KICKOFF_PROMPT.md`.
