<h1 align="center">Omarchy TidyUp</h1>

<p align="center">
  <a href="https://github.com/tcballard/omarchy-badges"><img src="https://raw.githubusercontent.com/tcballard/omarchy-badges/75975e5b5bf75e7ede3764bcd2950046f7abfe2c/badges/v1/omarchy-plugin.svg" alt="Built for Omarchy: Plugin" height="24"></a>
</p>

**See what an app leaves behind.**

TidyUp helps you review an app’s settings, cache and data before removing them. Browse native Arch applications, inspect matching folders, and move selected items into Recovery from a native Omarchy panel.

## Everyday use

Open the bin icon, choose an app and review its folders. Nothing starts selected. **Move to Recovery** lets you restore an item later; permanent deletion asks separately. Package uninstallation opens in a terminal for pacman’s confirmation.

## Install

Omarchy Quattro, Python 3.11+, pacman, sudo and Omarchy’s terminal launcher. [Tested host and requirements →](GUIDE.md#compatibility)

```bash
omarchy plugin add https://github.com/tcballard/omarchy-plugin-tidyup.git --enable
```

## Update and remove

Update:

```bash
omarchy plugin update io.github.tcballard.tidyup
```

Remove:

```bash
omarchy plugin remove io.github.tcballard.tidyup
```

## A few useful details

Close the app before cleaning. Selected folders can contain profiles and app-managed content. Recovery preserves files but does not free their disk space; review Recovery before removing TidyUp. [Workflow](GUIDE.md#workflow) · [Recovery](GUIDE.md#recovery-and-removal)

This version covers native package-owned desktop apps, not Flatpak, AppImage or webapps. [Verification](docs/VERIFICATION.md)

Inspired by Pearcleaner’s review-before-removal workflow; an independent Linux implementation.

[Usage and development guide](GUIDE.md) · [Report a bug](https://github.com/tcballard/omarchy-plugin-tidyup/issues)

[MIT licensed](LICENSE).

<!-- Preserve links to sections now in the guide. -->
<a id="compatibility"></a>
<a id="development"></a>
<a id="keyboard-navigation"></a>
<a id="local-development-installation"></a>
<a id="matching-and-limits"></a>
<a id="recovery-and-removal"></a>
<a id="workflow"></a>

[Looking for the previous detailed sections? Open the full guide →](GUIDE.md)
