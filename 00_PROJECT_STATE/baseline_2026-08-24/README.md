# baseline_2026-08-24

The only source for the "before" column of every table in
[`../TOOLING_MIGRATION.md`](../TOOLING_MIGRATION.md). **Written once on
2026-08-24 and not touched again** — a baseline that moves is not a baseline.

Taken at commit `9376905` ("The corners are an input nothing checks, and six
cartons still carry it"), with the tree otherwise clean apart from a
pre-existing modification to `audit.md` and untracked sweep reports, neither of
which this migration reads or writes.

| path | what it is | how it was taken |
|---|---|---|
| `design_specs/` | 29 `design_spec.json`, renamed `<folder>.design_spec.json` | copied from `Reference Templates/*/` |
| `render_manifests/` | all 391 Stage 1 manifests, contract 1.8 | copied from `04_passports/render_manifests/` |
| `design_qa.json` | the committed D-6 report | copied from `00_PROJECT_STATE/` |
| `render_calibration.json` | the transfer curves, driver fingerprint `351a55dbff2d837c` | copied from `00_PROJECT_STATE/` |
| `design_coverage.json` | coverage over all 28 folders | **regenerated**: `python scripts/design_coverage.py --out …` |
| `renders/` | 28 group packshots + their `.view.json` and `.job.json` | copied from `02_processing/blender_test_renders/` |

## The group figures this baseline holds

From `design_coverage.json`, over 28 cartons:

| figure | baseline |
|---|---|
| `pixel_agreement` | **99.18%** |
| `print_agreement` | **52.79%** |
| `truth_agreement` | **95.36%** |
| drawn off print (`spec_off_print_pct`) | **0.76%** |

`151-min`, `230-min` and `346-min` report `truth_agreement` as `n/a` rather than
`0.0` — they carry no component a person called `print`, so there is nothing for
a spec to agree or disagree with. They are excluded from every acceptance test in
this migration **by name**, which is the brief's rule and not a convenience.

Note this group `truth_agreement` of 95.36% is not the 95.59% `CLAUDE.md` quotes.
That figure was recorded at an earlier moment; 95.36% is what the instrument
returns against the tree as it stands today, and it is what "before" means here.

## `renders/` should not be committed

83 MB of PNG. `.gitignore` already excludes `02_processing/blender_test_renders/`
on the grounds that Blender output is regenerable and deterministic, and the same
reasoning applies to a copy of it.

**It is deliberately NOT added to `.gitignore` here**: that file is outside this
task's allowed changes, and silently widening the ignore list is not a decision a
migration gets to take on its own. The directory is therefore untracked and
visible in `git status`; leave it that way, or have the owner add the ignore rule.

The copy still earns its place on disk: after Phase 3 the driver changes, so
these pixels stop being reproducible from the manifests beside them. They are the
only record of what the carton looked like before, and a local safety net is
worth more than an 83 MB commit.
