# Verification Barrier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository unable to assert something that nothing verifies — by closing three live defects and adding the checks that would have caught each.

**Architecture:** Everything rides in the existing test suite (`python -m unittest discover -s tests`); no new command to remember. Three fast guards (stage smoke, artifact integrity, path reachability) plus a post-render OCR check that first flattens the carton's front face using corners the renderer publishes.

**Tech Stack:** Python 3.10.11, stdlib `unittest` (**not pytest**), Pillow, numpy, jsonschema, pytesseract + Tesseract 5.4.0.20240606, Blender 5.1 as an external executable.

**Design spec:** [`2026-08-03-verification-barrier-design.md`](../specs/2026-08-03-verification-barrier-design.md)

## Global Constraints

- **Tests are stdlib `unittest`, never pytest.** pytest is not a dependency. Run with `python -m unittest discover -s tests`.
- **Never `import bpy` outside `05_assets/blender/render_driver.py`.** Blender is an external executable; the driver runs inside Blender's own bundled interpreter, where project modules and pip packages are unavailable.
- **A hard failure inside `render_driver.py` must raise `SystemExit`.** Blender exits 0 after printing an ordinary uncaught exception, and `blender_renderer.py` would read that as success.
- **All paths resolve through `src.utils.get_path` / `resolve_path`, anchored to `PROJECT_ROOT`.** `config.yaml` is required in this fork; the built-in defaults in `src/utils.py` still point at the source project's layout.
- **Blender-dependent tests skip via `@unittest.skipUnless(Path(BLENDER_EXE).exists(), ...)`**, matching `tests/test_render_driver.py` and `tests/test_blender_carton.py`.
- **Tesseract lives at `C:\Program Files\Tesseract-OCR\tesseract.exe` and is NOT on PATH.** `shutil.which("tesseract")` returns `None`; `scripts/render_qa.py` already probes the absolute path in its import block.
- **Never derive carton face geometry from `(w, h, d)`.** Read it off the built mesh's `bound_box`. `render_driver.py:733-741` records why: the nominal dimensions and the mesh extents are not the same thing, and camera framing is calibrated against the mesh.
- **Commit messages end with:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- Work on branch `dev`.

## File Structure

| File | Responsibility |
|---|---|
| `scripts/catalogue_sweep.py` *(modify)* | Use the `md_path` it already computes (line ~504). |
| `tests/test_sweep_reporting.py` *(create)* | A partial run must not touch the canonical report. |
| `tests/test_state_artifacts.py` *(create)* | Every `*.json`/`*.md` pair in `00_PROJECT_STATE` agrees. |
| `tests/test_script_paths.py` *(create)* | Every `scripts/*.py` argparse path default resolves. |
| `scripts/render_qa.py` *(modify)* | Config-driven paths; read the manifest; deskew; confidence not HARD_FAIL. |
| `tests/test_pipeline_smoke.py` *(create)* | Stages run end to end from a foreign working directory. |
| `05_assets/blender/render_driver.py` *(modify)* | Publish printed-face corners in image pixels. |
| `src/deskew.py` *(create)* | Pure perspective flattening. No Blender, no config. |
| `tests/test_deskew.py` *(create)* | Round-trip a known warp without involving OCR. |
| `tests/fixtures/ocr/` *(create)* | One committed render + manifest + view sidecar. |
| `tests/test_render_qa.py` *(modify)* | Add the OCR barrier assertions to the existing file. |

---

### Task 1: The sweep report cannot lie about its scope

**Files:**
- Modify: `scripts/catalogue_sweep.py:504`
- Create: `tests/test_sweep_reporting.py`
- Regenerate: `00_PROJECT_STATE/sweep_report.md`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing later tasks depend on. `write_reports(records, group_name, started_at, interrupted=False, limit=None)` and `report_paths(limit) -> (json_path, md_path)` keep their current signatures.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sweep_reporting.py`:

```python
"""The sweep's own reporting, which has told the repository something false twice.

A code review caught it once (bc44665): a --limit smoke run overwrote a full
group's report. The fix routed partial runs to sweep_report.partial.*, and it
worked for the JSON only -- write_reports computed md_path and then hardcoded
the Markdown path anyway, so a 2-SKU run overwrote the 30-SKU record again and
rode into dc7d8e1 inside a 434-file rename commit.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import catalogue_sweep


def _record(stem="1-min"):
    """The smallest record write_reports will render without complaining."""
    return {
        "stem": stem,
        "product_name": "Test Product",
        "template_id": "T1",
        "carton_mm": [115.0, 55.0, 48.0],
        "rendered": True,
        "render_seconds": 1.0,
        "measurement": {"measured": False, "reason": "stub"},
    }


class TestPartialRunIsolation(unittest.TestCase):
    def test_partial_run_leaves_the_canonical_report_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            canonical_md = state / "sweep_report.md"
            canonical_json = state / "sweep_report.json"
            canonical_md.write_text("REAL 30-SKU REPORT", encoding="utf-8")
            canonical_json.write_text('{"counts": {"total": 30}}', encoding="utf-8")

            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "top30", "2026-01-01 00:00:00", limit=2)

            self.assertEqual(canonical_md.read_text(encoding="utf-8"),
                             "REAL 30-SKU REPORT",
                             "a --limit run overwrote the whole-group Markdown")
            self.assertEqual(canonical_json.read_text(encoding="utf-8"),
                             '{"counts": {"total": 30}}',
                             "a --limit run overwrote the whole-group JSON")
            self.assertTrue((state / "sweep_report.partial.md").exists())
            self.assertTrue((state / "sweep_report.partial.json").exists())

    def test_whole_group_run_writes_the_canonical_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "top30", "2026-01-01 00:00:00", limit=None)
            self.assertTrue((state / "sweep_report.md").exists())
            self.assertIn("the whole group",
                          (state / "sweep_report.md").read_text(encoding="utf-8"))
            self.assertFalse((state / "sweep_report.partial.md").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch the first test fail**

```bash
python -m unittest tests.test_sweep_reporting -v
```

Expected: `test_partial_run_leaves_the_canonical_report_untouched` FAILS with
`'# Catalogue sweep report...' != 'REAL 30-SKU REPORT'`. The second test passes
already. If the first test passes, the fix has been applied out of order — stop
and check `git diff`.

- [ ] **Step 3: Fix the one line**

In `scripts/catalogue_sweep.py`, at the end of `write_reports` (~line 504):

```python
    (STATE_DIR / "sweep_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
```

becomes:

```python
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
```

`md_path` is already bound at line 386 from `report_paths(limit)` and was
never read — that dead assignment is the whole bug.

- [ ] **Step 4: Run the tests**

```bash
python -m unittest tests.test_sweep_reporting -v
```

Expected: both PASS.

- [ ] **Step 5: Regenerate the canonical Markdown from the surviving JSON**

The 30-SKU data is intact in `00_PROJECT_STATE/sweep_report.json`
(`covers_whole_group: true`, `counts.total: 30`, `total_render_seconds: 1205.4`);
only its rendering was lost. Re-render it without re-running the sweep:

```bash
python -c "
import json
from scripts.catalogue_sweep import write_reports
d = json.load(open('00_PROJECT_STATE/sweep_report.json', encoding='utf-8'))
write_reports(d['records'], d['group'], d['started_at'],
              interrupted=d['interrupted'], limit=d['limit'])
print('rows:', len(d['records']))
"
```

Expected: `rows: 30`, and `00_PROJECT_STATE/sweep_report.md` now opens with
``> Group `top30`, the whole group · started 2026-08-02 19:51:24`` and reports
30 SKU / 20.1 min.

- [ ] **Step 6: Commit**

```bash
git add scripts/catalogue_sweep.py tests/test_sweep_reporting.py 00_PROJECT_STATE/sweep_report.md
git commit -m "Make the sweep's Markdown obey the same guard as its JSON

write_reports computed md_path from report_paths(limit) and then wrote to a
hardcoded sweep_report.md, so the guard added after the last code review
protected the JSON alone. A 2-SKU verification run therefore overwrote the real
30-SKU record a second time, and the change rode into dc7d8e1 as 46 lines inside
a 434-file rename commit.

The Markdown is regenerated from the surviving JSON rather than re-swept: the
records were never lost, only their rendering.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: No state artifact contradicts its sibling

**Files:**
- Create: `tests/test_state_artifacts.py`

**Interfaces:**
- Consumes: the report format from Task 1.
- Produces: nothing.

- [ ] **Step 1: Write the test**

Create `tests/test_state_artifacts.py`:

```python
"""Guards the permanent record in 00_PROJECT_STATE against self-contradiction.

Task 1 fixed one report's writer. This is the general form: any generated
Markdown that has a JSON sibling must agree with it, whatever produced them.
The failure this exists to prevent is a reader trusting a summary that its own
data disproves.
"""
import json
import re
import unittest
from pathlib import Path

from src.utils import PROJECT_ROOT

STATE_DIR = PROJECT_ROOT / "00_PROJECT_STATE"


class TestStateArtifactsAgree(unittest.TestCase):
    def _pairs(self):
        for json_path in sorted(STATE_DIR.glob("*.json")):
            md_path = json_path.with_suffix(".md")
            if md_path.exists():
                yield json_path, md_path

    def test_at_least_one_pair_exists(self):
        # Without this, deleting every report would make the suite below vacuous
        # and the guard would report success having checked nothing.
        self.assertTrue(list(self._pairs()),
                        f"no *.json/*.md report pairs found in {STATE_DIR}")

    def test_scope_claim_matches_the_data(self):
        for json_path, md_path in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if "covers_whole_group" not in data:
                    continue
                text = md_path.read_text(encoding="utf-8")
                says_partial = "a partial run" in text
                self.assertEqual(
                    says_partial, not data["covers_whole_group"],
                    f"{md_path.name} says partial={says_partial} but "
                    f"{json_path.name} says covers_whole_group="
                    f"{data['covers_whole_group']}")

    def test_headline_count_matches_the_data(self):
        for json_path, md_path in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                total = (data.get("counts") or {}).get("total")
                if total is None:
                    continue
                text = md_path.read_text(encoding="utf-8")
                m = re.search(r"SKU in group: \*\*(\d+)\*\*", text)
                self.assertIsNotNone(
                    m, f"{md_path.name} has no 'SKU in group' line to check")
                self.assertEqual(
                    int(m.group(1)), total,
                    f"{md_path.name} claims {m.group(1)} SKU, "
                    f"{json_path.name} holds {total}")

    def test_record_count_matches_the_headline(self):
        for json_path, _ in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                records, counts = data.get("records"), data.get("counts")
                if records is None or counts is None:
                    continue
                self.assertEqual(
                    len(records), counts["total"],
                    f"{json_path.name} summarises {counts['total']} SKU but "
                    f"carries {len(records)} records")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

```bash
python -m unittest tests.test_state_artifacts -v
```

Expected: all PASS, because Task 1 regenerated the Markdown. If
`test_scope_claim_matches_the_data` fails, Task 1's step 5 was skipped.

- [ ] **Step 3: Prove the test has teeth**

Temporarily corrupt the report and confirm the guard notices:

```bash
python -c "
from pathlib import Path
p = Path('00_PROJECT_STATE/sweep_report.md')
t = p.read_text(encoding='utf-8')
p.write_text(t.replace('SKU in group: **30**', 'SKU in group: **2**'), encoding='utf-8')
"
python -m unittest tests.test_state_artifacts -v
git checkout 00_PROJECT_STATE/sweep_report.md
```

Expected: `test_headline_count_matches_the_data` FAILS, then `git checkout`
restores the file. Re-run the test to confirm it passes again before committing.

- [ ] **Step 4: Commit**

```bash
git add tests/test_state_artifacts.py
git commit -m "Assert that generated state reports agree with their own data

The sweep report is not a special case; any generated Markdown with a JSON
sibling can drift from it. This checks the scope claim, the headline SKU count
and the record count, and refuses to pass vacuously when no report pairs exist.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Every script's default paths resolve in this fork

**Files:**
- Create: `tests/test_script_paths.py`
- Modify: `scripts/render_qa.py:42-44`

**Interfaces:**
- Consumes: `src.utils.load_config`, `get_path`, `resolve_path`.
- Produces: `scripts/render_qa.py` exposes module-level `DEFAULT_PROCESSED_DIR`, `DEFAULT_PASSPORTS_DIR`, `DEFAULT_MANIFESTS_DIR`, `DEFAULT_REPORT_PATH` as absolute `Path`s. Task 7 builds on these.

- [ ] **Step 1: Write the failing test**

Create `tests/test_script_paths.py`:

```python
"""Every operator script must point at directories this fork actually has.

The fork remapped every path onto numbered folders. A script that kept the
source project's layout does not crash on import -- it runs, finds nothing, and
reports an empty result, which reads exactly like a clean pass. scripts/
render_qa.py defaulted to render_output/processed, a directory this repository
has never contained.
"""
import unittest
from pathlib import Path

from src.utils import PROJECT_ROOT

SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Directories a script may legitimately create on first use. Their PARENT must
# exist -- that is what distinguishes "not written yet" from "wrong layout".
CREATABLE = {"blender_test_renders", "processed", "superpowers"}


class TestScriptDefaultPaths(unittest.TestCase):
    def _modules(self):
        import importlib
        for path in sorted(SCRIPTS_DIR.glob("*.py")):
            if path.stem in ("__init__",):
                continue
            with self.subTest(script=path.name):
                yield path, importlib.import_module(f"scripts.{path.stem}")

    def test_module_level_path_defaults_are_inside_the_project(self):
        for path, mod in self._modules():
            for name in dir(mod):
                if not name.startswith("DEFAULT_"):
                    continue
                value = getattr(mod, name)
                if not isinstance(value, Path):
                    continue
                with self.subTest(script=path.name, constant=name):
                    self.assertTrue(
                        value.is_absolute(),
                        f"{path.name}.{name} is relative ({value}); it will "
                        f"resolve against the caller's working directory")
                    self.assertTrue(
                        str(value).startswith(str(PROJECT_ROOT)),
                        f"{path.name}.{name} points outside the project: {value}")

    def test_module_level_path_defaults_exist_or_have_an_existing_parent(self):
        for path, mod in self._modules():
            for name in dir(mod):
                if not name.startswith("DEFAULT_"):
                    continue
                value = getattr(mod, name)
                if not isinstance(value, Path):
                    continue
                with self.subTest(script=path.name, constant=name):
                    if value.exists():
                        continue
                    self.assertIn(
                        value.name, CREATABLE,
                        f"{path.name}.{name} -> {value} does not exist and is "
                        f"not a directory a script is allowed to create")
                    self.assertTrue(
                        value.parent.exists(),
                        f"{path.name}.{name} -> {value}: even its parent "
                        f"{value.parent} is missing, so this is a stale path "
                        f"from the source project's layout")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m unittest tests.test_script_paths -v
```

Expected: FAILS on `render_qa.DEFAULT_PROCESSED_DIR` — it is relative
(`render_output/processed`) and its parent `render_output/` does not exist.

- [ ] **Step 3: Route render_qa's paths through the config**

In `scripts/render_qa.py`, replace the constants at lines 42-44:

```python
DEFAULT_PROCESSED_DIR = Path("render_output/processed")
DEFAULT_PASSPORTS_DIR = Path("04_passports/passports_json")
DEFAULT_REPORT_PATH   = Path("06_docs/RENDER_QA_REPORT.md")
```

with:

```python
# Resolved through the config, not hardcoded: this fork remapped every path onto
# numbered folders, and a stale default does not fail loudly -- it finds no
# images and reports a clean run over nothing.
from src.utils import load_config, get_path, resolve_path, PROJECT_ROOT  # noqa: E402

_CFG = load_config()
# Source follows the selected engine. Blender writes to its own directory
# precisely so resume and Stage 3 cannot confuse the two engines' output.
_ENGINE = (_CFG.get("render") or {}).get("engine", "gemini")
DEFAULT_PROCESSED_DIR = (resolve_path(_CFG["blender"]["output_dir"])
                         if _ENGINE == "blender"
                         else get_path(_CFG, "renders_raw"))
DEFAULT_PASSPORTS_DIR  = get_path(_CFG, "passports_json")
DEFAULT_MANIFESTS_DIR  = get_path(_CFG, "passports_manifests")
DEFAULT_REPORT_PATH    = PROJECT_ROOT / "06_docs" / "RENDER_QA_REPORT.md"
```

Add `--manifests` to the argument parser in `main()`, beside `--passports`:

```python
    parser.add_argument(
        "--manifests",
        type=Path,
        default=DEFAULT_MANIFESTS_DIR,
        help=f"Directory of render manifests (default: {DEFAULT_MANIFESTS_DIR})",
    )
```

- [ ] **Step 4: Run the tests**

```bash
python -m unittest tests.test_script_paths tests.test_render_qa -v
```

Expected: both modules PASS. `test_render_qa` must still pass — Task 3 changes
paths only, not `check_image`.

- [ ] **Step 5: Confirm the script now finds real images**

```bash
python scripts/render_qa.py --limit 3
```

Expected: it reports 3 images checked from `02_processing/blender_test_renders`,
not "Processed images directory not found". The results will be poor
(`HARD_FAIL`) — that is the known OCR problem, fixed in Task 7, not a path bug.

- [ ] **Step 6: Commit**

```bash
git add tests/test_script_paths.py scripts/render_qa.py
git commit -m "Point render_qa at directories this fork has, and test the class

render_qa.py defaulted to render_output/processed, a path from the source
project. It did not crash -- it found no images and wrote a clean report over
nothing, which is the failure mode worth guarding: a stale path reads as a pass.

The test walks every scripts/*.py module-level DEFAULT_ path and requires it to
be absolute, inside the project, and either present or creatable with an
existing parent.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Stages run end to end, from a foreign working directory

**Files:**
- Create: `tests/test_pipeline_smoke.py`

**Interfaces:**
- Consumes: `src.utils.PROJECT_ROOT`, `get_path`.
- Produces: nothing.

- [ ] **Step 1: Write the test**

Create `tests/test_pipeline_smoke.py`:

```python
"""Runs the stages the way the pipeline runs them, which the unit suite does not.

src/passport_generator.py wrote its override audit to Path("docs"), relative to
the working directory. All 149 tests passed while Stage 1 was broken: nothing
exercised its main() to the end. It crashed after writing all 391 passports, and
only a live pipeline run found it.

The working directory is the point. Running from the repository root would not
have caught it -- Path("docs") resolves there. Every subprocess below therefore
runs from a temporary directory.
"""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.utils import load_config, get_path, PROJECT_ROOT

CFG = load_config()
MD_DIR = get_path(CFG, "passports_md")
MANIFEST_DIR = get_path(CFG, "passports_manifests")
JSON_DIR = get_path(CFG, "passports_json")

# Stage 1 takes ~3 s for all 391 passports (measured 2026-08-02, log
# pharmagen_20260802_205425). 300 s is generous headroom for a cold filesystem.
STAGE_TIMEOUT_S = 300


def _digest(directory: Path, pattern: str) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.glob(pattern))}


def _run_from_elsewhere(module: str, *args) -> subprocess.CompletedProcess:
    """Run a stage module as its own process, from a directory that is NOT the
    repository root, with PROJECT_ROOT on sys.path so imports still resolve."""
    with tempfile.TemporaryDirectory() as alien_cwd:
        env = {**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT),
               "PYTHONIOENCODING": "utf-8"}
        return subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=alien_cwd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=STAGE_TIMEOUT_S)


class TestStageOneRunsEndToEnd(unittest.TestCase):
    def test_stage_one_completes_and_is_idempotent(self):
        expected = len(list(JSON_DIR.glob("*.json")))
        self.assertGreater(expected, 0, f"no input passports in {JSON_DIR}")

        before_md = _digest(MD_DIR, "*.md")
        before_manifests = _digest(MANIFEST_DIR, "*.json")

        proc = _run_from_elsewhere("src.passport_generator")
        self.assertEqual(
            proc.returncode, 0,
            f"Stage 1 exited {proc.returncode}\nSTDERR:\n{proc.stderr[-3000:]}")

        after_md = _digest(MD_DIR, "*.md")
        after_manifests = _digest(MANIFEST_DIR, "*.json")

        self.assertEqual(len(after_md), expected,
                         "Stage 1 did not write one Markdown prompt per passport")
        self.assertEqual(len(after_manifests), expected,
                         "Stage 1 did not write one render manifest per passport")
        # Idempotence is a documented invariant of this fork; assert it rather
        # than trusting it. A diff here means Stage 1 has become non-deterministic.
        self.assertEqual(before_md, after_md,
                         "Stage 1 changed its Markdown output on a re-run")
        self.assertEqual(before_manifests, after_manifests,
                         "Stage 1 changed its manifests on a re-run")


class TestStageTwoFacadeDispatches(unittest.TestCase):
    def test_blender_estimate_is_a_clean_dry_run(self):
        proc = _run_from_elsewhere(
            "src.render_stage", "--engine", "blender", "--estimate")
        self.assertEqual(
            proc.returncode, 0,
            f"Stage 2 --estimate exited {proc.returncode}\n"
            f"STDERR:\n{proc.stderr[-3000:]}")
        self.assertIn("[blender]", proc.stdout + proc.stderr,
                      "the blender engine did not report an estimate")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it**

```bash
python -m unittest tests.test_pipeline_smoke -v
```

Expected: both PASS in roughly 5 seconds. If `test_stage_one_completes_and_is_idempotent`
reports a digest difference, Stage 1 is genuinely non-deterministic — that is a
real finding; stop and investigate rather than relaxing the assertion.

- [ ] **Step 3: Prove the test has teeth**

Reintroduce the exact bug that shipped:

```bash
python - <<'PY'
from pathlib import Path
p = Path("src/passport_generator.py")
t = p.read_text(encoding="utf-8")
assert 'docs_dir = PROJECT_ROOT / "06_docs"' in t, "anchor line not found"
p.write_text(t.replace('docs_dir = PROJECT_ROOT / "06_docs"',
                       'docs_dir = Path("docs")'), encoding="utf-8")
PY
python -m unittest tests.test_pipeline_smoke -v
git checkout src/passport_generator.py
```

Expected: `test_stage_one_completes_and_is_idempotent` FAILS with a non-zero exit
code from Stage 1. Then `git checkout` restores it; re-run to confirm green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline_smoke.py
git commit -m "Run the stages the way the pipeline runs them

Stage 1 wrote its override audit to Path(\"docs\"), relative to the working
directory, and crashed at the end of main() after writing all 391 passports.
Every one of the 149 tests passed while it was broken, because none invoked a
stage's main().

The subprocesses run from a temporary directory on purpose: from the repository
root, Path(\"docs\") resolves and the bug stays invisible. Idempotence is checked
by hashing the outputs either side of the run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: The renderer publishes where the printed faces landed

**Files:**
- Modify: `05_assets/blender/render_driver.py` (imports, new helpers, `dump_scene`, `main`)
- Modify: `tests/test_render_driver.py` (append a test class)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `{out_stem}.view.json` beside every rendered PNG:
    `{"resolution": [int, int], "front_face_px": [[x,y],[x,y],[x,y],[x,y]] | null, "side_panel_px": [...] | null}`
  - The same two keys inside `--dump-scene` output.
  - Corner order is **[top-left, top-right, bottom-right, bottom-left]**, in image pixels, origin top-left, y increasing downward. Tasks 6, 7 and 8 depend on this order.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render_driver.py` (it already defines `_HAVE_BLENDER`,
`_SKIP_REASON` and a helper that runs the driver with a job):

```python
@unittest.skipUnless(_HAVE_BLENDER, _SKIP_REASON)
class TestPrintedFaceCorners(unittest.TestCase):
    """The renderer owns the camera, so it -- not a downstream consumer --
    reports where each printed face landed in the frame.

    Recovering these corners from the image was tried and failed: a colour mask
    keyed on palette.accent cannot separate the accent stripe from the brand
    badge when primary and accent are close, and an SVD principal axis is
    sign-ambiguous (measured tilts came out at 138-178 degrees).
    """

    def test_front_face_corners_are_a_sane_quad_inside_the_frame(self):
        scene = _dump_scene()          # existing helper: runs --dump-scene
        corners = scene.get("front_face_px")
        self.assertIsNotNone(corners, "driver did not report front_face_px")
        self.assertEqual(len(corners), 4)
        res_x, res_y = scene["resolution"]
        for x, y in corners:
            self.assertTrue(0 <= x <= res_x, f"corner x={x} outside 0..{res_x}")
            self.assertTrue(0 <= y <= res_y, f"corner y={y} outside 0..{res_y}")

    def test_corners_are_ordered_tl_tr_br_bl(self):
        tl, tr, br, bl = _dump_scene()["front_face_px"]
        self.assertLess(tl[0], tr[0], "top-left is not left of top-right")
        self.assertLess(bl[0], br[0], "bottom-left is not left of bottom-right")
        self.assertLess(tl[1], bl[1], "top-left is not above bottom-left")
        self.assertLess(tr[1], br[1], "top-right is not above bottom-right")

    def test_the_quad_is_skewed_because_the_carton_is_rotated(self):
        # If this ever reads as a rectangle, either the rotation was removed or
        # the corners are being faked from nominal dimensions.
        tl, tr, br, bl = _dump_scene()["front_face_px"]
        left_height = bl[1] - tl[1]
        right_height = br[1] - tr[1]
        self.assertGreater(
            abs(left_height - right_height), 1.0,
            "the front face projects as a rectangle; the carton should be "
            "rotated 27.5-35 degrees about Z")

    def test_side_panel_corners_are_reported_too(self):
        self.assertIsNotNone(_dump_scene().get("side_panel_px"))
```

If `tests/test_render_driver.py` has no `_dump_scene()` helper returning parsed
JSON, add one modelled on the `subprocess.run` block in
`tests/test_blender_carton.py:115-130`.

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m unittest tests.test_render_driver.TestPrintedFaceCorners -v
```

Expected: all four FAIL with `driver did not report front_face_px` (or `KeyError:
'resolution'`).

- [ ] **Step 3: Add the projection helpers to the driver**

In `05_assets/blender/render_driver.py`, ensure `mathutils` is imported beside
`bpy` at the top, then add these two functions immediately above `def dump_scene`
(around line 1165):

```python
# ── Where the printed faces landed in the rendered frame ─────────────────────
# OCR of a packshot needs the front face flattened first, and flattening needs
# its four corners in pixels. The renderer holds the camera and the built mesh,
# so it publishes the answer; a consumer that reconstructs it from the image is
# guessing, and two attempts to do that failed.
#
# Corners come off the built mesh's bound_box, never off (w, h, d) -- see the
# note in build_box about the nominal dimensions and the mesh extents not being
# the same thing.
def _order_quad(pts):
    """[top-left, top-right, bottom-right, bottom-left], in image pixels."""
    by_y = sorted(pts, key=lambda p: p[1])
    top = sorted(by_y[:2], key=lambda p: p[0])
    bottom = sorted(by_y[2:], key=lambda p: p[0])
    return [top[0], top[1], bottom[1], bottom[0]]


def _face_corners_px(box, axis: int, take_min: bool):
    """One axis-aligned local face of *box*, projected to image pixels.

    axis 0/1/2 = local X/Y/Z. The front face is local -Y and the visible side
    panel is local -X; +ROTATION_DEG about Z turns both toward the camera.
    """
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    cam = scene.camera
    if box is None or cam is None:
        return None
    local = [mathutils.Vector(c) for c in box.bound_box]
    values = [v[axis] for v in local]
    target = min(values) if take_min else max(values)
    face = [v for v in local if abs(v[axis] - target) < 1e-6]
    if len(face) != 4:
        return None
    out = []
    for v in face:
        ndc = world_to_camera_view(scene, cam, box.matrix_world @ v)
        # world_to_camera_view puts (0, 0) at the frame's BOTTOM-left with y up;
        # image pixels count from the TOP-left with y down.
        out.append([ndc.x * RES_X, (1.0 - ndc.y) * RES_Y])
    return _order_quad(out)


def printed_faces_px():
    """Both printed faces in image pixels, plus the resolution they refer to."""
    box = bpy.data.objects.get("carton")
    bpy.context.view_layer.update()
    return {
        "resolution": [RES_X, RES_Y],
        "front_face_px": _face_corners_px(box, axis=1, take_min=True),
        # Nothing consumes the side panel yet. It comes from the same call, and
        # emitting it now avoids touching the driver twice.
        "side_panel_px": _face_corners_px(box, axis=0, take_min=True),
    }
```

- [ ] **Step 4: Emit the corners from both output paths**

In `dump_scene`, extend the `out` dict — add these entries beside `"film"`:

```python
        **printed_faces_px(),
```

In `main()`, after `setup_render(OUT_PATH, ENGINE, SAMPLES, RES_X, RES_Y)` and
before `bpy.ops.render.render(write_still=True)`:

```python
    # Sidecar for post-render QA. Written before the render so it exists even if
    # rendering later fails, and the pixels are unaffected either way.
    view_path = Path(OUT_PATH).with_suffix(".view.json")
    view_path.write_text(json.dumps(printed_faces_px(), indent=2), encoding="utf-8")
    print(f"[render_driver] wrote {view_path}")
```

- [ ] **Step 5: Run the tests**

```bash
python -m unittest tests.test_render_driver -v
```

Expected: the four new tests PASS, and every pre-existing test in the module
still passes.

- [ ] **Step 6: Prove the render pixels did not move**

This task must be a pure measurement addition. Render one SKU and compare
against the same SKU rendered before the change:

```bash
git stash
python -m src.blender_renderer --limit 1 --from 1-min
python -c "import hashlib,pathlib;print('BEFORE', hashlib.sha256(pathlib.Path('02_processing/blender_test_renders/1-min.png').read_bytes()).hexdigest())"
git stash pop
rm 02_processing/blender_test_renders/1-min.png
python -m src.blender_renderer --limit 1 --from 1-min
python -c "import hashlib,pathlib;print('AFTER ', hashlib.sha256(pathlib.Path('02_processing/blender_test_renders/1-min.png').read_bytes()).hexdigest())"
```

Expected: the two digests are identical. If they differ, the change is touching
the render path and must be reworked — the corners are read off an already-built
scene and must not alter it.

- [ ] **Step 7: Commit**

```bash
git add 05_assets/blender/render_driver.py tests/test_render_driver.py
git commit -m "Publish where each printed face landed in the frame

Reading a packshot needs the front face flattened, and flattening needs its four
corners in pixels. The renderer holds the camera and the built mesh, so it says
where they are; a downstream consumer would have to guess. Two probes tried
guessing from the image and failed -- a colour mask keyed on palette.accent
cannot separate the accent stripe from the brand badge, and the SVD principal
axis is sign-ambiguous, giving tilts of 138-178 degrees where the truth is a few
degrees to -41.

Corners come off the built mesh's bound_box rather than the nominal dimensions,
for the reason build_box already documents. Pure measurement: verified that
1-min renders to a byte-identical PNG either side of the change.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: A pure module that flattens a quadrilateral

**Files:**
- Create: `src/deskew.py`
- Create: `tests/test_deskew.py`

**Interfaces:**
- Consumes: the corner order from Task 5.
- Produces:
  - `perspective_coefficients(src_quad, dst_quad) -> numpy.ndarray` (8 floats)
  - `flatten_face(image, corners, out_width=1500, aspect=None) -> PIL.Image.Image`
  - `image` accepts a `Path`, a `str` or a `PIL.Image.Image`.
  - `corners` is `[[x,y] × 4]` ordered TL, TR, BR, BL.
  - Task 7 calls `flatten_face`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_deskew.py`. It deliberately avoids OCR: this module's job is
geometry, and a test that needed Tesseract would fail for reasons that are not
this module's fault.

```python
"""Geometry only. OCR is Task 8's business; if this test needed Tesseract it
would report recogniser problems as deskew bugs."""
import unittest

import numpy as np
from PIL import Image, ImageDraw

from src.deskew import flatten_face, perspective_coefficients


def _forward_warp(img, dst_quad):
    """Project a rectangular image onto `dst_quad` inside a white canvas."""
    w, h = img.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    canvas = Image.new("RGB", (w, h), "white")
    coeffs = perspective_coefficients(src, dst_quad)
    warped = img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC,
                           fillcolor=(255, 255, 255))
    canvas.paste(warped)
    return canvas


class TestFlattenFace(unittest.TestCase):
    def setUp(self):
        # A white card with one black square at a known place: 20%-40% across,
        # 10%-30% down.
        self.card = Image.new("RGB", (600, 400), "white")
        ImageDraw.Draw(self.card).rectangle([120, 40, 240, 120], fill="black")
        self.quad = [(90.0, 70.0), (540.0, 20.0), (560.0, 350.0), (60.0, 300.0)]

    def test_flattening_undoes_a_known_warp(self):
        warped = _forward_warp(self.card, self.quad)
        flat = flatten_face(warped, self.quad, out_width=600, aspect=400 / 600)
        self.assertEqual(flat.size, (600, 400))

        a = np.asarray(flat.convert("L")).astype(float)
        ys, xs = np.nonzero(a < 128)
        self.assertGreater(len(xs), 500, "the black square did not survive")
        # Tolerance is 12 px on a 600 px width: resampling twice softens edges,
        # but a misordered corner would move these by hundreds of pixels.
        self.assertAlmostEqual(xs.min(), 120, delta=12)
        self.assertAlmostEqual(xs.max(), 240, delta=12)
        self.assertAlmostEqual(ys.min(), 40, delta=12)
        self.assertAlmostEqual(ys.max(), 120, delta=12)

    def test_aspect_defaults_to_the_quads_own_proportions(self):
        flat = flatten_face(self.card, self.quad, out_width=600)
        self.assertEqual(flat.width, 600)
        self.assertGreater(flat.height, 200)
        self.assertLess(flat.height, 600)

    def test_accepts_a_path(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "card.png"
            self.card.save(p)
            flat = flatten_face(p, self.quad, out_width=300)
            self.assertEqual(flat.width, 300)

    def test_rejects_a_quad_that_is_not_four_corners(self):
        with self.assertRaises(ValueError):
            flatten_face(self.card, self.quad[:3])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m unittest tests.test_deskew -v
```

Expected: `ModuleNotFoundError: No module named 'src.deskew'`.

- [ ] **Step 3: Write the module**

Create `src/deskew.py`:

```python
"""Flatten the carton's front face so its printed text can be read.

A packshot is shot with the carton rotated 27.5-35 degrees about Z, which puts
every label row on a perspective-skewed plane. Tesseract reads that badly.
Measured on 2026-08-03 against six real renders: "Atomoxetine Generic" came back
as "Germetine", "Tramadol" as "{ra m a d O", and 11-min returned an empty string
-- in page-segmentation modes 3, 6, 11 and 12 alike. The same four strings drawn
flat in the same vendored DejaVu at the same cap heights read 4 of 4 cleanly.
The rotation is the whole problem, so undoing it is the whole fix.

Corners come from the renderer's {stem}.view.json, never from the image. Two
probes tried to recover them by colour-matching the accent stripe: the mask
cannot separate the stripe from the brand badge when palette.primary and
palette.accent are close, and the SVD principal axis is sign-ambiguous.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def perspective_coefficients(src_quad, dst_quad) -> np.ndarray:
    """The eight coefficients PIL's PERSPECTIVE transform wants.

    PIL samples backwards -- for each output pixel it asks where in the source
    to read -- so the map it needs runs destination to source, which is why
    dst_quad supplies the left-hand side below.
    """
    a, b = [], []
    for (sx, sy), (dx, dy) in zip(src_quad, dst_quad):
        a.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        a.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
        b += [sx, sy]
    return np.linalg.solve(np.asarray(a, dtype=float), np.asarray(b, dtype=float))


def flatten_face(image, corners, out_width: int = 1500, aspect: float | None = None):
    """Return quadrilateral *corners* of *image* as an axis-aligned image.

    corners:   [top-left, top-right, bottom-right, bottom-left] in pixels, the
               order 05_assets/blender/render_driver.py emits.
    out_width: width of the returned image in pixels.
    aspect:    height / width of the real face. Defaults to the quad's own
               averaged edge ratio, which is close enough for OCR and needs no
               knowledge of the carton.
    """
    if corners is None or len(corners) != 4:
        raise ValueError(
            f"need exactly four corners in TL, TR, BR, BL order; got "
            f"{0 if corners is None else len(corners)}")

    img = image if isinstance(image, Image.Image) else Image.open(Path(image))
    img = img.convert("RGB")

    tl, tr, br, bl = [(float(c[0]), float(c[1])) for c in corners]
    if aspect is None:
        top = float(np.hypot(tr[0] - tl[0], tr[1] - tl[1]))
        bottom = float(np.hypot(br[0] - bl[0], br[1] - bl[1]))
        left = float(np.hypot(bl[0] - tl[0], bl[1] - tl[1]))
        right = float(np.hypot(br[0] - tr[0], br[1] - tr[1]))
        width = (top + bottom) / 2.0
        aspect = ((left + right) / 2.0 / width) if width else 1.0

    out_h = max(1, int(round(out_width * aspect)))
    dst = [(0, 0), (out_width, 0), (out_width, out_h), (0, out_h)]
    coeffs = perspective_coefficients([tl, tr, br, bl], dst)
    return img.transform((out_width, out_h), Image.PERSPECTIVE, coeffs,
                         Image.BICUBIC, fillcolor=(255, 255, 255))
```

- [ ] **Step 4: Run the tests**

```bash
python -m unittest tests.test_deskew -v
```

Expected: all four PASS.

- [ ] **Step 5: Commit**

```bash
git add src/deskew.py tests/test_deskew.py
git commit -m "Add perspective flattening for the carton's front face

Measured against six real renders: raw OCR reads \"Atomoxetine Generic\" as
\"Germetine\" and returns an empty string for 11-min, in every page-segmentation
mode. The same strings drawn flat in the same vendored font read 4 of 4. The
35-degree rotation is the whole problem.

Geometry only, no OCR in the tests -- a Tesseract dependency here would report
recogniser problems as deskew bugs. The round-trip test warps a card with a
black square at a known position and checks it lands back where it started.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: render_qa checks the manifest, on a flattened face, without hard failures

**Files:**
- Modify: `scripts/render_qa.py` (`check_image`, `load_passport` → `load_manifest`, `main`, `write_report`)

**Interfaces:**
- Consumes: `src.deskew.flatten_face` (Task 6); `{stem}.view.json` (Task 5); `DEFAULT_MANIFESTS_DIR` (Task 3).
- Produces: `check_image(image_path, manifest, view=None) -> dict` with keys
  `sku, ocr_ok, ocr_error, deskewed, fields, found, expected, confidence, status, flags`.
  `fields` maps each of `brand_name_display`, `active_ingredient_display`,
  `dosage_display`, `unit_count_display` to `True` / `False`.
  `status` is one of `OK`, `WARN`, `UNAVAILABLE`, `NO_MANIFEST`. Task 8 asserts on these.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_render_qa.py`:

```python
class TestManifestBackedChecks(unittest.TestCase):
    """QA must check the contract the renderer actually consumed.

    The Blender engine renders from the manifest's label_content. render_qa read
    brand_name and label_content off the PASSPORT, so wherever the two differ it
    reported a failure against a contract the renderer never saw.
    """

    MANIFEST = {
        "sku_id": "TEST-1",
        "template_id": "T1",
        "label_content": {
            "brand_name_display": "Atomoxetine Generic",
            "active_ingredient_display": "Atomoxetine",
            "dosage_display": "40mg",
            "unit_count_display": "10 Pills",
        },
    }

    @patch("scripts.render_qa.extract_text")
    def test_all_four_fields_found_scores_full_confidence(self, mock_extract):
        mock_extract.return_value = (
            True, "Atomoxetine Generic Atomoxetine 40mg 10 Pills")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["confidence"], 1.0)
        self.assertTrue(all(res["fields"].values()))

    @patch("scripts.render_qa.extract_text")
    def test_a_missing_field_warns_and_never_hard_fails(self, mock_extract):
        mock_extract.return_value = (True, "Atomoxetine 40mg 10 Pills")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "WARN")
        self.assertFalse(res["fields"]["brand_name_display"])
        self.assertAlmostEqual(res["confidence"], 0.75)
        # Its own docstring promises the module never blocks the pipeline.
        self.assertNotIn("HARD_FAIL", res["status"])

    @patch("scripts.render_qa.extract_text")
    def test_dosage_still_matches_on_a_word_boundary(self, mock_extract):
        manifest = json.loads(json.dumps(self.MANIFEST))
        manifest["label_content"]["dosage_display"] = "5 mg"
        mock_extract.return_value = (True, "Atomoxetine Generic Atomoxetine 500mg 10 Pills")
        res = check_image(Path("dummy.png"), manifest)
        self.assertFalse(res["fields"]["dosage_display"],
                         "'5' must not match inside '500'")

    @patch("scripts.render_qa.extract_text")
    def test_ocr_unavailable_is_reported_not_scored(self, mock_extract):
        mock_extract.return_value = (False, "Tesseract binary not found")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "UNAVAILABLE")
        self.assertIsNone(res["confidence"])
```

Add `import json` and `from scripts.render_qa import check_image` to the imports
at the top of the file if they are not already there.

- [ ] **Step 2: Run it and watch it fail**

```bash
python -m unittest tests.test_render_qa -v
```

Expected: the four new tests FAIL (`KeyError: 'fields'` / `'confidence'`). The
two pre-existing word-boundary tests will also fail once `check_image` changes
signature — they are superseded by `test_dosage_still_matches_on_a_word_boundary`
and are deleted in step 3.

- [ ] **Step 3: Rework `check_image` and its callers**

In `scripts/render_qa.py`:

Replace `load_passport` with:

```python
def load_manifest(sku_stem: str, manifests_dir: Path) -> dict | None:
    """The render manifest for a SKU -- the contract the renderer consumed.

    Checking against the passport instead would compare the pixels to a
    document the renderer never read; where the two disagree, that is a false
    alarm rather than a finding.
    """
    path = manifests_dir / f"{sku_stem}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_view(image_path: Path) -> dict | None:
    """The renderer's sidecar saying where the printed faces landed."""
    path = image_path.with_suffix(".view.json")
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
```

Replace the whole of `check_image` with:

```python
# Which manifest fields are checked, and what OCR has to contain for a hit.
# A display string may carry punctuation or a unit the recogniser mangles, so
# the significant token is matched rather than the whole string.
CHECKED_FIELDS = ("brand_name_display", "active_ingredient_display",
                  "dosage_display", "unit_count_display")


def _field_present(expected: str, text: str) -> bool:
    """Is *expected* recognisable in *text*?

    Numeric fields match on a word boundary so '5' does not match inside '500'.
    Word fields match their longest token, which survives a mangled suffix.
    """
    expected = (expected or "").strip()
    if not expected:
        return False
    num = extract_numeric(expected)
    if num and num == expected.split()[0].rstrip("mgMG%"):
        return bool(re.search(rf"\b{re.escape(num)}\b", text))
    tokens = [t for t in re.split(r"[^\w.%-]+", expected) if len(t) >= 3]
    if not tokens:
        return expected.lower() in text.lower()
    longest = max(tokens, key=len)
    if longest.lower() in text.lower():
        return True
    if num:
        return bool(re.search(rf"\b{re.escape(num)}\b", text))
    return False


def check_image(image_path: Path, manifest: dict, view: dict | None = None) -> dict:
    """OCR one render and score it against the manifest that produced it.

    Deskews first when the renderer supplied face corners: on a 27.5-35 degree
    carton, raw OCR misses almost everything (measured 2026-08-03), so scoring a
    skewed frame would report false failures on correct packshots.

    Never returns a hard failure. This is a diagnostic; the module's contract is
    that it does not block the pipeline.
    """
    label = (manifest.get("label_content") or {})
    expected = {f: str(label.get(f, "") or "") for f in CHECKED_FIELDS}
    result = {
        "sku": image_path.stem,
        "ocr_ok": False, "ocr_error": "", "deskewed": False,
        "fields": {}, "found": 0,
        "expected": sum(1 for v in expected.values() if v),
        "confidence": None, "status": "UNKNOWN", "flags": [],
    }

    source = image_path
    corners = (view or {}).get("front_face_px")
    if corners:
        try:
            from src.deskew import flatten_face
            source = flatten_face(image_path, corners)
            result["deskewed"] = True
        except Exception as e:
            result["flags"].append(f"deskew failed, reading the raw frame: {e}")
    else:
        result["flags"].append(
            "no {stem}.view.json; reading the raw frame, where a rotated "
            "carton reads poorly")

    ok, text = extract_text(source)
    result["ocr_ok"] = ok
    if not ok:
        result["ocr_error"] = text
        result["status"] = "UNAVAILABLE"
        result["flags"].append(f"OCR unavailable: {text[:80]}")
        return result

    result["fields"] = {f: _field_present(expected[f], text) if expected[f] else None
                        for f in CHECKED_FIELDS}
    hits = sum(1 for v in result["fields"].values() if v)
    result["found"] = hits
    result["confidence"] = round(hits / result["expected"], 2) if result["expected"] else None

    for field, present in result["fields"].items():
        if present is False:
            result["flags"].append(f"not recognised: {field}={expected[field]!r}")
    if len(text) < MIN_OCR_TEXT_LENGTH:
        result["flags"].append(
            "OCR returned very little text; the image may be blank")
    result["status"] = "OK" if hits == result["expected"] else "WARN"
    return result
```

`extract_text` must accept a `PIL.Image.Image` as well as a path — change its
first lines to:

```python
def extract_text(image) -> tuple[bool, str]:
    """Run OCR on a path or an already-loaded image."""
    if not _TESSERACT_AVAILABLE:
        return False, _TESSERACT_ERROR
    try:
        # Imported locally on purpose. render_qa.py imports PIL.Image inside the
        # same try block as pytesseract, so on a machine without pytesseract the
        # module-level name never exists -- and isinstance(image, Image.Image)
        # would raise NameError instead of reporting "OCR unavailable".
        from PIL import Image as _Image
        img = image if isinstance(image, _Image.Image) else _Image.open(image)
        text = pytesseract.image_to_string(img, config="--psm 6")
        return True, text
    except Exception as e:
        return False, str(e)
```

In `main()`, swap the passport lookup for the manifest and view lookups:

```python
        manifest = load_manifest(sku_stem, args.manifests)
        if manifest is None:
            result = {"sku": sku_stem, "ocr_ok": False,
                      "ocr_error": "Render manifest not found",
                      "deskewed": False, "fields": {}, "found": 0, "expected": 0,
                      "confidence": None, "status": "NO_MANIFEST",
                      "flags": [f"No manifest at {args.manifests / sku_stem}.json"]}
        else:
            result = check_image(img_path, manifest, load_view(img_path))
```

Replace `write_report`'s body between its `report_path.parent.mkdir(...)` line
and its final `with open(...)` block. The `HARD_FAIL` section goes away entirely
— there is no such status any more — and `bool_icon` / `dup_icon` become dead
code, so delete both:

```python
    total = len(results)
    by_status = {s: sum(1 for r in results if r["status"] == s)
                 for s in ("OK", "WARN", "UNAVAILABLE", "NO_MANIFEST")}
    scored = [r for r in results if r["confidence"] is not None]
    mean_conf = round(sum(r["confidence"] for r in scored) / len(scored), 3) if scored else None
    raw_frames = [r for r in results if r["ocr_ok"] and not r["deskewed"]]

    lines = [
        "# RENDER QA REPORT",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Diagnostic, never blocking. Checks that each label string the render "
        "manifest specifies is actually READABLE in the rendered pixels — which "
        "`--dump-scene` cannot tell you, since it sees the text object rather "
        "than the image.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Images checked | {total} |",
        f"| All fields read (OK) | {by_status['OK']} |",
        f"| Some field unread (WARN) | {by_status['WARN']} |",
        f"| OCR unavailable | {by_status['UNAVAILABLE']} |",
        f"| No render manifest | {by_status['NO_MANIFEST']} |",
        f"| Mean confidence | {mean_conf if mean_conf is not None else '—'} |",
        "",
    ]

    if not _TESSERACT_AVAILABLE:
        lines += ["> [!WARNING]",
                  f"> Tesseract is not available: {_TESSERACT_ERROR}",
                  "> Install with: winget install --id UB-Mannheim.TesseractOCR",
                  ""]

    if raw_frames:
        lines += [
            "> [!WARNING]",
            f"> {len(raw_frames)} image(s) were read WITHOUT deskewing, having no "
            "`{stem}.view.json` beside them. A rotated carton reads very poorly "
            "raw, so treat those scores as unreliable rather than as findings. "
            "Re-render them to produce the sidecar.",
            "",
        ]

    lines += [
        "## Results",
        "",
        "| SKU | Deskewed | Brand | Ingredient | Dosage | Count | Confidence | Status |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    mark = lambda v: "—" if v is None else ("OK" if v else "MISS")
    for r in results:
        f = r.get("fields") or {}
        conf = "—" if r["confidence"] is None else f"{r['confidence']:.2f}"
        lines.append(
            f"| {r['sku']} | {'yes' if r['deskewed'] else 'RAW'} "
            f"| {mark(f.get('brand_name_display'))} "
            f"| {mark(f.get('active_ingredient_display'))} "
            f"| {mark(f.get('dosage_display'))} "
            f"| {mark(f.get('unit_count_display'))} "
            f"| {conf} | {r['status']} |")

    flagged = [r for r in results if r["flags"]]
    if flagged:
        lines += ["", "## Flagged", ""]
        for r in flagged:
            lines.append(f"### {r['sku']} ({r['status']})")
            lines += [f"- {flag}" for flag in r["flags"]]
            lines.append("")
```

Finally, delete the two superseded test methods
`test_dosage_word_boundary_matching` and `test_unit_count_word_boundary_matching`
from `tests/test_render_qa.py`; they call `check_image` with a passport.

- [ ] **Step 4: Run the tests**

```bash
python -m unittest tests.test_render_qa -v
```

Expected: the four new tests PASS.

- [ ] **Step 5: Run it against real renders**

```bash
python scripts/render_qa.py --limit 6
```

Expected: `Deskewed` is true for every SKU that has a `.view.json`, and
confidence is markedly better than the raw-frame baseline recorded in the spec.
SKUs rendered before Task 5 have no sidecar and will be flagged as raw — that is
correct reporting, not a bug.

- [ ] **Step 6: Commit**

```bash
git add scripts/render_qa.py tests/test_render_qa.py
git commit -m "Score renders against the manifest, on a flattened face, as a warning

Three changes to the same function. It read brand_name off the passport while
the Blender engine renders from the manifest's label_content, so any divergence
between them was reported as a render defect. It OCR'd the raw 35-degree frame,
where the recogniser misses almost everything. And it returned HARD_FAIL,
contradicting its own docstring's promise never to block the pipeline -- now a
per-field confidence score with warnings, like agent_2_verifier.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: The OCR barrier, on a committed fixture

**Files:**
- Create: `tests/fixtures/ocr/1-min.png`, `tests/fixtures/ocr/1-min.view.json`, `tests/fixtures/ocr/1-min.manifest.json`
- Modify: `tests/test_render_qa.py` (append a class)

**Interfaces:**
- Consumes: everything from Tasks 5, 6 and 7.
- Produces: nothing.

- [ ] **Step 1: Produce and commit the fixture**

`1-min` (Atomoxetine Generic, T1) is the fixture SKU: T1 is the modal template at
287 of 391, and 1-min is already the SKU the calibration work measures against.

```bash
mkdir -p tests/fixtures/ocr
rm -f 02_processing/blender_test_renders/1-min.png 02_processing/blender_test_renders/1-min.view.json
python -m src.blender_renderer --limit 1 --from 1-min
cp 02_processing/blender_test_renders/1-min.png tests/fixtures/ocr/1-min.png
cp 02_processing/blender_test_renders/1-min.view.json tests/fixtures/ocr/1-min.view.json
cp 04_passports/render_manifests/1-min.json tests/fixtures/ocr/1-min.manifest.json
```

Expected: three files, the PNG around 2.7 MB. Confirm the sidecar has a
`front_face_px` array of four pairs before continuing.

- [ ] **Step 2: Write the barrier test**

Append to `tests/test_render_qa.py`:

```python
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ocr"
_HAVE_TESSERACT = render_qa._TESSERACT_AVAILABLE


@unittest.skipUnless(_HAVE_TESSERACT,
                     f"Tesseract unavailable: {render_qa._TESSERACT_ERROR}")
@unittest.skipUnless((FIXTURE_DIR / "1-min.png").exists(),
                     f"OCR fixture missing from {FIXTURE_DIR}")
class TestOCRBarrier(unittest.TestCase):
    """Proves the label text is VISIBLE, which --dump-scene cannot.

    A dump proves a text object holds the right string byte for byte. It cannot
    see a correct string that fell outside the camera, ended up behind another
    face, or rendered white on white. This can.

    A committed fixture rather than a live render, because renders are not
    tracked by git and an opt-in check is not a barrier. The slow gate below
    re-renders the same SKU so the fixture cannot silently go stale.
    """

    @classmethod
    def setUpClass(cls):
        cls.png = FIXTURE_DIR / "1-min.png"
        cls.manifest = json.loads(
            (FIXTURE_DIR / "1-min.manifest.json").read_text(encoding="utf-8"))
        cls.view = json.loads(
            (FIXTURE_DIR / "1-min.view.json").read_text(encoding="utf-8"))

    def test_the_brand_name_is_readable_off_the_render(self):
        res = render_qa.check_image(self.png, self.manifest, self.view)
        self.assertTrue(res["deskewed"], "the fixture's view sidecar was not used")
        self.assertTrue(
            res["fields"]["brand_name_display"],
            f"brand name not recognised; flags={res['flags']}")

    def test_at_least_three_of_four_label_fields_are_readable(self):
        res = render_qa.check_image(self.png, self.manifest, self.view)
        # A threshold, not an exact string: Tesseract is a third-party
        # recogniser and an upgrade may change its output. 5.4.0.20240606 is the
        # version this was calibrated against.
        self.assertGreaterEqual(
            res["found"], 3,
            f"only {res['found']}/{res['expected']} fields read; "
            f"flags={res['flags']}")

    def test_deskewing_is_what_makes_it_readable(self):
        """Without this, someone could delete the deskew call and the two tests
        above might still pass by luck on one lucky fixture."""
        with_deskew = render_qa.check_image(self.png, self.manifest, self.view)
        without = render_qa.check_image(self.png, self.manifest, None)
        self.assertFalse(without["deskewed"])
        self.assertGreater(
            with_deskew["found"], without["found"],
            "deskewing did not improve recognition; either the corners are "
            "wrong or the deskew step is not being applied")


@unittest.skipUnless(os.environ.get("PHARMAGEN_SLOW_TESTS"),
                     "set PHARMAGEN_SLOW_TESTS=1 to re-render the fixture SKU")
@unittest.skipUnless(_HAVE_TESSERACT,
                     f"Tesseract unavailable: {render_qa._TESSERACT_ERROR}")
class TestOCRAgainstAFreshRender(unittest.TestCase):
    """The same assertions against output rendered now, so the committed
    fixture cannot drift away from what the renderer actually produces."""

    def test_a_fresh_render_of_the_fixture_sku_still_reads(self):
        import subprocess
        import sys
        out_dir = Path(render_qa.DEFAULT_PROCESSED_DIR)
        png = out_dir / "1-min.png"
        for stale in (png, png.with_suffix(".view.json")):
            if stale.exists():
                stale.unlink()
        proc = subprocess.run(
            [sys.executable, "-m", "src.blender_renderer", "--limit", "1",
             "--from", "1-min"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertTrue(png.exists(), "the render produced no PNG")

        manifest = json.loads(
            (Path(render_qa.DEFAULT_MANIFESTS_DIR) / "1-min.json")
            .read_text(encoding="utf-8"))
        view = render_qa.load_view(png)
        res = render_qa.check_image(png, manifest, view)
        self.assertGreaterEqual(res["found"], 3, f"flags={res['flags']}")
```

Add `import os`, `from src.utils import PROJECT_ROOT` and
`from scripts import render_qa` to the module's imports.

- [ ] **Step 3: Run it**

```bash
python -m unittest tests.test_render_qa -v
```

Expected: `TestOCRBarrier`'s three tests PASS; `TestOCRAgainstAFreshRender`
skips. If `test_at_least_three_of_four_label_fields_are_readable` fails, do not
lower the threshold — read `res["flags"]` and check the corner order first.

- [ ] **Step 4: Run the slow gate once**

```bash
PHARMAGEN_SLOW_TESTS=1 python -m unittest tests.test_render_qa.TestOCRAgainstAFreshRender -v
```

Expected: PASS in roughly 60 seconds.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr tests/test_render_qa.py
git commit -m "Make text visibility a barrier, not an opt-in

--dump-scene proves a label row holds the right string byte for byte. It cannot
prove the string is visible: correct text can still fall outside the camera, sit
behind another face, or render white on white. OCR sees exactly that, which is
why the two checks are complementary rather than redundant.

The fixture is committed because renders are not tracked by git and a check that
skips by default is not a barrier. The third assertion compares deskewed against
raw recognition, so removing the deskew step fails the suite instead of passing
by luck. A slow-gated test re-renders the same SKU so the fixture cannot drift.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Verify the barrier by breaking it, then refresh the record

**Files:**
- Modify: `00_PROJECT_STATE/CURRENT_STATE.md`
- Modify: `00_PROJECT_STATE/NEXT_STEPS.md`
- Modify: `08_ops/DEPENDENCY_INVENTORY.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: nothing.

- [ ] **Step 1: Run the whole suite**

```bash
python -m unittest discover -s tests
```

Expected: roughly 158 tests, 0 failures, 1 skip (the calibration gate) plus the
slow OCR gate. Record the exact numbers; step 4 writes them down.

- [ ] **Step 2: Mutation-test the barrier**

Each mutation must fail its own test and no others. Apply one, run the suite,
revert with `git checkout <file>`, then move to the next.

| # | Mutation | Must fail |
|---|---|---|
| 1 | In `src/passport_generator.py`, change `docs_dir = PROJECT_ROOT / "06_docs"` to `docs_dir = Path("docs")` | `tests.test_pipeline_smoke` |
| 2 | In `scripts/catalogue_sweep.py`, change `md_path.write_text(...)` back to `(STATE_DIR / "sweep_report.md").write_text(...)` | `tests.test_sweep_reporting` |
| 3 | In `scripts/render_qa.py`, set `DEFAULT_PROCESSED_DIR = Path("render_output/processed")` | `tests.test_script_paths` |
| 4 | In `scripts/render_qa.py`'s `check_image`, replace `source = flatten_face(...)` with `source = image_path` | `tests.test_render_qa.TestOCRBarrier.test_deskewing_is_what_makes_it_readable` |

```bash
# Pattern for each: mutate, run, revert.
python -m unittest discover -s tests 2>&1 | tail -20
git checkout <the file you mutated>
```

Any mutation that leaves the suite green means that test is decorative. Rewrite
the test — do not weaken the mutation.

- [ ] **Step 3: Record the mutation results**

Write the four outcomes into the commit message in step 5. If a mutation failed
a test other than its own, say which; overlapping coverage is fine, silence is not.

- [ ] **Step 4: Refresh the stale claims**

In `00_PROJECT_STATE/CURRENT_STATE.md`:
- Working branch is at the new HEAD, not `badc8b7`.
- Test count is the number from step 1, not 146.
- Delete the "`numpy` is undeclared" gap — it is in `requirements.txt` as
  `numpy>=1.24`.
- Replace "No post-render verification anywhere in the project" with what now
  exists: OCR against the manifest on a deskewed face, plus the pixel and scene
  passes already in `catalogue_sweep.py` / `src/measure.py`. Note the remaining
  gap: the brand badge (`palette.primary`) is still unchecked.

In `00_PROJECT_STATE/NEXT_STEPS.md`: remove item 3 (post-render verification),
which this plan delivers. Leave items 1 and 9 — the carton-proportions decision
and the small-print floor are untouched.

In `08_ops/DEPENDENCY_INVENTORY.md`: add rows for the Blender executable (still
missing, and this fork's default engine) and for Tesseract:

```markdown
| Tesseract OCR | 5.4.0.20240606 | System binary, `C:\Program Files\Tesseract-OCR\tesseract.exe` | Post-render QA (`scripts/render_qa.py`). NOT on PATH; `render_qa` probes the absolute path. Install: `winget install --id UB-Mannheim.TesseractOCR`. Absent → the OCR tests skip. |
```

In `CLAUDE.md`, under "Fork-specific gotchas", add:

```markdown
**OCR needs the face flattened first.** The carton is rotated 27.5-35 degrees
about Z, and Tesseract reads a skewed face very badly — measured, "Atomoxetine
Generic" comes back as "Germetine" and one render returns an empty string, in
every page-segmentation mode. The same strings drawn flat in the same vendored
font read 4 of 4. `render_driver.py` therefore emits `{stem}.view.json` with the
printed faces' corners in image pixels, and `src/deskew.py` flattens the front
face before `scripts/render_qa.py` reads it. Do not recover those corners from
the image: a colour mask keyed on `palette.accent` cannot separate the accent
stripe from the brand badge.
```

- [ ] **Step 5: Commit**

```bash
git add 00_PROJECT_STATE/CURRENT_STATE.md 00_PROJECT_STATE/NEXT_STEPS.md 08_ops/DEPENDENCY_INVENTORY.md CLAUDE.md
git commit -m "Verify the barrier by breaking it, and update what the repo claims

Four mutations, each reintroducing a bug that actually shipped: Path(\"docs\") in
Stage 1, the hardcoded sweep_report.md, render_output/processed in render_qa, and
a removed deskew call. Each failed its own test. [Record the actual outcomes
here, including any test that failed for more than one mutation.]

CURRENT_STATE listed numpy as undeclared when requirements.txt has numpy>=1.24,
cited a branch four commits stale, and said there was no post-render
verification anywhere -- which this plan makes untrue. DEPENDENCY_INVENTORY had
no row for Blender despite it being this fork's default engine, and none for
Tesseract.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Push**

```bash
git push origin dev
```

---

## Self-review notes

**Spec coverage.** F1 → Task 4. F2 → Tasks 1 and 2. F3 → Task 3. F4(a) → Task 5,
F4(b) → Task 6, F4(c) → Task 7, F4(d) → Task 8. Mutation testing → Task 9 step 2.
Risk "driver change moves pixels" → Task 5 step 6. Risk "Tesseract upgrade" →
threshold assertions in Task 8 plus the inventory row in Task 9. Risk "fixture
drift" → the slow-gated class in Task 8. Doc refresh → Task 9 step 4.

**Deliberately deferred, and why.** The spec's per-template OCR hit-rate sweep
across the 30-SKU group is a *reporting* run, not a code change; it needs the
whole group re-rendered so every SKU has a `.view.json`. Run it after Task 8 with
`python scripts/catalogue_sweep.py --group top30` followed by
`python scripts/render_qa.py`, and treat a template scoring below 3/4 as a
finding to open separately. It is not a task here because it produces no
committed code and its outcome cannot be predicted.

**Known interface risk.** Task 5 assumes `tests/test_render_driver.py` exposes a
`_dump_scene()` helper returning parsed JSON. If it does not, step 1 says to add
one modelled on `tests/test_blender_carton.py:115-130`.
