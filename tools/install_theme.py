#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Per-user theme installer with dry-run and conservative, conflict-aware restore.

Never changes GTK/window styling, launches apps, or restarts Plank/the panel.
Only opt-in --map/--known-apps requests modify application icons; all other launcher
bytes are preserved. Development installs require --allow-draft until rights are cleared.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

ROOT=Path(__file__).resolve().parents[1]
SAFE=re.compile(r'[A-Za-z0-9._-]+')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def paths(home=None):
    base=(home or Path.home()).expanduser().resolve()
    # --home is for an isolated test, not an override of the active session.
    def xdg(variable, default):
        value=Path(os.environ.get(variable, default)) if home is None else default
        if not value.is_absolute():raise ValueError('XDG destinations must be absolute')
        return value.resolve()
    return base,xdg('XDG_DATA_HOME',base/'.local/share'),xdg('XDG_CONFIG_HOME',base/'.config'),xdg('XDG_STATE_HOME',base/'.local/state')


def icon_only(data, icon):
    text=data.decode('utf-8')
    lines=text.splitlines(keepends=True)
    section=None;start=None;found=False;end=None
    for index,line in enumerate(lines):
        stripped=line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            if section=='Desktop Entry' and end is None:end=index
            section=stripped[1:-1]
            if section=='Desktop Entry':
                if start is not None:raise ValueError('Duplicate Desktop Entry section')
                start=index
        elif section=='Desktop Entry':
            match=re.match(r'^(Icon(?:\[[^\]\r\n]+\])?\s*=\s*)([^\r\n]*)(\r?\n?)$',line)
            if match:
                lines[index]=match[1]+icon+match[3];found=True
    if start is None:raise ValueError('Missing Desktop Entry section')
    if not found:
        newline='\r\n' if '\r\n' in text else '\n'
        at=end if end is not None else len(lines)
        if at and not lines[at-1].endswith(('\n','\r')):lines[at-1]+=newline
        lines.insert(at,'Icon='+icon+newline)
    return ''.join(lines).encode('utf-8')


def atomic(path,data,mode=0o644):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.monochrome-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.chmod(temp,mode)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def setting(value=None):
    command=['xfconf-query','-c','xsettings','-p','/Net/IconThemeName']
    if value is None:return subprocess.check_output(command,text=True).strip()
    subprocess.run(command+['-s',value],check=True)


def install(args):
    catalog=json.loads((ROOT/'assets.json').read_text())
    package=json.loads((ROOT/'theme-files.json').read_text())
    if catalog['release_status']!='ready' and not args.allow_draft:
        raise ValueError('This is an unreleased draft; only local testing with --allow-draft is permitted.')
    if args.activate and args.home is not None:
        raise ValueError('--activate is not allowed with an isolated --home')
    name=package['name']
    if not SAFE.fullmatch(name):raise ValueError('Invalid theme name')
    home,data,config,state=paths(args.home)
    theme=data/'icons'/name
    weather=config/'xfce4/weather/icons/monochrome'
    if theme.exists() or theme.is_symlink():raise ValueError('Theme already exists; restore the prior managed install before updating.')
    planned=[]
    for item in package['files']:
        source=ROOT/item['file']
        prefix='theme/'+name+'/'
        if not item['file'].startswith(prefix):raise ValueError('Invalid theme source')
        relative=Path(item['file'].removeprefix(prefix))
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe theme path')
        content=source.read_bytes()
        if source.is_symlink() or digest(content)!=item['sha256']:raise ValueError('Theme file changed: '+item['file'])
        planned.append((theme/relative,content))
    if args.weather:
        if weather.exists() or weather.is_symlink():raise ValueError('Weather theme already exists; refusing to overwrite it.')
        for bundle in catalog.get('bundles',[]):
            for item in bundle['files']:
                source=ROOT/item['file']
                if not item['file'].startswith('weather/'):raise ValueError('Invalid Weather source')
                relative=Path(item['file'].removeprefix('weather/'))
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe Weather path')
                content=source.read_bytes()
                if source.is_symlink() or digest(content)!=item['sha256']:raise ValueError('Weather file changed')
                planned.append((weather/relative,content))
    keys={a['key'] for a in catalog['assets'] if 'weather_assignment' not in a}
    directories=[data/'applications']+[p/'applications' for p in
        map(Path,os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')) if p.is_absolute()]
    seen=set()
    requests=list(args.map)
    explicit={r.partition('=')[0] for r in requests}
    if args.known_apps:
        for asset in catalog['assets']:
            for ident in asset.get('desktop_ids',[]):
                if ident not in explicit and any((p/ident).is_file() for p in directories):
                    requests.append(ident+'='+asset['key'])
    for request in requests:
        ident,separator,key=request.partition('=')
        if not separator or not SAFE.fullmatch(ident) or not ident.endswith('.desktop') or key not in keys:
            raise ValueError('Mappings must be an existing app.desktop=asset-key')
        if ident in seen:raise ValueError('Duplicate launcher mapping')
        seen.add(ident)
        source=next((p/ident for p in directories if (p/ident).is_file()),None)
        if source is None:raise ValueError('Launcher not found: '+ident)
        planned.append((data/'applications'/ident,icon_only(source.read_bytes(),'monochrome-'+key)))
    if args.menu:
        menu_directories=[data/'desktop-directories']+[p/'desktop-directories' for p in
            map(Path,os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')) if p.is_absolute()]
        for asset in catalog['assets']:
            assignment=asset.get('menu_assignment',{})
            if assignment.get('type')!='menu-directory':continue
            ident=assignment['directory']
            if not SAFE.fullmatch(ident) or not ident.endswith('.directory'):raise ValueError('Invalid menu directory name')
            source=next((p/ident for p in menu_directories if (p/ident).is_file()),None)
            if source is not None:
                planned.append((data/'desktop-directories'/ident,icon_only(source.read_bytes(),'monochrome-'+asset['key'])))
    for target,content in planned:
        permitted=data if target.is_relative_to(data) else config
        if not target.resolve().is_relative_to(permitted) or target.is_symlink():
            raise ValueError('Destination resolves outside the selected XDG root')
    previous=setting() if args.activate else None
    print(json.dumps({'theme':name,'theme_files':len(package['files']),
                      'weather':args.weather,'launcher_mappings':len(requests),'menu':args.menu,
                      'activate':args.activate,'dry_run':args.dry_run}))
    if args.dry_run:return
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    backup=state/'monochrome-icons/backups'/identifier
    backup.mkdir(parents=True,mode=0o700)
    manifest={'theme':name,'previous_theme':previous,'active_theme':name if args.activate else None,
              'files':[],'created_directories':[]}
    # Record backups before touching any target. The manifest is private user state.
    for index,(target,content) in enumerate(planned):
        existed=target.exists()
        record={'target':str(target),'installed_sha256':digest(content),'existed':existed}
        if existed:
            original=target.read_bytes();saved=backup/'files'/str(index)
            saved.parent.mkdir(exist_ok=True);shutil.copy2(target,saved)
            record.update(backup_file='files/'+str(index),original_sha256=digest(original),mode=target.stat().st_mode&0o777)
        parent=target.parent
        while not parent.exists():
            if str(parent) not in manifest['created_directories']:manifest['created_directories'].append(str(parent))
            parent=parent.parent
        manifest['files'].append(record)
    atomic(backup/'manifest.json',json.dumps(manifest,indent=2).encode(),0o600)
    for (target,content),record in zip(planned,manifest['files']):
        atomic(target,content,record.get('mode',0o644))
    if args.activate:setting(name)
    print('Installed. Restore manifest: '+str(backup/'manifest.json'))
    if args.weather:print('Weather: select Monochrome Weather in its Preferences > Appearance; no forecast setting was changed.')


def restore(args):
    path=args.manifest.expanduser().resolve()
    manifest=json.loads(path.read_text())
    home,data,config,state=paths(args.home)
    if not path.is_relative_to(state/'monochrome-icons/backups'):
        raise ValueError('Manifest is outside the selected user state directory')
    if manifest.get('active_theme') and args.home is not None:raise ValueError('Cannot restore a live activation into an isolated home')
    for item in manifest['files']:
        target=Path(item['target'])
        if not (target.resolve().is_relative_to(data) or target.resolve().is_relative_to(config)) or target.is_symlink():
            raise ValueError('Restore target is outside the selected XDG roots')
        if not target.is_file() or digest(target.read_bytes())!=item['installed_sha256']:
            raise ValueError('File changed since installation; restore stopped: '+str(target))
        if item['existed']:
            saved=path.parent/item['backup_file']
            if saved.is_symlink() or not saved.resolve().is_relative_to(path.parent) or digest(saved.read_bytes())!=item['original_sha256']:
                raise ValueError('Backup is missing or changed')
    if manifest.get('active_theme') and setting()!=manifest['active_theme']:
        raise ValueError('Icon theme changed since installation; restore stopped.')
    print(f"Restore {len(manifest['files'])} managed files; dry-run={args.dry_run}")
    if args.dry_run:return
    if manifest.get('active_theme'):setting(manifest['previous_theme'])
    for item in manifest['files']:
        target=Path(item['target'])
        if item['existed']:atomic(target,(path.parent/item['backup_file']).read_bytes(),item['mode'])
        else:target.unlink()
    for name in sorted(manifest['created_directories'],key=lambda p:len(Path(p).parts),reverse=True):
        directory=Path(name)
        if not (directory.resolve().is_relative_to(data) or directory.resolve().is_relative_to(config)):
            continue
        try:directory.rmdir()
        except OSError:pass  # User-added files are preserved, never recursively removed.
    atomic(path.parent/'restored.json',json.dumps({'restored':True}).encode(),0o600)
    print('Restored. Backups retained in '+str(path.parent))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    first=commands.add_parser('install')
    first.add_argument('--home',type=Path,help='Isolated test home; disables live activation')
    first.add_argument('--allow-draft',action='store_true')
    first.add_argument('--dry-run',action='store_true')
    first.add_argument('--activate',action='store_true',help='Change only Xfce icon theme')
    first.add_argument('--weather',action='store_true',help='Install optional Weather PNG companion')
    first.add_argument('--known-apps',action='store_true',help='Map installed apps with cataloged portable desktop IDs; excludes dynamic calendars and profile-specific web apps')
    first.add_argument('--menu',action='store_true',help='Map matching installed menu category files, preserving their other fields')
    first.add_argument('--map',action='append',default=[],metavar='APP.desktop=ASSET')
    second=commands.add_parser('restore')
    second.add_argument('manifest',type=Path)
    second.add_argument('--home',type=Path)
    second.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    try:
        (install if args.command=='install' else restore)(args)
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        parser.exit(1,'Error: '+str(error)+'\n')
