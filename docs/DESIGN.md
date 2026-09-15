# Design: Omarchy TidyUp 0.1.0

## Accepted requirements

Pearcleaner-inspired app-file review for Omarchy, named **Omarchy TidyUp**.
A waste-paper-bin icon in the desktop bar opens the UI. Every action is reachable
by keyboard. Native Omarchy components and panel interaction rules are required.

## Standards and architecture

Bundle: `tcballard/build-omarchy-plugins` at
`26ee1e7fc57e4089daea57ff0c51e6a10659e401` (reconciled 2026-09-14).

- Permanent ID: `io.github.tcballard.tidyup`; author: tcballard.
- Kind: `bar-widget`, mapped to `BarWidget.qml`, owning a private `Panel.qml`.
  No separately positioned top-level panel, redundant panel kind, or second shell.
- `Ui.BarWidget` and `Ui.WidgetButton`: icon slot sizing, orientation, theme,
  tooltip, lifecycle `opened/open/close`, and bar popout coordination.
- `Ui.KeyboardPanel`: real anchor item and bar injected; native positioning,
  fitted dimensions, outside-click dismissal, focus release and panel switching.
- `Ui.PanelHero`, `Ui.PanelSeparator`, `Ui.PanelSectionHeader`, `Ui.Button`,
  `Ui.TextField`, `Ui.ConfirmDialog` and `Ui.PanelKeyCatcher`: host styling and
  keyboard dispatch. Compact single-list drill-down rather than a desktop-app
  sidebar inside a custom window. All dynamic text is plain text.
- UI state is per-widget. No background polling. Helpers run only after explicit
  open/action. Backend locking serializes mutations across monitor instances.
- Durable state: private recovery directory beneath XDG data. Receipt precedes
  each rename and survives restore/deletion for crash recovery and audit.

## Navigation

Up/Down and j/k move a visible cursor through controls/rows. Left/Right and h/l
navigate tabs or recovery actions. Enter/Space activate the highlighted control.
Tab/Shift+Tab switch adjacent bar panels, matching native popouts. `/` or Ctrl+F
focuses the app search; Escape leaves search or cancels confirmation before closing.
Ctrl+1/2/3 selects Apps/Leftovers/Recovery. Backspace returns from file review to
Apps. Delete/x requests deletion only on a selected Recovery row. All destructive
confirmation dialogs initially select Cancel. Pointer hover and keyboard share
one cursor state; scrolling keeps its row visible.

## Boundaries

- Commands: `/usr/bin/python3 -I`; `/usr/bin/pacman` for inventory;
  `/usr/bin/omarchy-launch-terminal`, `/usr/bin/sudo`, `/usr/bin/pacman -R` for
  a user-confirmed native package transaction. Only distro pacman is elevated.
- No credentials, network, downloads, install hooks or background service.
- Exact package/desktop-ID/known app folder matching with reasons. All candidates
  start unselected. Cleanup moves to Recovery; restore never overwrites. Permanent
  deletion is separate and confirmed. Mounted content and symlink roots are refused.
- Known failure states: unavailable package inventory, empty scan, partial scan,
  changed selection, cross-filesystem move, permission or lock failure, partial
  batch, corrupt receipt, restore conflict, and terminal-launch failure.
- Closing cancels view interest in reads. A committed helper may finish its local
  transaction; receipt-first rename makes interrupted work discoverable. No promise
  that a backend test proves live host behavior.

## Evidence and scope

Portable backend tests, bundle manifest/security validator, QML import validation,
native hosted open/repeated-open/hide/keyboard tests, deterministic fictional demo
and captured preview with reversible setup. Exact source and host versions belong
in VERIFICATION.md. Installation/removal are checked without cleaning real files.

Initial scope: native Arch/AUR desktop apps and known native leftovers. Flatpak,
AppImage, webapps, broad home scanning, services, development environments, package
caches and macOS-specific tools are deferred. Target repository supplied by the user: `tcballard/omarchy-plugin-tidyup`.
Marketplace submission remains a separate action.

The read-only IPC target `io.github.tcballard.tidyup status` reports bounded counts,
UI state and geometry for acceptance checks. It does not expose file paths or app
records. On multi-monitor setups the handler may report one widget instance; the
canonical shell summon/hide routes choose the focused monitor.
