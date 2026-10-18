#!/usr/bin/env python3
"""Offline platform evidence audit. Never calls or mutates a provider service."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys


def load(path):
    return json.loads(Path(path).read_text())


def normalize_assets(payload, provider):
    if provider == "libtv":
        return [{"id": n["nodeKey"], "uri": libtv_single_url(n)} for n in payload["nodes"]]
    if provider == "oiioii":
        if payload.get("ok") is not True:
            raise ValueError("asset snapshot is not a successful response")
        return [{"id": a["assetId"], "uri": a["uri"]}
                for a in payload["data"]["assets"]]
    return payload["assets"]


def normalize_timeline(payload, provider):
    if provider == "libtv":
        return normalize_libtv_timeline(payload)
    if provider == "oiioii":
        if payload.get("code") != "SUCCESS":
            raise ValueError("timeline snapshot is not a successful response")
        data = payload["data"]
        doc = data["document"]
        return {
            "id": doc["documentId"], "duration_ms": doc["timelineDuration"],
            "aspect_ratio": doc["timelineAspectRatio"],
            "clips": [{"id": c["clipId"], "uri": c["resourceUri"],
                       "start_ms": c["targetStart"], "end_ms": c["targetEnd"],
                       "trim_start_ms": c["trimStart"], "trim_end_ms": c["trimEnd"],
                       "volume": c["volume"]} for c in doc["timelineClips"]],
            "source_uris": [r["uri"] for r in data["canvas"]["sourceReferences"]],
        }
    return payload


def libtv_single_url(node):
    urls = node["data"]["url"]
    if len(urls) != 1 or not urls[0]:
        raise ValueError("LibTV evidence requires exactly one real URL per source node")
    return urls[0]


def normalize_libtv_timeline(payload):
    """Resolve clip media by node ID but audit cached source URLs separately.

    LibTV real render tested with live source-node URLs. params.videoList can
    remain stale until --left refreshes it. Never conceal that discrepancy.
    Current adapter intentionally supports video-only, unscaled clip fixtures.
    """
    sources = index_unique([{"id": n["nodeKey"], "node": n} for n in payload["nodes"]])
    node = payload["timeline"]
    if node["nodeType"] != "video-clip":
        raise ValueError("expected LibTV video-clip timeline")
    data = node["data"]
    timeline = data["clipTimelineData"]
    if not timeline["clips"] or timeline["audioSourceNodeIds"]:
        raise ValueError("adapter requires nonempty video-only timeline")
    clips = []
    sizes = set()
    for c in timeline["clips"]:
        if c["type"] != "video" or c["sourceNodeId"] not in timeline["videoSourceNodeIds"]:
            raise ValueError("unsupported clip type or missing source binding")
        source = sources[c["sourceNodeId"]]["node"]
        clips.append({"id": c["id"], "uri": libtv_single_url(source),
            "start_ms": c["startTime"] * 1000, "end_ms": (c["startTime"] + c["duration"]) * 1000,
            "trim_start_ms": c["sourceOffset"] * 1000,
            "trim_end_ms": (c["sourceOffset"] + c["sourceDuration"]) * 1000,
            "volume": 0 if timeline.get("videoAudioMuted", False) else
                timeline.get("videoAudioVolume", 1) * 10 ** (c.get("decibel", 0) / 20)})
        sizes.add((c["width"], c["height"]))
    if len(sizes) != 1:
        raise ValueError("mixed-dimension timelines require explicit output configuration")
    width, height = sizes.pop()
    divisor = math.gcd(width, height)
    crop_start, crop_end = data["cropRange"]
    refs = data["params"]["videoList"]
    if {r["nodeId"] for r in refs} != set(timeline["videoSourceNodeIds"]):
        raise ValueError("cached source list is incomplete")
    return {"id": node["nodeKey"], "duration_ms": (crop_end - crop_start) * 1000,
            "aspect_ratio": f"{width // divisor}:{height // divisor}", "clips": clips,
            "source_uris": [r["url"] for r in refs], "crop_start_ms": crop_start * 1000}


def index_unique(items):
    result = {}
    for item in items:
        if not item["id"] or item["id"] in result:
            raise ValueError("missing or duplicate ID")
        result[item["id"]] = item
    return result


def check(report, name, passed, **details):
    report.append({"check": name, "passed": bool(passed), **details})


def audit_replacement(before_assets, after_assets, before, after, asset_id):
    """All clips and their IDs/timing must survive; all uses of old URI must update."""
    assets_a, assets_b = index_unique(before_assets), index_unique(after_assets)
    source_a, source_b = assets_a[asset_id], assets_b[asset_id]
    old, new = source_a["uri"], source_b["uri"]
    if not old or not new:
        raise ValueError("empty media URI")
    clips_a, clips_b = index_unique(before["clips"]), index_unique(after["clips"])
    affected = [c for c in clips_a.values() if c["uri"] == old]
    if not affected:
        raise ValueError("baseline has no clips referencing the source")
    checks = []
    check(checks, "same_asset_id_new_uri", old != new, asset_id=asset_id, old_uri=old, new_uri=new)
    check(checks, "same_timeline", before["id"] == after["id"])
    check(checks, "same_clip_ids", set(clips_a) == set(clips_b))
    timing = ("start_ms", "end_ms", "trim_start_ms", "trim_end_ms", "volume")
    check(checks, "timing_and_audio_preserved", all(
        cid in clips_b and all(c[k] == clips_b[cid][k] for k in timing)
        for cid, c in clips_a.items()))
    check(checks, "duration_and_aspect_preserved", all(
        before[k] == after[k] for k in ("duration_ms", "aspect_ratio"))
        and before.get("crop_start_ms", 0) == after.get("crop_start_ms", 0))
    check(checks, "affected_clips_updated", all(
        c["id"] in clips_b and clips_b[c["id"]]["uri"] == new for c in affected),
        affected_clip_ids=[c["id"] for c in affected])
    check(checks, "unaffected_clips_preserved", all(
        cid in clips_b and c == clips_b[cid] for cid, c in clips_a.items() if c["uri"] != old))
    check(checks, "no_stale_clip_uri", all(c["uri"] != old for c in clips_b.values()))
    check(checks, "no_stale_source_reference", old not in after["source_uris"])
    return checks


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_media(path, expected_seconds, expected_size):
    if not math.isfinite(expected_seconds) or expected_seconds <= 0:
        raise ValueError("expected duration must be positive and finite")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    audios = [s for s in data["streams"] if s["codec_type"] == "audio"]
    duration = float(data["format"]["duration"])
    checks = []
    check(checks, "export_duration", abs(duration - expected_seconds) <= 0.1, seconds=duration)
    check(checks, "export_size", len(videos) == 1 and
          (videos[0]["width"], videos[0]["height"]) == expected_size)
    check(checks, "export_has_audio", bool(audios))
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path),
                              "-f", "null", "-"], capture_output=True, text=True)
    check(checks, "export_full_decode", decoded.returncode == 0 and not decoded.stderr.strip())
    return checks


def audit_blue_marker(path, seconds):
    """Sample the middle of each supplied segment; intended only for the blue-bar fixture."""
    checks = []
    for second in seconds:
        if not math.isfinite(second) or second < 0:
            raise ValueError("marker sample time must be nonnegative and finite")
        result = subprocess.run([
            "ffmpeg", "-v", "error", "-ss", str(second), "-i", str(path), "-frames:v", "1",
            "-vf", "crop=iw:60:0:10,scale=16:4", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"
        ], check=True, capture_output=True)
        pixels = list(zip(result.stdout[0::3], result.stdout[1::3], result.stdout[2::3]))
        blue = sum(b > 180 and r < 60 and g < 60 for r, g, b in pixels)
        check(checks, "blue_marker", len(pixels) == 64 and blue >= 60,
              sample_seconds=second, blue_pixels=blue, total_pixels=len(pixels))
    return checks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=["oiioii", "libtv", "normalized"], required=True)
    for name in ("assets-before", "assets-after", "timeline-before", "timeline-after", "asset-id", "report"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--source")
    p.add_argument("--roundtrip")
    p.add_argument("--export")
    p.add_argument("--seconds", type=float)
    p.add_argument("--size", help="WIDTHxHEIGHT")
    p.add_argument("--blue-at", type=float, nargs="+")
    args = p.parse_args()
    try:
        if bool(args.source) != bool(args.roundtrip):
            raise ValueError("source and roundtrip must be supplied together")
        if args.export and (args.seconds is None or not args.size):
            raise ValueError("export requires seconds and size")
        if not args.export and (args.seconds is not None or args.size or args.blue_at):
            raise ValueError("media options require export")
        checks = audit_replacement(
            normalize_assets(load(args.assets_before), args.provider),
            normalize_assets(load(args.assets_after), args.provider),
            normalize_timeline(load(args.timeline_before), args.provider),
            normalize_timeline(load(args.timeline_after), args.provider), args.asset_id)
        if args.source:
            a, b = sha256(args.source), sha256(args.roundtrip)
            check(checks, "roundtrip_sha256", a == b, source_sha256=a, roundtrip_sha256=b)
        if args.export:
            size = tuple(map(int, args.size.split("x")))
            if len(size) != 2 or min(size) <= 0:
                raise ValueError("invalid size")
            checks += inspect_media(args.export, args.seconds, size)
            if args.blue_at:
                checks += audit_blue_marker(args.export, args.blue_at)
        report = {"passed": all(c["passed"] for c in checks), "checks": checks}
        if args.export:
            report["export_sha256"] = sha256(args.export)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        report = {"passed": False, "error": str(exc)}
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
