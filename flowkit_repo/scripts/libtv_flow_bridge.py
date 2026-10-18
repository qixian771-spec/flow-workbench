#!/usr/bin/env python3
"""Explicit LibTV -> local FlowKit -> LibTV bridge. Never invokes a LibTV generation model.

submit creates one Flow scene and submits through the batch API. collect checks once,
then uploads real completed media and fills the same LibTV node. State files prevent
automatic retries after ambiguous mutations. This does not intercept the website button.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid


def save(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)


def cli(binary, *args):
    result = subprocess.run([binary, *args], capture_output=True, text=True)
    if result.returncode or any(marker in result.stderr for marker in
                                ("API Request Error", "接口错误", "校验失败")):
        raise RuntimeError("LibTV command failed: " + result.stderr.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return json.loads(result.stdout)


def api(base, route, body=None, method=None):
    request = urllib.request.Request(base + route,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def single_uri(node):
    urls = node["data"]["url"]
    if len(urls) > 1:
        raise ValueError("multiple outputs are not supported")
    return urls[0] if urls else None


def verify_target(node, prompt, old_uri):
    if node["nodeType"] != "video":
        raise ValueError("target must be a video node")
    if node["data"]["params"]["prompt"] != prompt or single_uri(node) != old_uri:
        raise ValueError("target changed since submit; refusing to overwrite concurrent edits")


def validate_generation_request(node):
    params = node["data"]["params"]
    settings = params["settings"]
    if settings["duration"] != 8 or settings["ratio"] != "16:9":
        raise ValueError("bridge supports only an explicit 8-second 16:9 node")
    if params["modeType"] != "singleImage2video" or len(params["imageList"]) != 1:
        raise ValueError("bridge supports exactly one image reference")


def submit(args, path):
    base = args.flow_base.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("FlowKit must be on the local host")
    health = api(base, "/health")
    if health.get("extension_connected") is not True:
        raise ValueError("Flow extension is disconnected")
    project = api(base, "/api/projects/" + args.flow_project)
    if project.get("video_model_family") != "omni_flash":
        raise ValueError("this bridge requires the explicitly selected Omni Flash project")
    node = cli(args.libtv, "node", args.node, "-p", args.project)
    prompt = node["data"]["params"]["prompt"]
    verify_target(node, prompt, single_uri(node))
    validate_generation_request(node)
    if not prompt.strip():
        raise ValueError("node prompt is empty")
    reference = api(base, "/api/scenes/" + args.reference_scene)
    reference_video = api(base, "/api/videos/" + reference["video_id"])
    if reference_video["project_id"] != args.flow_project:
        raise ValueError("reference belongs to another Flow project")
    if reference["horizontal_image_status"] != "COMPLETED":
        raise ValueError("reference image is not complete")
    media_id = str(uuid.UUID(reference["horizontal_image_media_id"]))
    state = {"phase": "reserved", "libtv": args.libtv, "project": args.project,
             "node": args.node, "flow_base": base, "flow_project": args.flow_project,
             "prompt": prompt, "old_uri": single_uri(node), "reference_media_id": media_id,
             "reference_scene": args.reference_scene}
    # Exclusive creation: unknown outcomes never silently cause a second charge.
    with path.open("x") as f:
        json.dump(state, f, ensure_ascii=False)
    state["phase"] = "creating_flow_video"
    save(path, state)
    video = api(base, "/api/videos", {"project_id": args.flow_project,
        "title": "LibTV node " + args.node, "orientation": "HORIZONTAL", "target_duration_s": 8})
    state["video_id"] = video["id"]
    state["phase"] = "creating_flow_scene"
    save(path, state)
    scene = api(base, "/api/scenes", {"video_id": video["id"], "prompt": prompt,
                                      "video_prompt": prompt, "character_names": []})
    state["scene_id"] = scene["id"]
    state["phase"] = "binding_existing_reference"
    save(path, state)
    api(base, "/api/scenes/" + scene["id"], {
        "horizontal_image_media_id": media_id,
        "horizontal_image_url": reference["horizontal_image_url"],
        "horizontal_image_status": "COMPLETED", "duration": 8}, method="PATCH")
    state["phase"] = "submitting"
    save(path, state)
    requests = api(base, "/api/requests/batch", {"requests": [{
        "type": "GENERATE_VIDEO", "provider": "flow", "orientation": "HORIZONTAL",
        "project_id": args.flow_project, "video_id": video["id"], "scene_id": scene["id"]}]})
    if len(requests) != 1:
        raise ValueError("expected one Flow request")
    state.update(phase="submitted", request_id=requests[0]["id"])
    save(path, state)
    print(json.dumps({k: state[k] for k in ("phase", "request_id", "video_id", "scene_id")}))
    return 0


def collect(args, path):
    state = json.loads(path.read_text())
    if state["phase"] == "complete":
        print(json.dumps({"phase": "complete", "node": state["node"], "already_collected": True}))
        return 0
    if state["phase"] != "submitted":
        raise ValueError("incomplete/ambiguous mutation; inspect state before any retry: " + state["phase"])
    base = state["flow_base"]
    query = urllib.parse.urlencode({"video_id": state["video_id"], "type": "GENERATE_VIDEO",
                                   "orientation": "HORIZONTAL"})
    status = api(base, "/api/requests/batch-status?" + query)
    if not status["done"]:
        print(json.dumps({"phase": "pending", "status": status}))
        return 3
    if status["total"] != 1 or not status["all_succeeded"]:
        raise ValueError("Flow generation failed or unexpected requests present")
    request = api(base, "/api/requests/" + state["request_id"])
    scene = api(base, "/api/scenes/" + state["scene_id"])
    if request["status"] != "COMPLETED" or scene["horizontal_video_status"] != "COMPLETED":
        raise ValueError("Flow media is not complete")
    state["flow_media_id"] = str(uuid.UUID(scene["horizontal_video_media_id"]))
    uri = scene["horizontal_video_url"]
    if not uri.startswith("https://"):
        raise ValueError("expected a real remote Flow output URL")
    node = cli(state["libtv"], "node", state["node"], "-p", state["project"])
    verify_target(node, state["prompt"], state["old_uri"])
    validate_generation_request(node)
    media_path = path.parent / "flow-generated.mp4"
    # Use the existing system HTTPS client and its certificate trust store.
    # Never disable certificate verification or retry generation on download errors.
    subprocess.run(["/usr/bin/curl", "--fail", "--silent", "--show-error", "--location",
                    "--proto", "=https", "--proto-redir", "=https", "--max-time", "120",
                    "--output", str(media_path), uri], check=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                            str(media_path)], capture_output=True, text=True, check=True)
    meta = json.loads(probe.stdout)
    videos = [s for s in meta["streams"] if s["codec_type"] == "video"]
    if len(videos) != 1 or (videos[0]["width"], videos[0]["height"]) != (1280, 720):
        raise ValueError("unexpected Flow dimensions")
    if abs(float(meta["format"]["duration"]) - 8) > 0.1:
        raise ValueError("unexpected Flow duration")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(media_path), "-f", "null", "-"], check=True)
    state.update(phase="uploading", media_sha256=hashlib.sha256(media_path.read_bytes()).hexdigest())
    save(path, state)
    uploaded = cli(state["libtv"], "upload", "Flow-live-" + state["request_id"],
                   "-p", state["project"], "--resource", str(media_path))
    state.update(phase="uploaded", upload=uploaded)
    save(path, state)
    node = cli(state["libtv"], "node", state["node"], "-p", state["project"])
    verify_target(node, state["prompt"], state["old_uri"])
    validate_generation_request(node)
    state["phase"] = "filling_target"
    save(path, state)
    cli(state["libtv"], "node", state["node"], "-p", state["project"],
        "-u", "url=" + json.dumps([uploaded["cdnUrl"]]),
        "-u", "resourceMeta=" + json.dumps(uploaded["resourceMeta"]))
    after = cli(state["libtv"], "node", state["node"], "-p", state["project"])
    if after["nodeKey"] != state["node"] or single_uri(after) != uploaded["cdnUrl"]:
        raise ValueError("same-node backfill did not persist")
    state.update(phase="complete", after_node=after)
    save(path, state)
    print(json.dumps({k: state[k] for k in ("phase", "node", "flow_media_id", "media_sha256")}))
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    submit_parser = sub.add_parser("submit")
    for name in ("project", "node", "flow-project", "reference-scene", "state"):
        submit_parser.add_argument("--" + name, required=True)
    submit_parser.add_argument("--libtv", default=str(Path.home() / ".libtv/libtv"))
    submit_parser.add_argument("--flow-base", default="http://127.0.0.1:8100")
    sub.add_parser("collect").add_argument("--state", required=True)
    args = p.parse_args()
    try:
        path = Path(args.state).resolve()
        with path.with_suffix(path.suffix + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return submit(args, path) if args.command == "submit" else collect(args, path)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
