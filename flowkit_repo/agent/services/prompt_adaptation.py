"""Versioned, lossless Seko -> Omni rules. Unsupported intent stops explicitly.

v1 covers timed, locked-camera, silent reaction shots only. It is not a freeform
script translator. Source action text remains byte-for-byte in the compiled prompt.
"""
import hashlib
import json
from pathlib import Path
import re
import uuid

PROFILE = 'seko-omni-first-frame-silent-v1'
EXPERIMENTAL_PROFILE = 'seko-omni-first-frame-silent-v2'
PREFIX = ('One continuous 8-second shot with no cuts. Use the supplied image as '
          'the first frame. Maintain its framing with a locked camera throughout.\n')
CLOSED_LIPS = ('Keep the lips gently closed during every segment while performing the requested actions. '
               'Do not articulate words or add speaking mouth movements.')
TIMING = re.compile(r'(?<!\d)(\d+)-(\d+)s:')
SPEECH = re.compile(r'\b(?:says?|asks?|replies|whispers?|shouts?|speaks?|sings?)\b|[“”「」]|说[：:]|问[：:]', re.I)
CONFLICT = re.compile(r'\b(?:cuts?|cutaway|montage|pan|pans|zoom|zooms|dolly|handheld|orbit|tracking)\b|切镜|转场|推镜|拉镜|运镜', re.I)


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def record_omni_request(output_dir, request_id, payload):
    """Persist the actual provider arguments before submission, without session data.

    A receipt proves the prepared payload, not remote success. Existing operation
    IDs are re-polled by the provider before this function is reached.
    """
    path = Path(output_dir) / 'prompt-audit' / (digest(request_id) + '.json')
    record = {'stage': 'prepared', 'request_id': request_id, 'payload': payload,
              'prompt_sha256': digest(payload['prompt'])}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != record:
            raise ValueError('Prepared Omni request changed; inspect before submission')
        return
    with path.open('x') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def finalize_omni_prompt(prompt, project):
    """Shared final-text builder; no Veo negative list or guessed voice identity."""
    if not project or project.get('video_model_family') != 'omni_flash':
        raise ValueError('Explicit Omni project required for prompt finalization')
    if not project.get('allow_voice') and SPEECH.search(prompt):
        raise ValueError('Prompt speech conflicts with project allow_voice=false')
    parts = [prompt.strip()]
    if not project.get('allow_music'):
        parts.append('Do not add background music.')
    if not project.get('allow_voice'):
        parts.append('Use only natural ambient sound; no speech, narration or voiceover.')
    return '\n'.join(parts)


def compile_seko_omni(native, project, reference_media_id, *, profile=PROFILE):
    if profile not in (PROFILE, EXPERIMENTAL_PROFILE):
        raise ValueError('Unknown prompt profile; no generation submitted')
    if (native.get('selectedVideoDuration') != 8 or native.get('visionRatioId') != 1
            or native.get('resolutionType') != 1 or native.get('lastFrameNodeId')
            or native.get('refNodeIds') or not native.get('firstFrameNodeId')):
        raise ValueError('Prompt profile requires eight-second 720p landscape first-frame input')
    source = native.get('videoPrompt', '')
    if not source or source != native.get('processedPrompt'):
        raise ValueError('Original and processed Seko prompt must match')
    if source.startswith('One continuous 8-second shot with no cuts.'):
        raise ValueError('Prompt is already adapted; supply the original Seko prompt')
    if (project.get('video_model_family') != 'omni_flash' or
            project.get('allow_voice') or project.get('allow_music')):
        raise ValueError('Silent-shot profile requires Omni with voice/music disabled')
    reference_media_id = str(uuid.UUID(reference_media_id))
    timings = list(TIMING.finditer(source))
    if [(m.group(1), m.group(2)) for m in timings] != [('0', '3'), ('3', '6'), ('6', '8')]:
        raise ValueError('Unverified timing: this profile requires 0-3s, 3-6s, 6-8s')
    if timings[0].start() != 0 or any(not source[m.end():timings[i+1].start() if i < 2 else len(source)].strip()
                                     for i, m in enumerate(timings)):
        raise ValueError('Each timing segment requires explicit action text')
    if not re.search(r'\blocked camera\b', source, re.I):
        raise ValueError('Unverified camera intent: explicit locked camera required')
    if not re.search(r'\bno (?:talking|speech|dialogue)\b', source, re.I):
        raise ValueError('Unverified audio intent: explicit no talking/speech/dialogue required')
    if not re.search(r'\bno music\b', source, re.I):
        raise ValueError('Unverified audio intent: explicit no music required')
    if profile == EXPERIMENTAL_PROFILE and not re.search(r'\b(?:lips closed|closed lips)\b', source, re.I):
        raise ValueError('Closed-lips profile requires an explicit source closed-lips instruction')
    if SPEECH.search(source) or '"' in source or CONFLICT.search(source):
        raise ValueError('Dialogue, quoted text or camera/cut instructions need a different verified profile')
    prefix = PREFIX if profile == PROFILE else PREFIX.rstrip() + ' ' + CLOSED_LIPS + '\n'
    prompt = prefix + source
    changes = ['Make continuous-shot intent explicit for Omni',
               'Bind framing and camera to the supplied first frame',
               'Preserve every source character and action in original order']
    if profile == EXPERIMENTAL_PROFILE:
        changes.append('Experimental closed-lips constraint; did not reliably prevent mouth opening in the live test')
    return {'profile': profile, 'source_platform': 'seko',
            'source_model': native.get('videoModel'), 'source_prompt': source,
            'source_sha256': digest(source), 'flow_prompt': prompt,
            'final_prompt': finalize_omni_prompt(prompt, project),
            'target_family': 'omni_flash', 'mode': 'first_frame', 'duration_s': 8,
            'resolution': '720p', 'aspect': '16:9',
            'reference_media_ids': [reference_media_id],
            'changes': changes,
            'limitations': ['Silent timed locked-camera shots only; no arbitrary Skill translation',
                            'No voice reference binding; no claim of quality improvement']}
