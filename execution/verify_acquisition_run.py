import os
import sys
import json
import hashlib
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "Reference Templates"

def verify_all():
    errors = []
    total_folders_checked = 0
    total_accepted_files = 0

    target_folders = sorted([d for d in TEMPLATES_DIR.iterdir() if d.is_dir() and d.name not in ["02_T1_SMALL_Cialis", "31_Kamagra_Template_Reference", "32_Viagra_Template_Reference"]])

    print(f"Verifying {len(target_folders)} acquisition target folders...")

    for d in target_folders:
        total_folders_checked += 1

        # Check for leftover _tmp_* files
        tmp_files = list(d.glob("_tmp_*"))
        if tmp_files:
            errors.append(f"{d.name} contains leftover temp files: {[f.name for f in tmp_files]}")

        # Check report existence
        report_path = d / "_acquisition_report.json"
        if not report_path.exists():
            errors.append(f"{d.name} missing _acquisition_report.json")
            continue

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception as e:
            errors.append(f"{d.name}/_acquisition_report.json is invalid JSON: {e}")
            continue

        accepted = report.get("accepted", [])
        images_on_disk = [p for p in d.iterdir() if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"] and not p.name.startswith("_tmp_")]

        # Image budget check (<= 6)
        if len(images_on_disk) > 6:
            errors.append(f"{d.name} has {len(images_on_disk)} images, exceeding cap of 6")

        # Verify each accepted record against disk
        if len(accepted) != len(images_on_disk):
            errors.append(f"{d.name} report accepted count ({len(accepted)}) != images on disk ({len(images_on_disk)})")

        for idx, rec in enumerate(accepted, start=1):
            total_accepted_files += 1
            filename = rec.get("file")
            file_path = d / filename

            if not file_path.exists():
                errors.append(f"{d.name} report references non-existent file: {filename}")
                continue

            with open(file_path, "rb") as f:
                file_bytes = f.read()

            actual_sha = hashlib.sha256(file_bytes).hexdigest()
            actual_bytes = len(file_bytes)

            with Image.open(file_path) as img:
                actual_w, actual_h = img.size

            if actual_sha != rec.get("sha256"):
                errors.append(f"{d.name}/{filename} SHA256 mismatch: report={rec.get('sha256')}, actual={actual_sha}")

            if actual_bytes != rec.get("bytes"):
                errors.append(f"{d.name}/{filename} bytes mismatch: report={rec.get('bytes')}, actual={actual_bytes}")

            if actual_w != rec.get("width") or actual_h != rec.get("height"):
                errors.append(f"{d.name}/{filename} dimensions mismatch: report={rec.get('width')}x{rec.get('height')}, actual={actual_w}x{actual_h}")

    print(f"Summary: Verified {total_folders_checked} target folders, {total_accepted_files} accepted files.")
    if errors:
        print("VERIFICATION FAILED WITH ERRORS:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("ALL SELF-VALIDATION CHECKS PASSED CLEANLY!")
        return True

if __name__ == "__main__":
    success = verify_all()
    if not success:
        sys.exit(1)
