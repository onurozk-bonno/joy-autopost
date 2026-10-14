"""Joy LoRA eğitimini Replicate'te başlatır.

Kullanım (bir kez, bilgisayardan veya GitHub Actions'tan):
  export REPLICATE_API_TOKEN=...
  python training/train_lora.py --zip training/joy_photos.zip --owner REPLICATE_KULLANICI_ADIN

joy_photos.zip: Joy'un 10-20 net fotoğrafı (tasmasız tercih edilir, insan yok).
Eğitim ~20-30 dk sürer; bitince çıkan "owner/joy-flux:versiyon" değerini
GitHub'da REPLICATE_MODEL değişkenine yaz.
"""
from __future__ import annotations

import argparse

import replicate

TRAINER = "ostris/flux-dev-lora-trainer"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--zip", required=True)
    p.add_argument("--owner", required=True, help="Replicate kullanıcı adın")
    p.add_argument("--name", default="joy-flux")
    p.add_argument("--steps", type=int, default=1200)
    args = p.parse_args()

    dest = f"{args.owner}/{args.name}"
    try:
        replicate.models.create(owner=args.owner, name=args.name, visibility="private", hardware="gpu-t4")
        print(f"Model oluşturuldu: {dest}")
    except Exception as e:  # already exists
        print(f"Model zaten var ya da oluşturulamadı ({e}); devam ediliyor.")

    trainer = replicate.models.get(TRAINER)
    version = trainer.latest_version.id
    with open(args.zip, "rb") as f:
        training = replicate.trainings.create(
            version=f"{TRAINER}:{version}",
            input={
                "input_images": f,
                "trigger_word": "JOYDOG",
                "steps": args.steps,
                "lora_rank": 16,
                "learning_rate": 0.0004,
                "autocaption": True,
                "autocaption_prefix": "a photo of JOYDOG, an Afghan hound,",
            },
            destination=dest,
        )
    print(f"Eğitim başladı: https://replicate.com/p/{training.id}")
    print("Bitince REPLICATE_MODEL değişkenine modelin 'owner/name:version' değerini yaz.")


if __name__ == "__main__":
    main()
