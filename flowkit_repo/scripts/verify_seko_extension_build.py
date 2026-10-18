"""Compare observed Chrome script bytes and manifest with the intended build.

Read-only: this module never reloads, registers, or injects an extension.
Matching the public version string alone does not establish build identity.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ('seko_local_bundle.js', 'seko_page.js', 'seko_content.js')


def inspect_build(observed, extension_dir, expected_id):
    if not re.fullmatch(r'[a-p]{32}', expected_id):
        raise ValueError('Invalid expected extension identity')
    expected = json.loads((extension_dir / 'manifest.json').read_text())
    differences = []
    if observed.get('extension_id') != expected_id:
        differences.append({'field': 'extension_id', 'expected': expected_id,
                            'actual': observed.get('extension_id')})
    actual = observed.get('manifest', {})
    for field in sorted(set(expected) | set(actual)):
        if actual.get(field) != expected.get(field):
            differences.append({'field': 'manifest.' + field,
                                'expected': expected.get(field), 'actual': actual.get(field)})
    scripts = observed.get('scripts', {})
    for name in REQUIRED:
        record = scripts.get(name, {})
        expected_url = f'chrome-extension://{expected_id}/{name}'
        expected_hash = hashlib.sha256((extension_dir / name).read_bytes()).hexdigest()
        for field, value in [('url', expected_url), ('sha256', expected_hash)]:
            if record.get(field) != value:
                differences.append({'field': f'scripts.{name}.{field}',
                                    'expected': value, 'actual': record.get(field)})
    return {'matches': not differences, 'expected_version': expected.get('version'),
            'actual_version': actual.get('version'), 'differences': differences}


def require_build(observed, extension_dir, expected_id):
    result = inspect_build(observed, extension_dir, expected_id)
    if not result['matches']:
        raise ValueError('Loaded extension build mismatch: ' + ', '.join(
            item['field'] for item in result['differences']))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observed', type=Path, required=True)
    parser.add_argument('--extension-id', required=True)
    parser.add_argument('--extension-dir', type=Path, default=ROOT / 'extension')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = inspect_build(json.loads(args.observed.read_text()), args.extension_dir, args.extension_id)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Loaded build matches' if result['matches'] else 'Loaded build mismatch')
    raise SystemExit(0 if result['matches'] else 1)
