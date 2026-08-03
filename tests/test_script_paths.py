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


if __name__ == "__main__":
    unittest.main()
