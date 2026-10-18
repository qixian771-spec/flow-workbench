import asyncio
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from agent.services import toonflow_jobs as jobs
from agent.services import toonflow_video as video

router = APIRouter(prefix='/toonflow', tags=['toonflow'])


class ImageJob(BaseModel):
    model_config = ConfigDict(extra='forbid')
    job_id: UUID
    model: Literal['BELUGA']
    ratio: Literal['16:9']
    prompt: str = Field(min_length=1, max_length=100000)


@router.post('/jobs')
async def create(body: ImageJob):
    try:
        return await asyncio.to_thread(jobs.create, body.model_dump(mode='json'))
    except ValueError as error:
        raise HTTPException(400, str(error))


@router.get('/jobs/{job_id}')
async def get(job_id: UUID):
    try:
        state = await asyncio.to_thread(jobs.read, str(job_id))
        return await asyncio.to_thread(video.refresh if state['kind'] == 'video' else jobs.refresh, str(job_id))
    except FileNotFoundError:
        raise HTTPException(404, 'Task not found')
    except ValueError as error:
        raise HTTPException(409, str(error))


@router.get('/jobs/{job_id}/media')
async def media(job_id: UUID):
    state = await get(job_id)
    if state['phase'] != 'complete':
        raise HTTPException(409, 'Artifact not complete')
    return FileResponse(jobs.directory(str(job_id)) / ('video.mp4' if state['kind'] == 'video' else 'image.bin'), media_type=state['mimeType'],
                        headers={'X-Content-SHA256': state['sha256']})


class VideoJob(BaseModel):
    model_config = ConfigDict(extra='forbid')
    job_id: UUID
    model: Literal['abra_i2v_8s']
    ratio: Literal['16:9']
    duration: Literal[8]
    resolution: Literal['720p']
    source_image_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    prompt: str = Field(min_length=1, max_length=100000)


@router.post('/video-jobs')
async def create_video(body: VideoJob):
    try:
        return await asyncio.to_thread(video.create, body.model_dump(mode='json'))
    except ValueError as error:
        raise HTTPException(400, str(error))
