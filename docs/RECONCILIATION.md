# Bundle reconciliation

Audit target: working tree of Omarchy TidyUp, 2026-09-14.
Authoritative bundle: 26ee1e7fc57e4089daea57ff0c51e6a10659e401.
The earlier local bundle was 4b3b3d48dc9ad3e20affbf0fcc22524f2171bcee.

| Contract | Earlier mismatch | Correction / required evidence |
| --- | --- | --- |
| Design before implementation; preserve user steering | Late design record; stale panel-only scope | DESIGN.md updated before replacement QML |
| Smallest kind set and bar ownership | Bar launcher plus separately hosted panel | One bar-widget owning a private anchored panel |
| Native popup positioning/focus | Custom PanelWindow, dimensions and focus timer | KeyboardPanel owns geometry, dismissal and focus |
| Native visual hierarchy | Large sidebar, custom cards and marketing subtitle | Compact PanelHero/section/separator/list composition |
| Keyboard parity | Partial Qt focus chain; no complete live exercise | PanelKeyCatcher with shared pointer/keyboard cursor and native panel switching |
| Explicit state and errors | Loading and close behavior unverified | Helper state transitions and host lifecycle tests |
| Test evidence belongs to source | Backend tests presented before QML proof | Exact source-bound verification record; no lint-success claim with missing imports |
| Demo is deterministic and reversible | Direct live link/enable, no complete harness | Guarded harness, configuration/workspace/cursor restoration and ready check |
| Product artifacts are real | Scaffold preview and example fixture remained | Replace with actual fixture, observed screenshot and accurate docs |
| Build is not publication | User supplied target repository | Initial source targets that repository; no marketplace submission |

Pre-reconciliation live setup: development symlink at
`~/.config/omarchy/plugins/io.github.tcballard.tidyup`, original shell configuration
backup `/tmp/tidyup-live-check-2i3mxqep/shell.json`. Preserve unrelated current
configuration; restore only TidyUp entries rather than overwriting a whole file
that may have changed during the session.

This table records findings and intended corrections, not completed verification.
See VERIFICATION.md for observed results.

## Completed corrections

The final source uses only `bar-widget` with a private anchored KeyboardPanel;
its visual structure and keyboard dispatch use the native components named above.
The real panel was visually inspected and captured in `preview.png`.
PointerMoveGate prevents keyboard selection from being replaced by synthetic hover
when layout changes. Live tests exercised app search/drill-down, selection,
Cancel-first cleanup/restore/delete dialogs, repeated open, Escape and outside click.
Demo preflight passes; the harness restores configuration, workspace and cursor.

The initial setup was reconciled without overwriting unrelated settings. The final
development link points to `~/Source/omarchy-plugin-tidyup`; the bin widget is enabled
in the right bar section as requested. No demo setting is left enabled. Backup files
are retained under `/tmp/tidyup-live-check-*` and the private runtime demo directories.

The bundle's security checker reports no findings and identifies reviewable process
and privilege capabilities. The actual privileged boundary is the distro's pacman
inside a visible sudo terminal, with its transaction confirmation; Python is never
elevated. This is documented, not represented as a security certification.
