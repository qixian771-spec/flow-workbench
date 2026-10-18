#!/usr/bin/env python3
"""Audit Seko snapshots without inventing timeline volume or source-cache fields."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from platform_probe import check, index_unique, inspect_media, audit_blue_marker, sha256


def media_identity(uri):
    if not uri:
        raise ValueError('Missing media URI')
    u = urlsplit(uri)
    if u.scheme == 'media':
        return uri
    if u.scheme != 'https':
        raise ValueError('Expected HTTPS media')
    # Signed query parameters rotate; the object path identifies the bytes.
    return u.netloc + u.path


def audit(before, after):
    a, b = before['node']['node'], after['node']['node']
    old, new = media_identity(a['genFileUrl']), media_identity(b['genFileUrl'])
    first, last = index_unique(before['shots']), index_unique(after['shots'])
    if not first:
        raise ValueError('Empty baseline')
    affected = [s['id'] for s in first.values() if media_identity(s['shotVideoUrl']) == old]
    if not affected:
        raise ValueError('No baseline shot references target media')
    checks = []
    check(checks, 'same_node_new_media', a['id'] == b['id'] and old != new)
    check(checks, 'completed_node', b['genStatus'] == 'GENERATING_COMPLETED')
    check(checks, 'same_shot_ids', first.keys() == last.keys())
    fields = ('seq', 'seqValue', 'duration', 'shotVideoStartTime', 'shotVideoEndTime',
              'bindAudioSync', 'linesAudioEnabledFlag', 'shotVideoType')
    check(checks, 'shot_timing_and_audio_flags_preserved', all(
        sid in last and all(s[k] == last[sid][k] for k in fields)
        for sid, s in first.items()))
    check(checks, 'all_affected_shots_updated', all(
        sid in last and media_identity(last[sid]['shotVideoUrl']) == new for sid in affected))
    check(checks, 'no_stale_shot_media', all(
        media_identity(s['shotVideoUrl']) != old for s in last.values()))
    check(checks, 'unrelated_shots_preserved', all(
        sid in last and media_identity(s['shotVideoUrl']) == media_identity(last[sid]['shotVideoUrl'])
        for sid, s in first.items() if sid not in affected))
    check(checks, 'completed_shots', all(
        s['genVideoStatus'] == 'GENERATING_COMPLETED' for s in last.values()))
    return checks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', required=True)
    p.add_argument('--after', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--export', dest='video')
    p.add_argument('--blue-at', nargs='+', type=float)
    args = p.parse_args()
    checks = audit(json.loads(Path(args.before).read_text()), json.loads(Path(args.after).read_text()))
    if args.video:
        checks += inspect_media(args.video, 16, (1280, 720))
        if args.blue_at:
            checks += audit_blue_marker(args.video, args.blue_at)
    result = {'passed': all(c['passed'] for c in checks), 'checks': checks,
              'limits': ['No independent source-reference cache exposed in these snapshots',
                         'Audio flags are not a volume, voice or lip-sync verification']}
    if args.video:
        result['export_sha256'] = sha256(args.video)
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(checks)}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
