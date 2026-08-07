"""Runs the stages the way the pipeline runs them, which the unit suite does not.

src/passport_generator.py wrote its override audit to Path("docs"), relative to
the working directory. All 149 tests passed while Stage 1 was broken: nothing
exercised its main() to the end. It crashed after writing all 391 passports, and
only a live pipeline run found it.

The working directory is the point. Running from the repository root would not
have caught it -- Path("docs") resolves there. Every subprocess below therefore
runs from a temporary directory.

Exit code alone is not enough to catch this class of bug: a path bug that
*misplaces* output without raising exits 0 just like a correct run does. So
every subprocess run here is also checked for what it left behind in its own
working directory -- the real invariant this task exists to guard is "no stage
writes anything relative to the working directory," and that has to be asserted
directly rather than inferred from exit codes and output counts alone.
"""
import hashlib
import os
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


def _run_from_elsewhere(module: str, *args) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run a stage module as its own process, from a directory that is NOT the
    repository root, with PROJECT_ROOT on sys.path so imports still resolve.

    Returns (proc, leftover) where `leftover` is the sorted list of names the
    subprocess left behind in its own working directory. `leftover` is
    captured with the TemporaryDirectory still alive -- checking after the
    `with` block exits would find nothing, because cleanup would have already
    deleted whatever the subprocess wrote there. An empty `leftover` is the
    actual invariant this module exists to check: exit code 0 alone does not
    prove a stage anchored every path to PROJECT_ROOT, because a stage that
    writes into the working directory by mistake still exits 0 -- it just
    leaves something behind where nothing should be.
    """
    with tempfile.TemporaryDirectory() as alien_cwd:
        env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT),
               "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=alien_cwd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=STAGE_TIMEOUT_S)
        leftover = sorted(p.name for p in Path(alien_cwd).iterdir())
    return proc, leftover


class TestStageOneRunsEndToEnd(unittest.TestCase):
    def test_stage_one_completes_and_is_idempotent(self):
        expected = len(list(JSON_DIR.glob("*.json")))
        self.assertGreater(expected, 0, f"no input passports in {JSON_DIR}")

        before_md = _digest(MD_DIR, "*.md")
        before_manifests = _digest(MANIFEST_DIR, "*.json")

        proc, leftover = _run_from_elsewhere("src.passport_generator")
        self.assertEqual(
            proc.returncode, 0,
            f"Stage 1 exited {proc.returncode}\nSTDERR:\n{proc.stderr[-3000:]}")
        self.assertEqual(
            leftover, [],
            f"Stage 1 wrote {leftover} into its working directory; "
            f"every path must be anchored to PROJECT_ROOT")

        after_md = _digest(MD_DIR, "*.md")
        after_manifests = _digest(MANIFEST_DIR, "*.json")

        self.assertEqual(len(after_md), expected,
                         "Stage 1 did not write one Markdown prompt per passport")
        self.assertEqual(len(after_manifests), expected,
                         "Stage 1 did not write one render manifest per passport")
        # Idempotence is a documented invariant of this fork; assert it rather
        # than trusting it. A diff here has two possible explanations, not
        # one: genuine non-determinism in Stage 1, OR the 391 tracked
        # manifests/prompts were simply stale before this run started -- the
        # normal state after any legitimate Stage 1 edit that changes their
        # content. This run's own `after_*` digest just became the new
        # baseline on disk, so a second run right now would pass either way;
        # that is what tells the two apart, not this message alone.
        self.assertEqual(before_md, after_md,
                         "Stage 1 changed its Markdown output on a re-run -- "
                         "either Stage 1 is non-deterministic, or the "
                         "committed passports_md were merely stale before "
                         "this run (expected after a legitimate Stage 1 "
                         "edit); re-run this test once more to tell them "
                         "apart -- a stale-fixture diff will not repeat")
        self.assertEqual(before_manifests, after_manifests,
                         "Stage 1 changed its manifests on a re-run -- "
                         "either Stage 1 is non-deterministic, or the "
                         "committed render_manifests were merely stale "
                         "before this run (expected after a legitimate "
                         "Stage 1 edit); re-run this test once more to tell "
                         "them apart -- a stale-fixture diff will not repeat")


class TestStageTwoFacadeDispatches(unittest.TestCase):
    def test_blender_estimate_is_a_clean_dry_run(self):
        proc, leftover = _run_from_elsewhere(
            "src.render_stage", "--engine", "blender", "--estimate")
        self.assertEqual(
            proc.returncode, 0,
            f"Stage 2 --estimate exited {proc.returncode}\n"
            f"STDERR:\n{proc.stderr[-3000:]}")
        self.assertEqual(
            leftover, [],
            f"Stage 2 --estimate wrote {leftover} into its working directory; "
            f"every path must be anchored to PROJECT_ROOT")
        self.assertIn("[blender]", proc.stdout + proc.stderr,
                      "the blender engine did not report an estimate")


if __name__ == "__main__":
    unittest.main()
