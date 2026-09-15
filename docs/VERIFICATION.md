# Verification

Reconciled against Build Omarchy Plugins commit
`26ee1e7fc57e4089daea57ff0c51e6a10659e401`.

## Host and source

Observed on 2026-09-14/15, Arch Linux, Omarchy `dev (4ee6d4ee)`, source commit
`4ee6d4eeea176b0bf4014ce8b82a148a9433efff`, one eDP-1 display at 1.25 scale.
The UI reports revision `native-3`. Exact source digests are in `source-evidence.json`.
No claim is made that every Omarchy 4.x release or monitor arrangement was tested.

## Passed

- `./tests/run`: generated manifest validator, installed Omarchy validator,
  24 backend tests and one wrapper running the production navigation/fixture
  JavaScript in QtTest (six behavioral tests plus init/cleanup).
- Backend tests cover exact matching, read-only scans, cleanup/restore preservation,
  conflict refusal, stale/unknown/duplicate selection, symlink roots and candidates,
  nested links, mounted content, protected directories, alternate packages,
  interrupted/partial moves, permissions, invalid tokens, permanent recovery
  deletion, command deadlines/output bounds, fixed uninstall argv, and JSON-safe
  file identity. Mutation tests use temporary directories only.
- Current bundle `validate_plugin.py --json --security`: valid, no warnings,
  no findings; process/collected-input/privilege capabilities require manual review.
- Current bundle `demo_preflight.py`: PASS. Python owns signals/finally cleanup;
  the shell entry point documents that delegation.
- `./demo/run --shell-path /home/tcballard/omarchy`: real hosted native components;
  fictional fixture verified; keyboard search, drill-down, file selection,
  cleanup/restore/delete confirmations with Cancel default, arrow navigation,
  repeated open, Escape and outside-click dismissal. Desktop state restored.
- `preview.png` and `demo-overview.png`: cropped actual hosted panels, visually
  inspected; no generated mockup and no personal file paths in the captures.
- Real mode: the hosted panel loaded 38 native desktop apps with `busy:false`,
  `failed:false`, `demo:false` and no selected items. No plugin-specific errors
  appeared in the checked runtime log.

## Limits and unrun checks

- Full package uninstallation was not performed on the user's machine. The fixed
  terminal/pacman handoff is covered with a mocked process; actual authentication
  and removal require a disposable test machine.
- Permanent cleanup and restore were tested with temporary data, not personal files.
- One monitor and a horizontal bar were available. Vertical sizing comes from the
  native WidgetButton, and anchoring/dismissal from KeyboardPanel; vertical and
  multi-monitor presentation have not been observed on this host.
- Plain qmllint initially lacked the synthetic `qs.*` imports; its zero exit code
  was not treated as proof. Actual hosted component loading and QtTest are recorded
  separately above.
- GitHub CI passed on source commit `3f81203d67f5245bca0f90c148dd2704feb8e1e1`
  ([run 34931527301](https://github.com/tcballard/omarchy-plugin-tidyup/actions/runs/34931527301)).
  A fresh independent local Git clone also passed all 25 checks.
- Live installation used a development symlink. A full standard Git add, an update
  between released versions, and removal of that installation have not been exercised.
  These remain release verification gaps; source-clone tests do not replace them.

## Resolved failures

The initial harness used legacy Hyprland dispatcher syntax. It now uses the host's
Lua dispatchers and retained its backup until restoration was verified. Early
runs exposed cached components and pointer/focus interference; a source revision
readiness check, a shell reload, pre-positioning the pointer, and PointerMoveGate
resolved those issues. Failed attempts are not counted as passing evidence.
