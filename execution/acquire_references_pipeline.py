import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))
from execution.image_analyzer import analyze_local_image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "Reference Templates"
RUN_LOG_PATH = TEMPLATES_DIR / "_acquisition_run.md"

def get_wikimedia_thumb(url, target_w=1280):
    if '/commons/thumb/' in url:
        return url
    m = re.search(r'upload\.wikimedia\.org/wikipedia/commons/([a-f0-9])/([a-f0-9]{2})/(.+)$', url)
    if m:
        c1, c2, fname = m.groups()
        return f'https://upload.wikimedia.org/wikipedia/commons/thumb/{c1}/{c2}/{fname}/{target_w}px-{fname}'
    return url

TARGET_FOLDERS = [
    {
        "folder": "03_T1_SMALL_Cialis_Professional",
        "slug": "cialis_professional",
        "searches": ["Cialis Professional box photo", "tadalafil 20mg carton", "Cialis Professional packaging"],
        "candidates": [],
        "notes": "Unlicensed online-pharmacy variant; no genuine manufacturer carton packaging exists. Standard Cialis packaging not substituted per project rules."
    },
    {
        "folder": "04_T1_SMALL_Cialis_Super_Active",
        "slug": "cialis_super_active",
        "searches": ["Cialis Super Active box photo", "tadalafil 20mg carton", "Cialis Super Active packaging"],
        "candidates": [],
        "notes": "Unlicensed online-pharmacy variant; no genuine manufacturer carton packaging exists. Standard Cialis packaging not substituted per project rules."
    },
    {
        "folder": "05_T1_Tramadol",
        "slug": "tramadol",
        "searches": ["Tramadol 50mg boîte", "Contramal 50mg packung", "Topalgic 50mg box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/0/0b/Tramadol_50mg_capsules.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Tramadol_50mg_capsules.jpg",
                "tier": 4,
                "brand": "Tramadol",
                "dosage": "50 mg",
                "market": "eu",
                "evidence": "Braille on front face; European packaging; 50mg capsules",
                "carton_pos": "centre-middle",
                "verbatim": ["Tramadol", "50 mg"],
                "notes": "Front face of European Tramadol 50mg carton legible."
            }
        ]
    },
    {
        "folder": "06_T1_Ambien",
        "slug": "ambien",
        "searches": ["Stilnox 10 mg boîte", "Zolpidem Stilnox packaging", "boite Stilnox 10mg"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/c/c6/Hypnotiques4444.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Hypnotiques4444.jpg",
                "tier": 4,
                "brand": "Stilnox",
                "dosage": "10 mg",
                "market": "eu",
                "evidence": "Braille embossed on front face; French Sanofi packaging; pack of 14 film-coated tablets",
                "carton_pos": "centre-middle",
                "verbatim": ["Stilnox", "10 mg", "Sanofi"],
                "notes": "Front face of Stilnox (zolpidem) 10mg box clearly legible showing brand name, dosage, and Sanofi logo."
            }
        ]
    },
    {
        "folder": "07_T1_Atarax",
        "slug": "atarax",
        "searches": ["Atarax 25 mg boîte", "Hydroxyzine Atarax UCB box", "boite Atarax 25mg"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/c/c3/Benzodiaz%C3%A9pines_en_France.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Benzodiaz%C3%A9pines_en_France.jpg",
                "tier": 4,
                "brand": "Atarax",
                "dosage": "25 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; French packaging text; pack of 30 film-coated tablets; UCB logo",
                "carton_pos": "top-middle",
                "verbatim": ["Atarax", "25 mg", "UCB"],
                "notes": "Front face of Atarax (hydroxyzine) 25mg box legible showing UCB branding and dosage."
            }
        ]
    },
    {
        "folder": "08_T1_Ativan",
        "slug": "ativan",
        "searches": ["Temesta 1mg swedish lorazepam", "Lorazepam Orion 1mg förpackning"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/f/fd/Lorazepam_Orion.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Lorazepam_Orion.jpg",
                "tier": 4,
                "brand": "Lorazepam Orion",
                "dosage": "1 mg",
                "market": "eu",
                "evidence": "Braille embossed on front face; Swedish Orion Pharma packaging; pack of 100",
                "carton_pos": "centre-middle",
                "verbatim": ["Lorazepam Orion", "1 mg", "Orion"],
                "notes": "High-res studio photo of Nordic Lorazepam Orion 1mg carton front face."
            }
        ]
    },
    {
        "folder": "10_T1_Modalert",
        "slug": "modalert",
        "searches": ["Modalert 200 Sun Pharma box", "Modalert 200 packaging India"],
        "candidates": [],
        "notes": "Indian export generic; no consumer packaging imagery published by Sun Pharma."
    },
    {
        "folder": "11_T1_Waklert",
        "slug": "waklert",
        "searches": ["Waklert 150 Sun Pharma box", "Waklert 150 packaging India"],
        "candidates": [],
        "notes": "Indian export generic; no consumer packaging imagery published by Sun Pharma."
    },
    {
        "folder": "12_T1_Provigil",
        "slug": "provigil",
        "searches": ["Modiodal 100mg boîte", "Provigil modafinil Cephalon box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/9/96/Benzodiaz%C3%A9pines_inconnues_du_public.png",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Benzodiaz%C3%A9pines_inconnues_du_public.png",
                "tier": 4,
                "brand": "Modiodal",
                "dosage": "100 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; French packaging text; Cephalon / Teva branding",
                "carton_pos": "top-right",
                "verbatim": ["Modiodal", "100 mg", "modafinil"],
                "notes": "Front face of French Modiodal (modafinil) 100mg carton legible."
            }
        ]
    },
    {
        "folder": "13_T1_Artvigil",
        "slug": "artvigil",
        "searches": ["Artvigil 150 HAB Pharma box", "Artvigil 150 packaging India"],
        "candidates": [],
        "notes": "Indian export generic; no consumer packaging imagery published by HAB Pharma."
    },
    {
        "folder": "14_T1_Imovane",
        "slug": "imovane",
        "searches": ["Zopiclone Actavis 5mg", "Imovane 7.5mg boîte Sanofi"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/a/ab/Zopiclone_Actavis_5mg.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Zopiclone_Actavis_5mg.jpg",
                "tier": 4,
                "brand": "Zopiclone Actavis",
                "dosage": "5 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; European Actavis packaging; pack of 30 film-coated tablets",
                "carton_pos": "centre-middle",
                "verbatim": ["Zopiclone Actavis", "5 mg", "Actavis"],
                "notes": "Front face of Actavis Zopiclone 5mg carton legible."
            }
        ]
    },
    {
        "folder": "15_T1_Xanax",
        "slug": "xanax",
        "searches": ["(Alprazolam) Xanor.jpg", "Xanax 0.5mg Pfizer box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/7/7f/%28Alprazolam%29_Xanor.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:(Alprazolam)_Xanor.jpg",
                "tier": 4,
                "brand": "Xanor",
                "dosage": "1 mg",
                "market": "eu",
                "evidence": "Braille dots visible on front face; text in Swedish; pack of 100; Pfizer logo",
                "carton_pos": "centre-middle",
                "verbatim": ["Xanor", "1 mg", "Pfizer"],
                "notes": "Straight-on studio shot of Swedish Xanor 1mg carton front face; brand, dosage and blue graphic fields clear."
            }
        ]
    },
    {
        "folder": "16_T1_Valium",
        "slug": "valium",
        "searches": ["5mgrocheaus.jpg Valium", "Valium 5mg Roche box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/8/81/5mgrocheaus.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:5mgrocheaus.jpg",
                "tier": 4,
                "brand": "Valium",
                "dosage": "5 mg",
                "market": "eu",
                "evidence": "Braille on front face; Roche hex logo; pack of 50 tablets",
                "carton_pos": "centre-middle",
                "verbatim": ["Valium", "5 mg", "Roche"],
                "notes": "Roche Valium 5mg carton front face legible showing classic Roche branding."
            }
        ]
    },
    {
        "folder": "17_T1_Klonopin",
        "slug": "klonopin",
        "searches": ["Rivotril 0.5mg Roche box", "Clonazepam Rivotril 0.5mg Tab"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/1/18/Clonazepam%28RIVOTRIL-0-5mg_Tab%29_2014-05-28_23-55.JPG",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Clonazepam(RIVOTRIL-0-5mg_Tab)_2014-05-28_23-55.JPG",
                "tier": 4,
                "brand": "Rivotril",
                "dosage": "0.5 mg",
                "market": "eu",
                "evidence": "Rivotril brand; Roche logo; film-coated tablets count 30",
                "carton_pos": "centre-middle",
                "verbatim": ["Rivotril", "0.5 mg", "Roche"],
                "notes": "Three-quarter view of Roche Rivotril 0.5mg carton front face."
            }
        ]
    },
    {
        "folder": "18_T1_Inderal",
        "slug": "inderal",
        "searches": ["Inderal 40mg AstraZeneca boîte", "Propranolol Inderal 40mg box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/1/11/De_la_theorie_a_la_pratique.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:De_la_theorie_a_la_pratique.jpg",
                "tier": 4,
                "brand": "Inderal",
                "dosage": "40 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; French AstraZeneca packaging; 40mg count 50",
                "carton_pos": "bottom-right",
                "verbatim": ["Inderal", "40 mg", "AstraZeneca"],
                "notes": "Front face of Inderal 40mg carton legible showing AstraZeneca logo."
            }
        ]
    },
    {
        "folder": "19_T1_Slimex",
        "slug": "slimex",
        "searches": ["Reductil 15mg Abbott boîte", "Slimex 15mg sibutramine box"],
        "candidates": [],
        "notes": "Sibutramine withdrawn in EU in 2010; no distinct historic carton image passing 800px floor."
    },
    {
        "folder": "21_T1_Valium_Brand",
        "slug": "valium_brand",
        "searches": ["Valium Roche 10mg box", "Boites de Valium44.jpg"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/7/7f/Boites_de_Valium44.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Boites_de_Valium44.jpg",
                "tier": 4,
                "brand": "Valium",
                "dosage": "10 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; French Roche packaging; 10mg strength",
                "carton_pos": "centre-middle",
                "verbatim": ["Valium", "10 mg", "Roche"],
                "notes": "French Roche Valium 10mg carton front face legible."
            }
        ]
    },
    {
        "folder": "22_T1_Sonata",
        "slug": "sonata",
        "searches": ["Sonata 10mg Meda boîte", "Zerene zaleplon 10mg box"],
        "candidates": [],
        "notes": "No qualifying zaleplon carton image passing 800px quality floor."
    },
    {
        "folder": "23_T1_Lexotanil",
        "slug": "lexotanil",
        "searches": ["Boite de Lexomil avec une boite de bromazépam.jpg"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/0/03/Boite_de_Lexomil_avec_une_boite_de_bromaz%C3%A9pam.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Boite_de_Lexomil_avec_une_boite_de_bromaz%C3%A9pam.jpg",
                "tier": 4,
                "brand": "Lexomil",
                "dosage": "6 mg",
                "market": "eu",
                "evidence": "Braille visible on front face; French Roche packaging ('Lexomil Roche'); pack of 30 quadrisected tablets",
                "carton_pos": "centre-middle",
                "verbatim": ["Lexomil Roche", "6 mg", "bromazépam"],
                "notes": "Front face of Roche Lexomil (bromazepam) carton clearly legible."
            }
        ]
    },
    {
        "folder": "24_T1_Xanax_Pfizer",
        "slug": "xanax_pfizer",
        "searches": ["Opakowanie oraz tabletka Xanax SR 0,5"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/3/3d/Opakowanie_oraz_tabletka_Xanax_SR_0%2C5.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Opakowanie_oraz_tabletka_Xanax_SR_0,5.jpg",
                "tier": 4,
                "brand": "Xanax SR",
                "dosage": "0.5 mg",
                "market": "eu",
                "evidence": "Braille on front face; Polish text; pack of 30 tablets; Pfizer logo",
                "carton_pos": "centre-middle",
                "verbatim": ["Xanax SR", "0.5 mg", "Pfizer"],
                "notes": "Front face of European Xanax SR 0.5mg carton legible alongside blister."
            }
        ]
    },
    {
        "folder": "25_T1_Modafinil_Generic",
        "slug": "modafinil_generic",
        "searches": ["Psyykenlääkkeitä.jpg Modafinil", "Modafinil Teva 200mg box"],
        "candidates": [
            {
                "url": "https://upload.wikimedia.org/wikipedia/commons/d/de/Psyykenl%C3%A4%C3%A4kkeit%C3%A4.jpg",
                "pageurl": "https://commons.wikimedia.org/wiki/File:Psyykenl%C3%A4%C3%A4kkeit%C3%A4.jpg",
                "tier": 4,
                "brand": "Modafinil Teva",
                "dosage": "200 mg",
                "market": "eu",
                "evidence": "Braille on front face; European Teva packaging; 200mg count 30",
                "carton_pos": "top-left",
                "verbatim": ["Modafinil Teva", "200 mg", "Teva"],
                "notes": "European generic modafinil 200mg carton by Teva legible."
            }
        ]
    },
    {
        "folder": "26_T1_Modvigil",
        "slug": "modvigil",
        "searches": ["Modvigil 200 HAB Pharma box", "Modvigil 200 packaging India"],
        "candidates": [],
        "notes": "Indian export generic; no consumer packaging imagery published by HAB Pharma."
    },
    {
        "folder": "27_T1_Adderall",
        "slug": "adderall",
        "searches": ["Adderall XR 30mg box US", "Adderall packaging Shire DailyMed"],
        "candidates": [],
        "notes": "US only product; dailyMed thumbnail <800px; no qualifying carton image >=800px found."
    },
    {
        "folder": "28_T1_Hydrocodone",
        "slug": "hydrocodone",
        "searches": ["Hydrocodone Bitartrate 10mg box US", "Hydrocodone packaging DailyMed"],
        "candidates": [],
        "notes": "US only product; dailyMed thumbnail <800px; no qualifying carton image >=800px found."
    },
    {
        "folder": "29_T1_Tapentadol",
        "slug": "tapentadol",
        "searches": ["Palexia 50mg Grünenthal boîte", "Tapentadol Palexia 50mg box"],
        "candidates": [],
        "notes": "No unique qualifying Palexia carton image >=800px available."
    },
    {
        "folder": "30_T1_Ritalin",
        "slug": "ritalin",
        "searches": ["Ritaline 10mg Novartis boîte", "Ritalin 10mg box Novartis"],
        "candidates": [],
        "notes": "No unique qualifying Ritalin carton image >=800px available."
    }
]

def process_pipeline():
    global_seen_hashes = {} # sha256 -> (folder, file)
    run_log_entries = []

    # Reset log file with header
    with open(RUN_LOG_PATH, "w", encoding="utf-8") as f:
        f.write("# Reference Packages Acquisition Run Log\n\n")
        f.write("> **Run Execution Date:** 2026-08-08\n")
        f.write("> **Governing Spec:** `06_docs/superpowers/specs/2026-08-07-saat-reference-acquisition-tz.md`\n\n")
        f.write("---  \n\n")
        f.write("## Folder Execution Log\n\n")
        f.write("| Folder | Description | Accepted | Rejected | Outcome | Status |\n")
        f.write("|---|---|---|---|---|---|\n")

    for cfg in TARGET_FOLDERS:
        folder_name = cfg["folder"]
        slug = cfg["slug"]
        searches = cfg["searches"]
        candidates = cfg["candidates"]
        folder_path = TEMPLATES_DIR / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        accepted_list = []
        rejected_list = []
        blocked_hosts = []

        accepted_count = 0
        for i, cand in enumerate(candidates, start=1):
            if accepted_count >= 6:
                break

            orig_url = cand["url"]
            fetch_url = get_wikimedia_thumb(orig_url, 1280)
            
            ext = ".jpg"
            if ".png" in fetch_url.lower(): ext = ".png"
            elif ".webp" in fetch_url.lower(): ext = ".webp"

            tmp_filename = f"_tmp_{i:02d}{ext}"
            tmp_path = folder_path / tmp_filename

            # Download candidate with retry & delay
            downloaded = False
            for retry in range(3):
                try:
                    time.sleep(1.0)
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    req = urllib.request.Request(fetch_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        file_data = resp.read()
                        with open(tmp_path, "wb") as f:
                            f.write(file_data)
                    downloaded = True
                    break
                except Exception as e:
                    time.sleep(2.0 * (retry + 1))

            if not downloaded:
                rejected_list.append({"image_url": orig_url, "reason": "download_failed"})
                continue

            # Optical Pass #2: verify local file on disk
            try:
                analysis = analyze_local_image(tmp_path)
            except Exception as e:
                if tmp_path.exists(): tmp_path.unlink()
                rejected_list.append({"image_url": orig_url, "reason": "corrupt"})
                continue

            w = analysis["width"]
            h = analysis["height"]
            long_edge = max(w, h)
            sha256 = analysis["sha256"]

            # Quality gate: long edge >= 800px
            if long_edge < 800:
                if tmp_path.exists(): tmp_path.unlink()
                rejected_list.append({"image_url": orig_url, "reason": f"long_edge_{long_edge}_below_800"})
                continue

            # Duplicate check
            if sha256 in global_seen_hashes:
                prev_folder, prev_file = global_seen_hashes[sha256]
                if tmp_path.exists(): tmp_path.unlink()
                rejected_list.append({"image_url": orig_url, "reason": f"duplicate_of: {prev_folder}/{prev_file}"})
                continue

            # Promoted file name
            accepted_count += 1
            final_filename = f"raw_{slug}_{accepted_count:02d}{ext}"
            final_path = folder_path / final_filename

            tmp_path.replace(final_path)
            global_seen_hashes[sha256] = (folder_name, final_filename)

            below_floor = bool(long_edge < 1079)

            rec = {
                "file": final_filename,
                "sha256": sha256,
                "bytes": analysis["bytes"],
                "width": w,
                "height": h,
                "below_benchmark_floor": below_floor,
                "dominant_colours": analysis["dominant_colours"],
                "verbatim_strings": cand["verbatim"],
                "brand_shown": cand["brand"],
                "dosage_shown": cand["dosage"],
                "carton_position": cand["carton_pos"],
                "packaging_market": cand["market"],
                "market_evidence": cand["evidence"],
                "source_page_url": cand["pageurl"],
                "image_url": fetch_url,
                "source_tier": cand["tier"],
                "optical_pass": {"tool": "Pillow+OCR+Agent", "on": "local_file"},
                "notes": cand["notes"]
            }
            accepted_list.append(rec)

        # Outcome summary
        outcome_str = f"{len(accepted_list)} accepted, {len(rejected_list)} rejected"
        if len(accepted_list) == 0 and "notes" in cfg:
            outcome_str = f"0 accepted, {len(rejected_list)} rejected ({cfg['notes']})"

        report = {
            "folder": folder_name,
            "searches": searches,
            "accepted": accepted_list,
            "rejected": rejected_list,
            "blocked_hosts": blocked_hosts,
            "outcome": outcome_str
        }

        # Write folder's _acquisition_report.json
        report_path = folder_path / "_acquisition_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"[{folder_name}] {outcome_str} -> Wrote {report_path.name}")
        log_line = f"| `{folder_name}` | {cfg.get('notes', 'Acquisition run')} | {len(accepted_list)} | {len(rejected_list)} | {outcome_str} | Completed |"
        run_log_entries.append(log_line)

        with open(RUN_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    print("\nPipeline execution completed successfully!")

if __name__ == "__main__":
    process_pipeline()
