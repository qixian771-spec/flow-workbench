#!/usr/bin/env python3
"""Compare native-render audio against the exact supplied dialogue waveforms.

Signal retention verifies delivery, not pronunciation or speaker identity. Run
with the already available NumPy runtime; no model or dependency installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np


def pcm(path):
    data = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1',
                           '-ar', '24000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(data, dtype='<f4').astype(np.float64)


def check(root):
    final = root / '等雨停-Seko原站对白成片.mp4'
    rendered = pcm(final)
    results = []
    for i in range(1, 5):
        path = root / f'dialogue-{i}-5s.wav'
        source = pcm(path)
        n = 1 << (len(rendered) + len(source) - 1).bit_length()
        correlations = np.fft.irfft(np.fft.rfft(rendered,n) * np.conj(np.fft.rfft(source,n)),n)
        # Alignment stays near the expected cut; search is never used to match another shot.
        low = max(0, int(((i-1)*5-.2)*24000))
        high = min(len(rendered)-len(source)+1, int(((i-1)*5+.2)*24000))
        at = low + int(np.argmax(correlations[low:high]))
        actual = rendered[at:at+len(source)]
        correlation = float(np.corrcoef(source, actual)[0,1])
        active = np.flatnonzero(np.abs(source) > .015)
        results.append({'shot':i,'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'alignedStartSeconds':at/24000,'correlation':round(correlation,6),
            'sourceSpeechAboveThresholdSeconds':[round(active[0]/24000,4),round(active[-1]/24000,4)],
            'signalRetained':correlation>.95})
    return {'nativeFinalSha256':hashlib.sha256(final.read_bytes()).hexdigest(),
            'renderAudioSeconds':len(rendered)/24000,'shots':results,
            'allSignalsRetained':all(x['signalRetained'] for x in results),
            'scope':'Waveform retention only; no ASR, human listening or phoneme-level lip assessment claimed.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    result=check(args.directory)
    (args.directory/'audio-retention-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
