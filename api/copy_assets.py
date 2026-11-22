import os
import shutil
import glob
from pathlib import Path

base_dir = Path(__file__).resolve().parent
img_dir = base_dir / "app" / "static" / "img"
img_dir.mkdir(parents=True, exist_ok=True)

brain_dirs = [
    Path(r"C:\Users\Anuj\.gemini\antigravity-ide\brain\8bd5c50b-1175-4e97-aa88-78ec69ee7b60"),
    Path(r"C:\Users\Anuj\.gemini\antigravity-ide\brain\3cff87c6-a456-462e-a7c4-603850fab267"),
]

aliases = {
    "hero_athlete.jpg": "hero_bodybuilder_*.jpg",
    "program_strength.jpg": "program_strength_*.jpg",
    "program_muscle.jpg": "program_muscle_*.jpg",
    "program_trainer.jpg": "program_trainer_*.jpg",
    "bench_lockout.jpg": "bench_press_phase1_*.jpg",
    "bench_bottom.jpg": "bench_press_bottom_*.jpg",
    "bench_phase2.jpg": "bench_press_phase2_*.jpg",
    "gym_strength_zone.jpg": "gym_strength_zone_*.jpg",
    "gym_cardio_deck.jpg": "gym_cardio_deck_*.jpg",
    "gym_functional_zone.jpg": "gym_functional_zone_*.jpg",
    "gym_recovery_spa.jpg": "gym_recovery_spa_*.jpg",
}

for b in brain_dirs:
    if not b.exists():
        continue
    for dest, pat in aliases.items():
        dest_p = img_dir / dest
        if not dest_p.exists():
            matches = list(b.glob(pat))
            if matches:
                try:
                    shutil.copy(matches[0], dest_p)
                    print(f"Copied {matches[0].name} -> {dest}")
                except Exception as e:
                    print(f"Error copying {dest}: {e}")

print("Assets synced.")
