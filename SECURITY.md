# Security reporting

TidyUp runs as your desktop user and can move or permanently delete explicitly
selected app data. Package uninstallation opens a separate terminal running the
system's sudo and pacman, which provide authentication and transaction confirmation.

Report suspected vulnerabilities through the repository's
[issue tracker](https://github.com/tcballard/omarchy-plugin-tidyup/issues).
Use a minimal reproduction with fictional files and include the full plugin SHA
and Omarchy version. Do not post personal paths, recovery receipts, credentials,
or sensitive file contents. This is a public reporting channel; private reporting
and a guaranteed response time are not currently offered.

The maintained development line is `main`, currently version 0.1.0. Automated
checks and marketplace baseline scans are limited evidence, not a security audit.
