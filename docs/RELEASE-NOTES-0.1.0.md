# Omarchy TidyUp 0.1.0 — release draft

Initial native Omarchy app cleanup plugin, with a waste-paper-bin bar icon and
keyboard navigation throughout Apps, Leftovers, file review, and Recovery.

- Browse and search native Arch/AUR desktop apps.
- Review exact matches in XDG settings, cache, data, and state directories.
- Move selected files into recoverable storage; restore without overwriting, or
  permanently delete a selected recovery item after separate confirmation.
- Open package removal in a terminal for sudo authentication and pacman confirmation.
- Inspect explicitly known leftover app folders and their matching explanations.

Tested on Omarchy development commit
`4ee6d4eeea176b0bf4014ce8b82a148a9433efff`, one horizontal bar on a single display
at 1.25 scale. Requires Python 3.11+, the native Quickshell/Omarchy components,
pacman, sudo, the Omarchy terminal launcher, and Linux renameat2.

Flatpak, AppImage, webapps, services, development environments, and package cache
cleanup are outside this version. Recovery retains storage until explicit deletion
and survives plugin removal. Full package removal, vertical/multiple displays,
and the standard Git installation/update/removal lifecycle remain unverified.
See [verification](VERIFICATION.md) for the evidence and limitations.

This document prepares release notes; no tag, published release, or marketplace
approval is implied.
