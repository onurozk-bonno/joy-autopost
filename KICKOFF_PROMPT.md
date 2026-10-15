Joy Autopost reposundasın. Önce CLAUDE.md ve HANDOVER.md'yi oku.

Hafta 1 işlerini alt ajanlarla PARALEL yürüt, her biri kendi dalında (git worktree) çalışsın:

1. **repo-maintainer**: Kök dizindeki dosyaları src/, config/, state/ düzenine taşı; joy-autopost.zip
   ve __pycache__ sil; .gitignore ekle; workflow'lardaki yolları güncelle; `python -m py_compile`
   ve kuru çalıştırma (`python src/main.py draft` sahte görsel üreticiyle) ile doğrula. PR aç.
2. **content-producer**: `daily.yml`'ı `workflow_dispatch` ile bir kez çalıştır (gh workflow run),
   logu oku; Gemini hatası varsa nedenini raporla ve generate.py'de düzelt (ayrı PR).
3. **reel-editor**: reel.py'a `--text` (çok satırlı, sırayla beliren yazı) ve `--music` (özgün,
   numpy ile üretilmiş ambient) seçeneklerini ekle; Hayırlı Cumalar Reels'ini referans al. PR aç.
4. **growth-analyst**: Instagram Insights API ile son 3 paylaşımın erişim/kaydetme/hashtag
   verisini çeken `insights.py` ve haftalık `insights.yml` workflow'u yaz. PR aç.

Kurallar: Hiçbir şeyi Instagram'da yayınlama, `onay` etiketi ekleme, secret yazma.
Bitince her PR'ın özetini ve Onur'un yapması gereken manuel adımları (ör. GH_ADMIN_TOKEN) tek
listede ver.
