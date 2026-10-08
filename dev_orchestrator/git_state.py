"""Observación de Git y contenido; nunca restaura, limpia, añade ni registra archivos."""
import hashlib
import os
from pathlib import Path
import subprocess
import time


def remaining(deadline):
    value=15 if deadline is None else min(15,deadline-time.monotonic())
    if value<=0: raise TimeoutError('phase_timeout during Git observation')
    return value


def git(root, *args, deadline=None):
    return subprocess.run(['git',*args],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          check=True,timeout=remaining(deadline)).stdout


def digest(path, deadline=None):
    if path.is_symlink(): return 'symlink:'+os.readlink(path)
    if not path.exists(): return 'missing'
    if not path.is_file(): return 'directory'
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            remaining(deadline); value.update(chunk)
    return value.hexdigest()


def snapshot(root, deadline=None):
    root=Path(root)
    raw=git(root,'status','--porcelain=v1','-z','--untracked-files=all',deadline=deadline).decode('utf-8','surrogateescape').split('\0')
    changes=[]; i=0
    while i<len(raw) and raw[i]:
        item=raw[i]; i+=1
        row=dict(status=item[:2],path=item[3:])
        if 'R' in item[:2] or 'C' in item[:2]:
            row['original_path']=raw[i]; i+=1
        changes.append(row)
    index={}
    for item in git(root,'ls-files','--stage','-z',deadline=deadline).decode('utf-8','surrogateescape').split('\0'):
        if item:
            value,name=item.split('\t',1)
            index.setdefault(name,[]).append(value)
    untracked=git(root,'ls-files','--others','--exclude-standard','-z',deadline=deadline).decode('utf-8','surrogateescape').split('\0')
    paths=set(index)|set(filter(None,untracked))
    return dict(commit=git(root,'rev-parse','HEAD',deadline=deadline).decode().strip(),dirty=bool(changes),
        changes=changes,untracked=sorted(filter(None,untracked)),
        files={p:dict(content=digest(root/p,deadline),index=index.get(p),
                      mode=(root/p).lstat().st_mode if (root/p).exists() or (root/p).is_symlink() else None) for p in sorted(paths)})


def matches(path, rules):
    # Directorios usan barra final; archivos se comparan exactamente.
    key=path.casefold()
    return any(key.startswith(r.casefold()) if r.endswith('/') else key==r.casefold() for r in rules)


def compare(before, after, phase):
    changed=sorted(p for p in before['files'].keys()|after['files'].keys()
                   if before['files'].get(p)!=after['files'].get(p))
    previous={r['path'] for r in before['changes']}|set(before['untracked'])
    touched=sorted(set(changed)&previous)
    violations=[p for p in changed if matches(p,phase['forbidden_paths']) or not matches(p,phase['allowed_paths'])]
    if before['commit']!=after['commit']: violations.append('git:HEAD changed')
    # El alcance permitido no autoriza sobrescribir trabajo previo de otra persona.
    violations.extend('preexisting:'+p for p in touched if p not in violations)
    return changed, sorted(set(violations)), touched
