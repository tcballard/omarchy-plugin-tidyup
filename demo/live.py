#!/usr/bin/python3
"""Reversible single-monitor UI exercise. Never runs cleanup or package removal."""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'io.github.tcballard.tidyup'
CONFIG = Path.home() / '.config/omarchy/shell.json'
LINK = Path.home() / '.config/omarchy/plugins' / PLUGIN
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', '/tmp'))
MARKER = RUNTIME / 'omarchy-tidyup-demo.json'
ENV = dict(os.environ)

def call(argv, check=True):
    result = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=15)
    if check and result.returncode:
        raise RuntimeError(' '.join(argv[:3]) + ': ' + result.stderr[:500] + result.stdout[:500])
    return result.stdout.strip()

def ipc(method, *args, target='shell'):
    return call(['/usr/bin/omarchy-shell', target, method, *args])

def state():
    return json.loads(ipc('status', target=PLUGIN))

def wait_for(predicate, label, seconds=12):
    deadline = time.monotonic() + seconds
    latest = None
    while time.monotonic() < deadline:
        try:
            latest = state()
            if predicate(latest):
                return latest
        except (ValueError, RuntimeError):
            pass
        time.sleep(.15)
    raise RuntimeError(label + ': ' + json.dumps(latest))

def write_config(config):
    fd, filename = tempfile.mkstemp(prefix='.tidyup-', dir=CONFIG.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(config, stream, indent=2)
            stream.write('\n')
        os.replace(filename, CONFIG)
    finally:
        if os.path.exists(filename): os.unlink(filename)

def without_tidy(config):
    result = copy.deepcopy(config)
    result['plugins'] = [e for e in result.get('plugins', []) if e.get('id') != PLUGIN]
    for section, entries in result.get('bar', {}).get('layout', {}).items():
        result['bar']['layout'][section] = [e for e in entries if e.get('id') != PLUGIN]
    return result

def restore_entries(current, original):
    result = without_tidy(current)
    for key in ['plugins']:
        for index, entry in enumerate(original.get(key, [])):
            if entry.get('id') == PLUGIN:
                result.setdefault(key, []).insert(min(index, len(result[key])), entry)
    for section, entries in original.get('bar', {}).get('layout', {}).items():
        for index, entry in enumerate(entries):
            if entry.get('id') == PLUGIN:
                dest = result.setdefault('bar', {}).setdefault('layout', {}).setdefault(section, [])
                dest.insert(min(index, len(dest)), entry)
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shell-path', required=True)
    parser.add_argument('--capture', default=str(ROOT / 'preview.png'))
    args = parser.parse_args()
    ENV['OMARCHY_PATH'] = args.shell_path
    ENV['OMARCHY_SHELL_IPC_TIMEOUT'] = '8s'
    for command in ['omarchy-shell', 'hyprctl', 'wtype', 'grim']:
        if not shutil.which(command): raise RuntimeError('Missing ' + command)
    if MARKER.exists(): raise RuntimeError('Stale demo marker; inspect ' + str(MARKER))
    if not CONFIG.is_file(): raise RuntimeError('Missing shell configuration')
    if LINK.exists() and (not LINK.is_symlink() or LINK.resolve() != ROOT):
        raise RuntimeError('Ambiguous plugin installation: ' + str(LINK))
    if 'omarchy-lock' in call(['/usr/bin/hyprctl', 'layers', '-j']): raise RuntimeError('Session is locked')
    monitors = json.loads(call(['/usr/bin/hyprctl', 'monitors', '-j']))
    if len(monitors) != 1 or monitors[0]['transform'] != 0:
        raise RuntimeError('This capture harness requires one unrotated monitor')
    monitor = monitors[0]
    workspace = monitor['activeWorkspace']['id']
    cursor = json.loads(call(['/usr/bin/hyprctl', 'cursorpos', '-j']))
    clients = json.loads(call(['/usr/bin/hyprctl', 'clients', '-j']))
    occupied = {c['workspace']['id'] for c in clients}
    demo_workspace = next(i for i in range(90, 100) if i not in occupied)
    backup = Path(tempfile.mkdtemp(prefix='tidyup-demo-', dir=RUNTIME))
    original = json.loads(CONFIG.read_text())
    shutil.copy2(CONFIG, backup / 'shell.json')
    link_existed = LINK.is_symlink()
    MARKER.write_text(json.dumps({'backup': str(backup), 'workspace': workspace, 'linkExisted': link_existed}))
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    evidence = []
    restored = False
    try:
        if not link_existed: LINK.symlink_to(ROOT, target_is_directory=True)
        config = without_tidy(original)
        config.setdefault('bar', {}).setdefault('layout', {}).setdefault('right', []).append({'id': PLUGIN, 'demoMode': True})
        write_config(config)
        call(['/usr/bin/hyprctl', 'eval', f'hl.dispatch(hl.dsp.focus({{ workspace = "{demo_workspace}" }}))'])
        wait_for(lambda s: s.get('revision') == 'native-3' and s.get('configuredDemo', False) and not s['opened'], 'widget loaded')
        previous_instance = state()['instanceId']
        time.sleep(.8)
        wait_for(lambda s: s.get('configuredDemo', False) and s['instanceId'] == previous_instance, 'stable widget')
        call(['/usr/bin/hyprctl', 'eval', 'hl.dispatch(hl.dsp.cursor.move({ x = 20, y = 850 }))'])
        if ipc('summon', PLUGIN) != 'ok': raise RuntimeError('Cannot summon demo')
        wait_for(lambda s: s['opened'] and s['demo'] and s['rows'] == 4 and s['keyFocused'], 'demo ready')
        evidence.append('native bar-widget summon and fixture identity')
        time.sleep(.2)
        print('Before keys: ' + json.dumps(state()), flush=True)
        call(['/usr/bin/hyprctl', 'eval', 'hl.dispatch(hl.dsp.cursor.move({ x = 20, y = 850 }))'])
        snap = state()
        call(['/usr/bin/grim', '-g', f"{round(snap['x'])},{round(snap['y'])} {round(snap['width'])}x{round(snap['height'])}", str(backup / 'overview.png')])
        def key(*keys):
            args = ['/usr/bin/wtype']
            for k in keys: args.extend(['-k', k])
            call(args)
            print('After ' + ','.join(keys) + ': ' + json.dumps(state()), flush=True)
        key('Down')
        wait_for(lambda s: s['target'] == 'search', 'search cursor')
        key('Return')
        wait_for(lambda s: s['searchFocused'], 'search focus')
        call(['/usr/bin/wtype', 'chrom'])
        wait_for(lambda s: s['rows'] == 1, 'search filters')
        key('Down', 'Return')
        wait_for(lambda s: s['reviewing'] and s['rows'] == 2, 'app opens')
        key('Down', 'space')
        wait_for(lambda s: s['selected'] == 1, 'keyboard selects folder')
        evidence.extend(['keyboard search and drill-down', 'keyboard file selection'])
        # Rows -> refresh -> uninstall -> cleanup. Confirmations default to Cancel.
        key('Down', 'Down', 'Down', 'Down', 'Return')
        wait_for(lambda s: s['confirmation'] == 'clean' and s['confirmIndex'] == 0, 'cancel-first cleanup')
        key('Right')
        wait_for(lambda s: s['confirmIndex'] == 1, 'confirmation arrow navigation')
        key('Escape')
        wait_for(lambda s: not s['confirmation'] and s['opened'], 'confirmation escape')
        evidence.append('cleanup confirmation: Cancel default, arrows, Escape')
        # Move cursor back to the selected row for the preview.
        key('Up', 'Up', 'Up', 'Up')
        # Save only the fictional popout, excluding the desktop and other windows.
        status = state()
        geometry = f"{monitor['x'] + round(status['x'])},{monitor['y'] + round(status['y'])} {round(status['width'])}x{round(status['height'])}"
        call(['/usr/bin/grim', '-g', geometry, str(backup / 'preview.png')])
        ipc('summon', PLUGIN)
        wait_for(lambda s: s['opened'] and s['reviewing'], 'repeated open retains view')
        # Recovery navigation and both confirmations use the production UI.
        call(['/usr/bin/wtype', '3'])
        wait_for(lambda s: s['tab'] == 'Recovery' and s['rows'] == 1, 'recovery tab')
        key('Down', 'Return')
        wait_for(lambda s: s['confirmation'] == 'restore' and s['confirmIndex'] == 0, 'restore confirmation')
        key('Escape', 'Right', 'Return')
        wait_for(lambda s: s['confirmation'] == 'purge' and s['confirmIndex'] == 0, 'delete confirmation')
        key('Escape')
        evidence.append('recovery keyboard restore/delete with Cancel-first confirmation')
        key('Escape')
        wait_for(lambda s: not s['opened'], 'escape closes')
        evidence.append('repeated open and Escape close')
        ipc('summon', PLUGIN)
        wait_for(lambda s: s['opened'] and s['rows'] == 4, 'reopen resets view')
        # Click outside card. Native KeyboardPanel owns dismissal.
        call(['/usr/bin/hyprctl', 'eval', 'hl.dispatch(hl.dsp.cursor.move({ x = 20, y = 850 }))'])
        call(['/usr/bin/hyprctl', 'eval', 'hl.dispatch(hl.dsp.send_key_state({ mods = "", key = "mouse:272", state = "down" }))'])
        call(['/usr/bin/hyprctl', 'eval', 'hl.dispatch(hl.dsp.send_key_state({ mods = "", key = "mouse:272", state = "up" }))'])
        wait_for(lambda s: not s['opened'], 'outside-click dismissal')
        evidence.append('outside-click dismissal')
        print(json.dumps({'checks': evidence, 'capture': args.capture}))
    finally:
        errors = []
        steps = [
            lambda: ipc('hide', PLUGIN),
            lambda: write_config(restore_entries(json.loads(CONFIG.read_text()), original)),
            lambda: LINK.unlink() if not link_existed and LINK.is_symlink() and LINK.resolve() == ROOT else None,
            lambda: call(['/usr/bin/hyprctl', 'eval', f'hl.dispatch(hl.dsp.focus({{ workspace = "{workspace}" }}))']),
            lambda: call(['/usr/bin/hyprctl', 'eval', f"hl.dispatch(hl.dsp.cursor.move({{ x = {cursor['x']}, y = {cursor['y']} }}))"]),
        ]
        for step in steps:
            try: step()
            except Exception as error: errors.append(str(error))
        if errors:
            print('Restoration requires attention. Backup: ' + str(backup) + '; ' + '; '.join(errors))
        else:
            MARKER.unlink()
            restored = True
            print('Restored shell configuration, workspace and cursor. Backup: ' + str(backup))

    if restored:
        shutil.copy2(backup / 'preview.png', args.capture)
        shutil.copy2(backup / 'overview.png', ROOT / 'demo-overview.png')
        (ROOT / 'docs/live-evidence.json').write_text(json.dumps({'checks': evidence, 'capture': str(args.capture), 'monitor': monitor['name'], 'source': 'working tree', 'restored': True}, indent=2) + '\n')

if __name__ == '__main__':
    main()
