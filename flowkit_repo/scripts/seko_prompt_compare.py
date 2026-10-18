#!/usr/bin/env python3
"""Durable A/B of one captured Seko input; exactly one two-request batch.

The baseline bypass is only available here, never on the resident generation path.
Unknown mutation outcomes leave the journal intact and cannot be auto-resubmitted.
"""
import argparse
import fcntl
import json
from pathlib import Path
import sys

from seko_flow_job import BASE, api, prepare, save, collect
from agent.services.prompt_adaptation import finalize_omni_prompt


def submit_comparison(args, path):
    job, project, ref, media_id, adaptation = prepare(args)
    state = {'phase': 'reserved', 'source': job, 'adaptation': adaptation,
             'flow_project': args.flow_project, 'reference_media_id': media_id,
             'variants': {}, 'generation_count': 2}
    with path.open('x') as f:
        json.dump(state, f, ensure_ascii=False)
    state['phase'] = 'creating_video'; save(path, state)
    video = api(BASE, '/api/videos', {'project_id': args.flow_project,
        'title': 'Seko prompt A-B: same first frame', 'orientation': 'HORIZONTAL', 'target_duration_s': 16})
    state['video_id'] = video['id']; save(path, state)
    batch = []
    for label, prompt in [('original', adaptation['source_prompt']), ('adapted', adaptation['flow_prompt'])]:
        state['phase'] = 'creating_' + label; save(path, state)
        scene = api(BASE, '/api/scenes', {'video_id': video['id'], 'prompt': adaptation['source_prompt'],
            'video_prompt': prompt, 'character_names': [], 'display_order': len(batch)})
        variant = {'phase': 'binding_reference', 'scene_id': scene['id'], 'video_id': video['id'],
                   'prompt': prompt, 'expected_final_prompt': finalize_omni_prompt(prompt, project),
                   'reference_media_id': media_id}
        state['variants'][label] = variant; save(path, state)
        api(BASE, '/api/scenes/' + scene['id'], {'horizontal_image_media_id': media_id,
            'horizontal_image_url': ref['horizontal_image_url'], 'horizontal_image_status': 'COMPLETED',
            'duration': 8}, method='PATCH')
        batch.append({'type': 'GENERATE_VIDEO', 'provider': 'flow', 'orientation': 'HORIZONTAL',
                      'project_id': args.flow_project, 'video_id': video['id'], 'scene_id': scene['id']})
    state['phase'] = 'submitting'; save(path, state)
    receipts = api(BASE, '/api/requests/batch', {'requests': batch})
    by_scene = {r['scene_id']: r for r in receipts}
    if len(receipts) != 2 or set(by_scene) != {v['scene_id'] for v in state['variants'].values()}:
        raise ValueError('Unexpected A/B receipt; inspect stored scene IDs before any retry')
    for label, variant in state['variants'].items():
        variant.update(phase='submitted', request_id=by_scene[variant['scene_id']]['id'])
        save(path.with_name(label + '.json'), variant)
    state['phase'] = 'submitted'; save(path, state)
    return {'phase': state['phase'], 'video_id': video['id'],
            'requests': {k: v['request_id'] for k,v in state['variants'].items()}}


def collect_comparison(args, path):
    state = json.loads(path.read_text())
    if state['phase'] not in ('submitted', 'downloaded'):
        raise ValueError('Unknown comparison mutation; inspect journal instead of resubmitting')
    status = api(BASE, '/api/requests/batch-status?video_id=' + state['video_id'] + '&type=GENERATE_VIDEO')
    if not status['all_succeeded']:
        return {'phase': 'failed' if status['done'] else 'pending', 'batch': status}
    results = {label: collect(args, path.with_name(label + '.json')) for label in state['variants']}
    state.update(phase='downloaded', results=results); save(path, state)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('submit')
    for name in ('capture', 'job-id', 'flow-project', 'reference-scene', 'state'):
        create.add_argument('--' + name, required=True)
    sub.add_parser('collect').add_argument('--state', required=True)
    args = parser.parse_args(); path = Path(args.state).resolve()
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = submit_comparison(args, path) if args.command == 'submit' else collect_comparison(args, path)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
