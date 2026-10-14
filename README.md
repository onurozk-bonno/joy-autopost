# Joy Autopost

@joytheafghanhound için her gün yapay zekâ ile Joy görseli üretip Instagram'da paylaşan sistem.

## Akış
1. **Sahne seçimi**: `config/scenes.yaml` içinden mevsime uygun, son 10 paylaşımda olmayan bir sahne seçilir.
2. **Görsel**: Joy'un LoRA modeli (Replicate) ile 4:5 fotoğraf üretilir.
3. **Kalite kontrolü**: Claude görseli inceler, bozuksa en fazla 3 kez yeniden üretilir.
4. **Caption**: Claude TR + EN caption ve hashtag yazar ("Joy'un hayal sahneleri" ve #aiart dahil).
5. **Onay modu** (varsayılan): GitHub'da "Taslak …" başlıklı bir Issue açılır. **onay** etiketini eklersen paylaşılır, Issue'yu kapatırsan iptal edilir.
6. **Otomatik mod**: `POST_MODE` değişkenini `auto` yaparsan direkt paylaşır.

## GitHub ayarları
**Settings → Secrets and variables → Actions**

Secrets:
| Ad | Ne |
|---|---|
| `IG_ACCESS_TOKEN` | Meta panelindeki "Generate token" ile alınan token |
| `IG_USER_ID` | `17841460947654690` |
| `REPLICATE_API_TOKEN` | replicate.com → Account → API tokens |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API keys |
| `GH_ADMIN_TOKEN` | (isteğe bağlı) token'ı otomatik yenilemek için |

Variables:
| Ad | Ne |
|---|---|
| `REPLICATE_MODEL` | LoRA eğitimi bitince `kullanici/joy-flux:versiyon` |
| `POST_MODE` | `approval` veya `auto` |
| `CLAUDE_MODEL` | (isteğe bağlı) kullanılacak Claude modeli |

## Çalıştırma
- **Actions → Gunluk Joy paylasimi → Run workflow**: hemen bir taslak üretir.
- **Actions → Token kontrol ve yenileme → Run workflow**: Instagram bağlantısını test eder.
- Saat: her gün 18:43 (İstanbul). Değiştirmek için `daily.yml` içindeki `cron` satırı.

## Not
Depo **public** olmalı: Instagram görseli `raw.githubusercontent.com` adresinden çeker. Depoda gizli bilgi yoktur; tüm anahtarlar GitHub Secrets'ta durur.
