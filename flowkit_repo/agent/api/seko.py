"""Persistent, explicitly configured Seko -> Flow jobs. No Seko credentials leave Chrome."""
import asyncio
import base64
import hashlib
import json
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from agent.config import BASE_DIR
from agent.services import seko_local_workflow as local_workflow
from agent.services import seko_local_video as local_video
from agent.services import seko_local_assembly as local_assembly
from agent.services import seko_local_multishot as local_multishot

ROOT = BASE_DIR / 'output' / 'seko-resident'
CONFIG = ROOT / 'config.json'
LOCK = asyncio.Lock()


async def authorize(request: Request):
    expected = getattr(request.app.state, 'seko_bridge_secret', '')
    if not expected or not secrets.compare_digest(request.headers.get('x-flowkit-seko', ''), expected):
        raise HTTPException(403, 'Existing Flow Kit extension connection required')


router = APIRouter(prefix='/seko', tags=['seko'], dependencies=[Depends(authorize)])


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def job_dir(job_id):
    if str(uuid.UUID(job_id)) != job_id:
        raise ValueError('Canonical UUID required')
    return ROOT / 'jobs' / job_id


def config():
    if not CONFIG.exists():
        return {'enabled': False, 'projects': []}
    return read(CONFIG)


def validate(body, cfg):
    native = body['nativeRequest']
    matches = [p for p in cfg['projects'] if p['canvasId'] == native['canvasId']]
    if not cfg['enabled'] or len(matches) != 1:
        raise ValueError('Canvas not explicitly enabled')
    project = matches[0]
    reference = project['references'].get(native['firstFrameNodeId'])
    if not reference:
        raise ValueError('Reference is not mapped to Flow')
    if (native.get('lastFrameNodeId') or native.get('refNodeIds') or
        native.get('selectedVideoDuration') != 8 or native.get('visionRatioId') != 1 or
        native.get('resolutionType') != 1 or not native.get('videoPrompt', '').strip() or
        native.get('processedPrompt') != native['videoPrompt']):
        raise ValueError('Only explicit eight-second 720p horizontal first-frame requests supported')
    return project, reference


def invoke(command, *args):
    result = subprocess.run([sys.executable, str(BASE_DIR / 'scripts' / 'seko_flow_job.py'),
                             command, *map(str, args)], capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(result.stderr.strip()[-1200:] or 'Flow job failed')
    return json.loads(result.stdout)


@router.get('/config')
async def get_config():
    return config()


@router.post('/jobs')
async def create_job(body: dict):
    async with LOCK:
        try:
            if body.get('workflow') == local_workflow.WORKFLOW:
                return await asyncio.to_thread(local_workflow.create, body)
            project, ref = validate(body, config())
            directory = job_dir(body['jobId'])
            digest = hashlib.sha256(json.dumps(body['nativeRequest'], sort_keys=True).encode()).hexdigest()
            state_path = directory / 'state.json'
            if state_path.exists():
                state = read(state_path)
                if state['inputHash'] != digest:
                    raise ValueError('Job ID already belongs to another request')
                return state
            # A double click may carry a new page UUID; do not charge twice for
            # the same in-flight native input, including across browser refreshes.
            for existing_path in (ROOT / 'jobs').glob('*/state.json'):
                existing = read(existing_path)
                if (existing['inputHash'] == digest and existing['canvasId'] == project['canvasId']
                    and existing['phase'] in ('submitting', 'submitted', 'ready', 'uploading', 'uploaded', 'creating-node')):
                    return existing
            directory.mkdir(parents=True, exist_ok=False)
            state = {'jobId': body['jobId'], 'canvasId': project['canvasId'],
                     'storyId': project['storyId'], 'phase': 'submitting', 'inputHash': digest,
                     'nativeRequest': body['nativeRequest'], 'history': ['submitting']}
            write(state_path, state)
            capture = {'canvasId': project['canvasId'], 'referenceNodeId': body['nativeRequest']['firstFrameNodeId'],
                       'jobs': [{'jobId': body['jobId'], 'state': 'captured', 'actualProvider': 'flow',
                                 'actualModelFamily': 'omni_flash', 'nativeRoute': 'seko-canvas/v1/canvas-node/gen-video',
                                 'nativeRequest': body['nativeRequest']}]}
            write(directory / 'capture.json', capture)
            try:
                result = await asyncio.to_thread(invoke, 'submit', '--capture', directory / 'capture.json',
                    '--job-id', body['jobId'], '--flow-project', project['flowProject'],
                    '--reference-scene', ref['sceneId'], '--state', directory / 'flow.json')
                state.update(phase='submitted', flow=result)
                state['history'].append('submitted')
            except Exception as error:
                state.update(phase='failed', error=str(error))
            write(state_path, state)
            return state
        except (ValueError, KeyError, OSError) as error:
            raise HTTPException(400, str(error))


@router.get('/jobs')
async def list_jobs(canvasId: str):
    return [read(p) for p in sorted((ROOT / 'jobs').glob('*/state.json'))
            if read(p)['canvasId'] == canvasId] + local_workflow.list_jobs(canvasId)


@router.post('/jobs/{job_id}/collect')
async def collect_job(job_id: str, body: dict | None = None):
    async with LOCK:
        if local_workflow.exists(job_id):
            if body == {'stepId':local_multishot.STEP}:
                return await asyncio.to_thread(local_multishot.collect,job_id)
            if body in ({'stepId':local_assembly.STEP}, {'stepId':local_assembly.STEP,'recheckCompletedRender':True}):
                return await asyncio.to_thread(local_assembly.collect,job_id,bool(body.get('recheckCompletedRender')))
            if body == {'stepId': local_video.STEP}:
                return await asyncio.to_thread(local_video.collect, job_id)
            if body == {'recheckCompletedMedia': True}:
                try:
                    await asyncio.to_thread(local_workflow.recheck_completed_media, job_id)
                except ValueError as error:
                    raise HTTPException(409, str(error))
            return await asyncio.to_thread(local_workflow.collect, job_id)
        directory = job_dir(job_id)
        state = read(directory / 'state.json')
        if state['phase'] != 'submitted':
            return state
        try:
            result = await asyncio.to_thread(invoke, 'collect', '--state', directory / 'flow.json')
            if result['phase'] == 'downloaded':
                state.update(phase='ready', sha256=result['media_sha256'], mediaId=result['media_id'],
                             size=(directory / 'flow.mp4').stat().st_size)
                state['history'].append('ready')
                write(directory / 'state.json', state)
        except Exception as error:
            state.update(phase='failed', error=str(error))
            write(directory / 'state.json', state)
        return state


@router.get('/jobs/{job_id}/media')
async def media(job_id: str, offset: int = 0, kind: str = "image"):
    if local_workflow.exists(job_id):
        try:
            if kind == "multishot":
                return local_multishot.media(job_id, offset)
            if kind == "video":
                return local_video.media(job_id, offset)
            if kind != "image":
                raise ValueError("Unsupported media kind")
            return local_workflow.media(job_id, offset)
        except ValueError as error:
            raise HTTPException(409, str(error))
    directory = job_dir(job_id)
    state = read(directory / 'state.json')
    if state['phase'] not in ('ready', 'uploading', 'uploaded', 'creating-node', 'complete') or offset < 0:
        raise HTTPException(409, 'Media is not ready')
    with (directory / 'flow.mp4').open('rb') as f:
        f.seek(offset)
        chunk = f.read(65536)
    return {'offset': offset, 'base64': base64.b64encode(chunk).decode(), 'length': len(chunk)}


def transition(state, body):
    if body.get('expectedPhase') != state['phase']:
        raise ValueError('Concurrent state change')
    allowed = {'submitted': {'needs-inspection'}, 'ready': {'uploading'}, 'uploading': {'uploaded', 'failed'},
               'uploaded': {'creating-node', 'failed'}, 'creating-node': {'complete', 'failed'}}
    if body.get('phase') not in allowed.get(state['phase'], set()):
        raise ValueError('Invalid checkpoint transition')
    for field in ('upload', 'receipt', 'error'):
        if field in body:
            state[field] = body[field]
    state['phase'] = body['phase']
    state['history'].append(body['phase'])
    return state


@router.post('/jobs/{job_id}/checkpoint')
async def checkpoint(job_id: str, body: dict):
    async with LOCK:
        if local_workflow.exists(job_id):
            try:
                if body.get("stepId") == local_multishot.STEP:
                    return await asyncio.to_thread(local_multishot.checkpoint, job_id, body)
                if body.get("stepId") == local_assembly.STEP:
                    return await asyncio.to_thread(local_assembly.checkpoint, job_id, body)
                if body.get("stepId") == local_video.STEP:
                    return await asyncio.to_thread(local_video.checkpoint, job_id, body)
                return await asyncio.to_thread(local_workflow.checkpoint, job_id, body)
            except ValueError as error:
                raise HTTPException(409, str(error))
        path = job_dir(job_id) / 'state.json'
        try:
            state = transition(read(path), body)
            write(path, state)
            return state
        except ValueError as error:
            raise HTTPException(409, str(error))
