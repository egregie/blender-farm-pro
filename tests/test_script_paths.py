"""Every operator script must point at directories this fork actually has.

The fork remapped every path onto numbered folders. A script that kept the
source project's layout does not crash on import -- it runs, finds nothing, and
reports an empty result, which reads exactly like a clean pass. scripts/
render_qa.py defaulted to render_output/processed, a directory this repository
has never contained.

RELIANCE THIS TEST DEPENDS ON, NOT SOMETHING IT VERIFIES: coverage below walks
module-level `DEFAULT_*` `Path` constants, not each script's `argparse` parser
directly. That finds every current script's path defaults only because all six
of them happen to route their `--dir`/`--input`/`--output`/etc. defaults
through a `DEFAULT_*` constant at import time. An inline
`parser.add_argument(..., default=Path("render_output/x"))`, with no
module-level constant behind it, would be invisible to this test and pass
silently while pointing at a directory the fork does not have. Follow that
convention in any new operator script, or extend this test to read
`parser.parse_args([]).<dest>` (or inspect `parser._actions` for `default`
values) instead of `dir(mod)`.
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
        """A DEFAULT_ path may legitimately not exist yet, but only in one of
        two distinct ways -- conflating them is a category error:

          - it names an OUTPUT FILE (has a suffix, e.g. a generated report):
            the script itself creates the file on first write, the same way
            `open(path, "w")` only needs its directory. An existing PARENT is
            therefore sufficient on its own; CREATABLE (a set of directory
            *names*) has no bearing on files and must not be extended for one.
          - it names a DIRECTORY a script is allowed to create on first use
            (its name is in CREATABLE): for those we additionally require the
            parent to exist, to distinguish "not written yet" from "wrong
            layout entirely" (a directory could otherwise be missing for any
            reason, not just "not created yet").

        Anything else missing is a stale path from the source project's layout.
        """
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
                    if value.suffix:
                        # File-valued default: an existing parent directory is
                        # all a script needs to be able to write this file.
                        self.assertTrue(
                            value.parent.exists(),
                            f"{path.name}.{name} -> {value}: this names a "
                            f"file the script writes on first run, but even "
                            f"its parent {value.parent} is missing, so this "
                            f"is a stale path from the source project's "
                            f"layout")
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

    def test_image_postprocessor_output_does_not_collide_with_canonical_stage3(self):
        """scripts/image_postprocessor.py is a non-canonical alternative to
        src/image_processor.py (see scripts/README.md), but both scripts
        derive the same {stem}.webp filename from an input PNG. If they ever
        again pointed at the same directory, running the non-canonical script
        would silently overwrite the canonical Stage 3 output --
        01_input_raster/gemini_renders_final, where git tracks 389 real
        deliverables -- with a 2048px/quality-85 file that violates the
        documented Stage 3 contract (1600px, <=500KB auto-tuned).
        """
        import scripts.image_postprocessor as postprocessor
        from src.utils import load_config, resolve_path

        canonical_output = resolve_path(load_config()["image_processor"]["output_dir"])
        self.assertNotEqual(
            postprocessor.DEFAULT_OUTPUT_DIR, canonical_output,
            "image_postprocessor.py's DEFAULT_OUTPUT_DIR must not be "
            "image_processor.output_dir -- that key is src/image_processor.py's "
            "canonical Stage 3 output directory")


if __name__ == "__main__":
    unittest.main()
