---
name: retro
description: Her görevin sonunda ders çıkarma ve ajan/skill'leri iyileştirme protokolü. Bir ajan veya skill işini bitirdiğinde, hata yaptığında ya da Onur düzeltme yaptığında kullan.
---
# Retro: kendini iyileştirme protokolü
**Ne zaman:** görev bitince; bir şey beklenmedik şekilde başarısız olunca; Onur bir şeyi düzeltince veya
beğenmeyince; bir workflow kırmızı olup çözülünce.

**Adımlar**
1. `.claude/LEARNINGS.md` oku (aynı hatayı tekrarlama).
2. Kendine sor: Ne işe yaradı? Ne zaman kaybettirdi? Hangi varsayım yanlıştı? Onur neyi düzeltti?
3. Ders genelleştirilebiliyorsa `.claude/LEARNINGS.md`'ye tek satır ekle:
   `- YYYY-MM-DD [ajan/skill adı] Durum → Ders → Ne yapılmalı`
4. Ders bir ajan/skill talimatını değiştirmeyi gerektiriyorsa o dosyayı küçük, somut bir diff ile
   düzenle. Aynı dersi 2. kez yaşadıysan talimata kalıcı olarak taşı.
5. Değişiklikleri **PR** olarak aç (başlık `retro: <konu>`). Doğrudan main'e push yok, kendi PR'ını
   merge etme; Onur inceler.

**Sınırlar (değiştirilemez)**
- CLAUDE.md "Değişmez kurallar" bölümüne, onay akışına, AI şeffaflığına, 5 hashtag sınırına ve sır
  kurallarına dokunan hiçbir "iyileştirme" yapılmaz; gevşetme önerisi PR yerine Onur'a sorulur.
- Sır, token, kişisel veri LEARNINGS'e yazılmaz (repo PUBLIC).
- Spekülasyon değil, gözlenen olay yaz. Emin olmadığın dersi "hipotez:" diye işaretle.
- Talimat dosyalarını şişirme: yeni ders eklerken eskisiyle çakışan/gereksiz satırı sil.
