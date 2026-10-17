# Joy Autopost — Claude Code proje talimatı

@joytheafghanhound Instagram hesabı için yapay zekâ ile Joy (Afgan tazısı) içerikleri üreten ve
GitHub Actions üzerinden Instagram Graph API ile paylaşan sistem. Sahibi: Onur (onurozk-bonno).
Tüm konuşmalar Türkçe.

## Mimari (kısa)
- Repo: github.com/onurozk-bonno/joy-autopost (PUBLIC — Instagram görseli raw.githubusercontent'tan çeker)
- Düzen: `src/` (main.py, common.py, generate.py, instagram.py, reel.py, scene.py, claude_tasks.py,
  train_lora.py), `config/` (settings.yaml, scenes.yaml), `state/history.json`, `drafts/` kökte.
  Komutlar: `python src/main.py draft|publish|check|refresh-token`. Bağımlılıklar: `requirements.txt`
  (temel) + `requirements-claude.txt` (ANTHROPIC_API_KEY varsa) + `requirements-replicate.txt` (replicate backend).
- Görsel: Gemini (`gemini-2.5-flash-image`) + `refs/` içindeki Joy referans fotoğrafları.
- Taslak = `drafts/<YYYYMMDD-HHMM>.jpg|mp4` + aynı adlı `.json` (caption, media_type: image|reel).
- Paylaşım: başlığı `Taslak <id>` olan bir Issue'ya `onay` etiketi eklenince `publish.yml` paylaşır,
  linki yorum yazar, Issue'yu kapatır. Sadece repo sahibinin etiketi tetikler.
- Workflow'lar: `daily.yml` (her gün 15:43 UTC taslak + onay Issue'su), `publish.yml`, `maintenance.yml`
  (token testi/yenileme). `daily.yml` taslak üretemezse kırmızı
  olmaz; `taslak-hata` etiketli "Taslak üretilemedi" Issue'su açar/yorumlar.

## Değişmez kurallar
1. **Herkese açık paylaşım = Onur'un açık onayı.** `onay` etiketini Onur söylemeden ekleme.
2. **AI şeffaflığı:** AI görsel/videoda caption'da "Joy'un hayal sahnelerinden biri ✨" + `#aiart`.
   Gerçek fotoğrafta bu ifadeler KULLANILMAZ. Emin değilsen sor.
3. **En fazla 5 hashtag** (Instagram limiti, Aralık 2025): #afghanhound #joytheafghanhound
   + sahneye özel 1 + #aiart + (#afgantazısı | #sighthound).
4. Görsel oranı 4:5 (1080x1350), Reels 9:16 (1080x1920, H.264 + AAC, ses izi şart).
5. Sır/anahtar asla repoya, loga veya sohbete yazılmaz. Hepsi GitHub Secrets'ta.
6. Joy: mavi-gri kıvırcık/dalgalı tüy, krem göğüs, benekli namlu, uzun püsküllü kulak, halka kuyruk,
   tasmasız (gerçek fotolarda turuncu göğüs tasması olabilir).

## Secrets / Variables
Secrets: IG_ACCESS_TOKEN, IG_USER_ID (17841460947654690), GEMINI_API_KEY,
(opsiyonel) ANTHROPIC_API_KEY, GH_ADMIN_TOKEN, REPLICATE_API_TOKEN.
Variables: IMAGE_BACKEND, GEMINI_MODEL, POST_MODE (approval|auto), CLAUDE_MODEL.

## Ayrıntı
HANDOVER.md (durum, yol haritası, açık işler) ve `.claude/skills/*` (tarifler).
