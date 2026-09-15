#!/usr/bin/python3
"""Local-only app inventory and recoverable cleanup. No privileged Python code."""
import argparse
import configparser
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import subprocess
import time
import uuid
from contextlib import contextmanager

PACKAGE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9@._+\-]{0,127}\Z")
# Explicit associations supplement exact package / desktop ID matches. Never fuzzy-match.
KNOWN = {
    "firefox": {"packages": ["firefox", "firefox-developer-edition", "firefox-esr"], "names": ["mozilla", "firefox"]},
    "chromium": {"packages": ["chromium"], "names": ["chromium"]},
    "google-chrome": {"packages": ["google-chrome", "google-chrome-beta", "google-chrome-dev"], "names": ["google-chrome"]},
    "discord": {"packages": ["discord", "discord-canary", "discord-ptb"], "names": ["discord"]},
    "spotify": {"packages": ["spotify", "spotify-launcher"], "names": ["spotify"]},
    "obsidian": {"packages": ["obsidian"], "names": ["obsidian"]},
    "code": {"packages": ["code", "visual-studio-code-bin"], "names": ["Code"]},
    "vlc": {"packages": ["vlc"], "names": ["vlc"]},
    "gimp": {"packages": ["gimp"], "names": ["GIMP", "gimp"]},
    "libreoffice": {"packages": ["libreoffice-fresh", "libreoffice-still"], "names": ["libreoffice"]},
    "telegram": {"packages": ["telegram-desktop"], "names": ["telegram-desktop"]},
}
PROTECTED = {"omarchy", "omarchy-tidyup", "hypr", "systemd", "applications", "icons", "fonts", "Trash", "keyrings", "mime", "dbus", "dconf", "gtk-3.0", "gtk-4.0", "autostart"}
FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def command(argv, timeout=20, limit=2_000_000):
    """Bound both output streams during receipt; kill/reap on deadline or overflow."""
    env = dict(os.environ, LC_ALL="C", PATH="/usr/bin:/bin")
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as proc:
        buffers = [bytearray(), bytearray()]
        try:
            with selectors.DefaultSelector() as sel:
                for i, stream in enumerate((proc.stdout, proc.stderr)):
                    os.set_blocking(stream.fileno(), False)
                    sel.register(stream, selectors.EVENT_READ, i)
                deadline = time.monotonic() + timeout
                while sel.get_map():
                    if time.monotonic() >= deadline:
                        raise ValueError("Command timed out. Try again.")
                    for key, _ in sel.select(.1):
                        data = os.read(key.fd, 65536)
                        if not data:
                            sel.unregister(key.fileobj)
                            continue
                        buffers[key.data].extend(data)
                        if len(buffers[key.data]) > limit:
                            raise ValueError("Command output exceeded the supported limit.")
                proc.wait(timeout=max(.01, deadline - time.monotonic()))
        except BaseException:
            proc.kill()
            proc.wait()
            raise
    return proc.returncode, *(b.decode("utf-8", "replace") for b in buffers)


def basename(value):
    if not isinstance(value, str) or value in ("", ".", "..") or "/" in value or "\x00" in value or len(value) > 255:
        raise ValueError("Invalid file name.")
    return value


def mountpoints():
    with open("/proc/self/mountinfo", "rb") as stream:
        data = stream.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Mount table exceeds the supported limit.")
    result = []
    for line in data.decode("utf-8", "replace").splitlines():
        fields = line.split()
        if len(fields) > 4:
            result.append(Path(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])))
    return result


def contains_mount(path, mounts):
    return any(mount == path or path in mount.parents for mount in mounts)


@contextmanager
def directory(path, create=False, private=False):
    """Retain a directory descriptor after opening every component without following links."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("An absolute path without parent traversal is required.")
    fd = os.open("/", FLAGS)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        if private:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("Recovery directory must be owned by you with mode 0700.")
        yield fd
    finally:
        os.close(fd)


def fingerprint(info):
    # QML uses IEEE-754 numbers: nanosecond timestamps exceed its exact integer
    # range. Preserve identity across the JSON round trip as decimal strings.
    return [str(info.st_dev), str(info.st_ino), str(info.st_mtime_ns), str(info.st_ctime_ns)]


def rename_exclusive(srcfd, source, dstfd, dest):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.renameat2(srcfd, os.fsencode(source), dstfd, os.fsencode(dest), 1):
        code = ctypes.get_errno()
        if code == errno.EXDEV:
            raise ValueError("This file is on another filesystem; recovery cannot move it safely.")
        raise OSError(code, os.strerror(code))


def read_json(fd, name):
    handle = os.open(basename(name), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    with os.fdopen(handle, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 16384:
            raise ValueError("Invalid recovery receipt.")
        return json.loads(stream.read(16385))


def write_json(fd, name, data):
    handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    with os.fdopen(handle, "w") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.fsync(fd)


class TidyUp:
    def __init__(self, home=None):
        self.home = Path(home or Path.home())
        self.roots = {
            "Settings": Path(os.environ.get("XDG_CONFIG_HOME", self.home / ".config")) if home is None else self.home / ".config",
            "Cache": Path(os.environ.get("XDG_CACHE_HOME", self.home / ".cache")) if home is None else self.home / ".cache",
            "Data": Path(os.environ.get("XDG_DATA_HOME", self.home / ".local/share")) if home is None else self.home / ".local/share",
            "State": Path(os.environ.get("XDG_STATE_HOME", self.home / ".local/state")) if home is None else self.home / ".local/state",
        }
        self.recovery = self.roots["Data"] / "omarchy-tidyup/recovery"

    def packages(self):
        code, out, err = command(["/usr/bin/pacman", "-Qq"])
        if code:
            raise ValueError("Cannot read installed packages: " + err[:300])
        return {p for p in out.splitlines() if PACKAGE.fullmatch(p)}

    def catalogue(self):
        installed = self.packages()
        paths = sorted(Path("/usr/share/applications").glob("*.desktop"))[:1024]
        owners = {}
        if paths:
            _, output, _ = command(["/usr/bin/pacman", "-Qo", "--", *map(str, paths)])
            for line in output.splitlines():
                match = re.fullmatch(r"(.+) is owned by (\S+) \S+", line)
                if match:
                    owners[match[1]] = match[2]
        apps = {}
        for path in paths:
            package = owners.get(str(path))
            if package not in installed:
                continue
            try:
                if path.stat().st_size > 65536:
                    continue
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read_string(path.read_text(errors="replace"))
                entry = parser["Desktop Entry"]
                if entry.get("NoDisplay", "false") == "true" or entry.get("Hidden", "false") == "true":
                    continue
                name = entry.get("Name", package)[:120]
            except (OSError, configparser.Error, KeyError):
                continue
            app = apps.setdefault(package, {"id": package, "name": name, "desktopIds": []})
            if len(name) < len(app["name"]):
                app["name"] = name
            app["desktopIds"].append(path.stem)
        return {"apps": sorted(apps.values(), key=lambda a: a["name"].casefold()), "note": "Native Arch and AUR desktop apps. Flatpak, AppImage and webapps are not included."}

    def aliases(self, package, installed):
        if package == "leftovers":
            return {name: "Known app folder; related native packages are absent. Check for other installations."
                    for spec in KNOWN.values() if not set(spec["packages"]) & installed
                    for name in spec["names"]}
        if not PACKAGE.fullmatch(package) or package not in installed:
            raise ValueError("This package is no longer installed. Refresh the app list.")
        names = {package: "Exact package-name match; verify the contents before cleanup."}
        for app in self.catalogue()["apps"]:
            if app["id"] == package:
                for desktop_id in app["desktopIds"]:
                    names[desktop_id] = "Exact desktop-ID match; verify the contents before cleanup."
        for spec in KNOWN.values():
            if package in spec["packages"]:
                for name in spec["names"]:
                    names[name] = "Known app folder; may be shared with another edition of this app."
        for name in list(names):
            if name not in PROTECTED:
                names.setdefault(name + ".conf", "Exact app configuration filename; review before cleanup.")
                names.setdefault(name + "rc", "Exact app configuration filename; review before cleanup.")
        return names

    def measure(self, fd, name):
        """Bounded estimate; never descend through a symbolic link."""
        total, count, partial = 0, 0, False
        deadline = time.monotonic() + .2
        def visit(parentfd, child, depth=0):
            nonlocal total, count, partial
            count += 1
            if count > 4000 or time.monotonic() > deadline or depth > 40:
                partial = True
                return
            try:
                info = os.stat(child, dir_fd=parentfd, follow_symlinks=False)
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
                elif stat.S_ISDIR(info.st_mode):
                    sub = os.open(child, FLAGS, dir_fd=parentfd)
                    try:
                        with os.scandir(sub) as entries:
                            for entry in entries:
                                if count > 4000 or time.monotonic() > deadline:
                                    partial = True
                                    break
                                visit(sub, entry.name, depth + 1)
                    finally:
                        os.close(sub)
            except OSError:
                partial = True
        visit(fd, name)
        return total, partial

    def scan(self, package):
        names = self.aliases(package, self.packages())
        mounts = mountpoints()
        items, warnings = [], []
        for kind, path in self.roots.items():
            try:
                with directory(path) as fd:
                    for name, reason in names.items():
                        if name in PROTECTED:
                            continue
                        basename(name)
                        try:
                            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                        except FileNotFoundError:
                            continue
                        if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)) or info.st_uid != os.getuid():
                            warnings.append("Skipped symbolic link, special or differently owned file: " + str(path / name))
                            continue
                        if contains_mount(path / name, mounts):
                            warnings.append("Skipped mounted content: " + str(path / name))
                            continue
                        size, partial = self.measure(fd, name)
                        items.append({"id": kind + ":" + name, "name": name, "kind": kind, "path": str(path / name), "bytes": size,
                                      "partial": partial, "fingerprint": fingerprint(info), "reason": reason})
            except FileNotFoundError:
                pass
            except OSError:
                warnings.append("Cannot safely inspect " + str(path) + "; symlinked roots are unsupported.")
        return {"app": package, "items": items, "warnings": warnings}

    @contextmanager
    def locked_recovery(self):
        with directory(self.recovery, create=True, private=True) as fd:
            lock = os.open(".lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
            try:
                if not stat.S_ISREG(os.fstat(lock).st_mode):
                    raise ValueError("Invalid recovery lock.")
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield fd
            finally:
                os.close(lock)

    def clean(self, package, selection):
        if not isinstance(selection, list) or not 1 <= len(selection) <= 64:
            raise ValueError("Select between 1 and 64 items.")
        fresh = {item["id"]: item for item in self.scan(package)["items"]}
        chosen, seen = [], set()
        for request in selection:
            item = fresh.get(request.get("id"))
            if not item or item["fingerprint"] != request.get("fingerprint") or item["id"] in seen:
                raise ValueError("Selection changed since review. Scan again before cleaning.")
            seen.add(item["id"])
            chosen.append(item)
        moved, failures = [], []
        with self.locked_recovery() as dest:
            for item in chosen:
                try:
                    with directory(self.roots[item["kind"]]) as source:
                        current = os.stat(item["name"], dir_fd=source, follow_symlinks=False)
                        if fingerprint(current) != item["fingerprint"]:
                            raise ValueError("File changed since review.")
                        token = uuid.uuid4().hex
                        receipt = dict(item, token=token, app=package, date=time.strftime("%Y-%m-%d %H:%M"))
                        # Receipt first: a crash after rename still leaves a recoverable record.
                        write_json(dest, token + ".json", receipt)
                        rename_exclusive(source, item["name"], dest, token + ".data")
                        os.fsync(source)
                        os.fsync(dest)
                        moved.append(token)
                except (OSError, ValueError) as error:
                    failures.append(item["path"] + ": " + str(error))
        return {"moved": moved, "failures": failures, "message": str(len(moved)) + " item(s) moved to Recovery. Disk space is retained until you remove those files yourself."}

    def history(self):
        entries, warnings = [], []
        try:
            with directory(self.recovery, private=True) as fd:
                with os.scandir(fd) as files:
                    for count, file in enumerate(files):
                        if count >= 4096:
                            warnings.append("Recovery listing reached its limit.")
                            break
                        if not re.fullmatch(r"[0-9a-f]{32}\.json", file.name):
                            continue
                        try:
                            receipt = read_json(fd, file.name)
                            token = file.name[:-5]
                            info = os.stat(token + ".data", dir_fd=fd, follow_symlinks=False)
                            if fingerprint(info)[:2] != receipt["fingerprint"][:2]:
                                raise ValueError("Recovery file identity changed.")
                            receipt["token"] = token
                            entries.append(receipt)
                        except FileNotFoundError:
                            pass  # Failed move or already restored; receipt is audit history.
                        except (OSError, ValueError, KeyError, TypeError) as error:
                            warnings.append(file.name + ": " + str(error))
        except FileNotFoundError:
            pass
        return {"entries": sorted(entries, key=lambda e: e["date"], reverse=True)[:512], "warnings": warnings}

    def restore(self, token):
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise ValueError("Invalid recovery identifier.")
        with self.locked_recovery() as source:
            receipt = read_json(source, token + ".json")
            name = basename(receipt["name"])
            kind = receipt["kind"]
            if kind not in self.roots or name in PROTECTED or str(self.roots[kind] / name) != receipt["path"]:
                raise ValueError("Recovery location changed or is unsupported.")
            info = os.stat(token + ".data", dir_fd=source, follow_symlinks=False)
            if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)) or fingerprint(info)[:2] != receipt["fingerprint"][:2]:
                raise ValueError("Recovery file identity changed.")
            with directory(self.roots[kind]) as dest:
                try:
                    rename_exclusive(source, token + ".data", dest, name)
                except FileExistsError:
                    raise ValueError("A file already exists at the original path. It has not been overwritten.") from None
                os.fsync(source)
                os.fsync(dest)
        return {"message": "Restored " + receipt["path"]}

    def uninstall(self, package):
        if not PACKAGE.fullmatch(package) or package not in {a["id"] for a in self.catalogue()["apps"]}:
            raise ValueError("Choose an installed desktop app.")
        if package in {"omarchy", "pacman", "quickshell", "hyprland"}:
            raise ValueError("Core desktop packages cannot be removed with TidyUp.")
        # The terminal owns authentication and pacman's transaction confirmation.
        # No code from this checkout is elevated, and no confirmation is bypassed.
        proc = subprocess.Popen(["/usr/bin/omarchy-launch-terminal", "/usr/bin/sudo", "/usr/bin/pacman", "-R", "--", package],
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            code = proc.wait(timeout=3)
            if code:
                raise ValueError("Could not open the package removal terminal.")
        except subprocess.TimeoutExpired:
            pass  # Terminal lifetime is intentionally independent of this panel.
        return {"message": "Package removal opened in a terminal. Review and confirm there, then refresh Apps. Personal files are cleaned separately."}

    def purge(self, token):
        """Only delete a reviewed recovery object, never an arbitrary caller-supplied path."""
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise ValueError("Invalid recovery identifier.")
        with self.locked_recovery() as fd:
            receipt = read_json(fd, token + ".json")
            name = token + ".data"
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if fingerprint(info)[:2] != receipt["fingerprint"][:2]:
                raise ValueError("Recovery file identity changed.")
            if contains_mount(self.recovery / name, mountpoints()):
                raise ValueError("Recovery item contains mounted content; deletion refused.")
            if stat.S_ISDIR(info.st_mode):
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise ValueError("Safe directory deletion is unavailable on this platform.")
                shutil.rmtree(name, dir_fd=fd)
            elif stat.S_ISREG(info.st_mode):
                os.unlink(name, dir_fd=fd)
            else:
                raise ValueError("Recovery item is not a regular file or directory.")
            os.fsync(fd)
        return {"message": "Permanently deleted the selected recovery item. It can no longer be restored."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["catalogue", "scan", "clean", "history", "restore", "purge", "uninstall"])
    parser.add_argument("--app", default="")
    parser.add_argument("--selection", default="[]")
    parser.add_argument("--token", default="")
    args = parser.parse_args()
    try:
        tidy = TidyUp()
        if args.action in ("catalogue", "history"):
            result = getattr(tidy, args.action)()
        elif args.action in ("scan", "uninstall"):
            result = getattr(tidy, args.action)(args.app)
        elif args.action in ("restore", "purge"):
            result = getattr(tidy, args.action)(args.token)
        else:
            if len(args.selection) > 32768:
                raise ValueError("Selection is too large.")
            result = tidy.clean(args.app, json.loads(args.selection))
        print(json.dumps(dict(result, ok=True)))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)[:1000]}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
