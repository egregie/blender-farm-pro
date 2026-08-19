"""Tests for Stage 2 engine selection.

Covers the two places the choice is made: main.py resolves which engine a run
wants, and src/render_stage.py is the facade that actually dispatches to it.

Dispatch is exercised against stand-in engine modules rather than the real
ones, because importing either engine opens a log file as a side effect. The
real modules are checked separately, by resolution rather than import, so a
renamed or deleted engine still fails a test.
"""
import io
import sys
import types
import importlib.util
import unittest
from contextlib import redirect_stderr
from unittest import mock

import src as src_pkg
from src import render_stage

import main


def _stub_engine():
    """A module-shaped object that records the argv its main() was called with."""
    mod = types.ModuleType("stub_engine")
    mod.seen_argv = None

    def _main():
        mod.seen_argv = list(sys.argv)

    mod.main = _main
    return mod


class DispatchHarness(unittest.TestCase):
    """Runs render_stage.main() with both engines replaced by stand-ins."""

    def dispatch(self, argv, config_engine="gemini"):
        gemini, blender = _stub_engine(), _stub_engine()
        with mock.patch.object(src_pkg, "rpa_orchestrator", gemini, create=True), \
             mock.patch.object(src_pkg, "blender_renderer", blender, create=True), \
             mock.patch.dict(sys.modules, {"src.rpa_orchestrator": gemini,
                                           "src.blender_renderer": blender}), \
             mock.patch.object(render_stage, "load_config",
                               return_value={"render": {"engine": config_engine}}), \
             mock.patch.object(sys, "argv", ["render_stage"] + argv):
            err = io.StringIO()
            with redirect_stderr(err):
                render_stage.main()
        return gemini, blender, err.getvalue()


class TestEngineRegistry(unittest.TestCase):
    def test_every_registered_engine_module_is_importable(self):
        """Resolution, not import — importing an engine opens a log file."""
        for engine, module in render_stage.ENGINE_MODULES.items():
            with self.subTest(engine=engine):
                self.assertIsNotNone(importlib.util.find_spec(module),
                                     f"{engine} points at missing module {module}")

    def test_stage_two_goes_through_the_facade_not_an_engine(self):
        """The architectural invariant: main.py must never name an engine."""
        self.assertEqual(main.MODULE[main.STAGE_RENDER], "src.render_stage")
        self.assertNotIn(main.MODULE[main.STAGE_RENDER],
                         render_stage.ENGINE_MODULES.values())

    def test_registry_and_cli_choices_agree(self):
        self.assertEqual(set(main.RENDER_ENGINES), set(render_stage.ENGINE_MODULES))


class TestDispatch(DispatchHarness):
    def test_explicit_blender_reaches_the_blender_engine(self):
        gemini, blender, _ = self.dispatch(["--engine", "blender"])
        self.assertIsNotNone(blender.seen_argv)
        self.assertIsNone(gemini.seen_argv)

    def test_explicit_gemini_reaches_the_gemini_engine(self):
        gemini, blender, _ = self.dispatch(["--engine", "gemini"], config_engine="blender")
        self.assertIsNotNone(gemini.seen_argv)
        self.assertIsNone(blender.seen_argv)

    def test_omitted_engine_follows_the_config(self):
        gemini, blender, _ = self.dispatch(["--all"], config_engine="blender")
        self.assertIsNotNone(blender.seen_argv)
        self.assertIsNone(gemini.seen_argv)

    def test_unknown_engine_is_refused(self):
        with self.assertRaises(SystemExit):
            self.dispatch(["--engine", "midjourney"])


class TestArgvHandover(DispatchHarness):
    def test_engine_flag_is_stripped_before_the_engine_sees_argv(self):
        """The engines have their own parsers and do not know --engine exists."""
        _, blender, _ = self.dispatch(["--engine", "blender", "--limit", "5"])
        self.assertNotIn("--engine", blender.seen_argv)
        self.assertNotIn("blender", blender.seen_argv[1:])

    def test_every_other_flag_is_passed_through_untouched(self):
        _, blender, _ = self.dispatch(
            ["--engine", "blender", "--limit", "5", "--from", "50-min", "--all"])
        self.assertEqual(blender.seen_argv[1:], ["--limit", "5", "--from", "50-min", "--all"])

    def test_argv_zero_is_preserved(self):
        _, blender, _ = self.dispatch(["--engine", "blender"])
        self.assertEqual(blender.seen_argv[0], "render_stage")


class TestExperimentalBanner(DispatchHarness):
    def test_non_gemini_engine_announces_itself(self):
        _, _, err = self.dispatch(["--engine", "blender"])
        self.assertIn("blender", err)

    def test_gemini_stays_quiet(self):
        _, _, err = self.dispatch(["--engine", "gemini"])
        self.assertEqual(err, "")


class TestResolveRenderEngine(unittest.TestCase):
    """main.py: an explicit flag beats config, config beats the built-in default."""

    def test_explicit_flag_wins_over_config(self):
        args = main.parse_args(["--render-only", "--render-engine", "gemini"])
        self.assertEqual(
            main.resolve_render_engine(args, {"render": {"engine": "blender"}}), "gemini")

    def test_config_used_when_flag_absent(self):
        args = main.parse_args(["--render-only"])
        self.assertEqual(
            main.resolve_render_engine(args, {"render": {"engine": "blender"}}), "blender")

    def test_falls_back_to_gemini_when_config_is_silent(self):
        args = main.parse_args(["--render-only"])
        self.assertEqual(main.resolve_render_engine(args, {}), "gemini")


class TestBuildCmd(unittest.TestCase):
    """main.py builds the subprocess argv for each stage."""

    def _render_cmd(self, argv):
        return main.build_cmd(main.STAGE_RENDER, main.parse_args(argv))

    def test_engine_forwarded_only_when_explicitly_requested(self):
        with_flag = self._render_cmd(["--render-only", "--render-engine", "blender"])
        self.assertIn("--engine", with_flag)
        self.assertIn("blender", with_flag)

        without = self._render_cmd(["--render-only"])
        self.assertNotIn("--engine", without,
                         "omitting the flag must leave the facade to read config")

    def test_render_stage_module_is_invoked(self):
        cmd = self._render_cmd(["--render-only"])
        self.assertEqual(cmd[1:3], ["-m", "src.render_stage"])

    def test_no_limit_means_the_whole_catalogue(self):
        self.assertIn("--all", self._render_cmd(["--render-only"]))

    def test_limit_replaces_all(self):
        cmd = self._render_cmd(["--render-only", "--limit", "5"])
        self.assertIn("--limit", cmd)
        self.assertNotIn("--all", cmd)

    def test_from_stem_is_forwarded(self):
        cmd = self._render_cmd(["--render-only", "--from", "50-min"])
        self.assertEqual(cmd[cmd.index("--from") + 1], "50-min")

    def test_passports_stage_takes_no_engine_flags(self):
        cmd = main.build_cmd(main.STAGE_PASSPORTS,
                             main.parse_args(["--render-engine", "blender"]))
        self.assertEqual(cmd[1:], ["-m", "src.passport_generator"])


class TestStageThreeFollowsTheEngine(unittest.TestCase):
    """Stage 3 must read where the SELECTED engine wrote, and write somewhere else.

    Until 2026-08-10 `image_processor.source_dir` was a constant naming the Gemini
    directory. Under `render.engine: blender` the pipeline rendered packshots into
    02_processing/blender_test_renders, Stage 3 converted
    01_input_raster/gemini_renders_raw, and `main.py --full` reported success
    having processed somebody else's renders.
    """

    def _cfg(self, engine):
        from src.utils import load_config
        cfg = load_config()
        cfg["render"]["engine"] = engine
        return cfg

    def test_raw_dir_follows_the_engine(self):
        cfg = self._cfg("blender")
        self.assertEqual(render_stage.raw_output_dir(cfg, "blender"),
                         cfg["blender"]["output_dir"])
        self.assertEqual(render_stage.raw_output_dir(cfg, "gemini"),
                         cfg["paths"]["renders_raw"])

    def test_final_dir_follows_the_engine(self):
        cfg = self._cfg("blender")
        self.assertEqual(render_stage.final_output_dir(cfg, "gemini"),
                         cfg["paths"]["renders_final"])
        self.assertTrue(render_stage.final_output_dir(cfg, "blender"))

    def test_the_two_engines_never_share_a_directory(self):
        """Both name their files after the SKU stem, so one shared directory means
        the second engine to run overwrites the first one's finished work."""
        cfg = self._cfg("blender")
        for fn in (render_stage.raw_output_dir, render_stage.final_output_dir):
            with self.subTest(resolver=fn.__name__):
                self.assertNotEqual(fn(cfg, "blender"), fn(cfg, "gemini"))

    def test_an_explicit_path_overrides_the_engine(self):
        """`source_dir` stays a live override rather than a key that quietly
        stopped mattering -- the failure the red team flagged before this shipped."""
        import importlib
        import src.image_processor as ip
        cfg = self._cfg("blender")
        cfg["image_processor"] = dict(cfg["image_processor"], source_dir="07_input")
        with mock.patch("src.utils.load_config", return_value=cfg):
            reloaded = importlib.reload(ip)
            self.assertTrue(reloaded.SOURCE_DIR.replace("\\", "/").endswith("07_input"))
        importlib.reload(ip)          # restore real module state for other tests

    def test_stage_three_imports_no_engine(self):
        """BND-001: engine selection lives in the facade. Stage 3 must not learn
        which engine ran by importing it -- that would break the boundary and drag
        Selenium into the image pipeline besides."""
        for name in ("src.rpa_orchestrator", "src.blender_renderer"):
            sys.modules.pop(name, None)
        import importlib
        import src.image_processor as ip
        importlib.reload(ip)
        for name in ("src.rpa_orchestrator", "src.blender_renderer"):
            self.assertNotIn(name, sys.modules, f"Stage 3 pulled in {name}")


if __name__ == "__main__":
    unittest.main()
