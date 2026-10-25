#!/usr/bin/env python3
"""Build a motion-calmed v003 from the currently mapped v002 GIFs.

This script only writes to output/dafeiyu-100-v003. It never edits the active
stickers, docs, downloads, or production manifests. Run integration separately
after reviewing the generated contacts and audit.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import re
import shutil
import statistics
import subprocess
import tempfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "dafeiyu-100-v003"
SOURCE_512 = ROOT / "stickers" / "512"
SOURCE_240 = ROOT / "docs" / "media"
V002_MANIFEST = ROOT / "production" / "published-v002" / "manifest.json"
CATALOG = ROOT / "docs" / "catalog.json"
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W = H = 128
ART_H = 98  # captions start at y=391/512 in the project's v002 generator
FRAME_BYTES = W * H * 3
ART_BYTES = W * ART_H * 3
WHITE = 255


def run_magick(*args: object, capture: bool = False) -> bytes | None:
    proc = subprocess.run(
        ["magick", *map(str, args)],
        check=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
    )
    return proc.stdout if capture else None


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def decode_raw_128(path: pathlib.Path) -> list[bytes]:
    raw = run_magick(path, "-coalesce", "-resize", "128x128!", "-depth", "8", "RGB:-", capture=True)
    assert raw is not None and len(raw) % FRAME_BYTES == 0, f"bad decoded RGB stream: {path}"
    frames = [raw[i:i + FRAME_BYTES] for i in range(0, len(raw), FRAME_BYTES)]
    if not frames:
        raise ValueError(f"no decoded frames: {path}")
    return frames


def feature(pixels: bytes) -> dict[str, float | int]:
    xs: list[int] = []
    ys: list[int] = []
    for y in range(ART_H):
        row = y * W * 3
        for x in range(W):
            k = row + x * 3
            if min(pixels[k], pixels[k + 1], pixels[k + 2]) < 245:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise ValueError("empty foreground in artwork region")
    return {
        "left": min(xs), "top": min(ys), "right": max(xs), "bottom": max(ys),
        "cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys),
        "width": max(xs) - min(xs) + 1, "height": max(ys) - min(ys) + 1,
    }


def diff_art(a: bytes, b: bytes) -> tuple[float, float]:
    """Mean absolute RGB delta / 255 and fraction of pixels with a >32 channel delta."""
    total = changed = 0
    for k in range(0, ART_BYTES, 3):
        d0 = abs(a[k] - b[k])
        d1 = abs(a[k + 1] - b[k + 1])
        d2 = abs(a[k + 2] - b[k + 2])
        total += d0 + d1 + d2
        changed += max(d0, d1, d2) > 32
    return total / (ART_BYTES * 255), changed / (W * ART_H)


def shifted_pixels(pixels: bytes, dx: int, dy: int) -> bytes:
    """Translate only the caption-free artwork area; leave the caption band fixed."""
    out = bytearray(pixels)
    for y in range(ART_H):
        for x in range(W):
            sx, sy = x - dx, y - dy
            k = (y * W + x) * 3
            if 0 <= sx < W and 0 <= sy < ART_H:
                sk = (sy * W + sx) * 3
                out[k:k + 3] = pixels[sk:sk + 3]
            else:
                out[k:k + 3] = bytes((WHITE, WHITE, WHITE))
    return bytes(out)


def safe_bbox_after_shift(f: dict[str, float | int], dx: int, dy: int) -> bool:
    return (
        int(f["left"]) + dx >= 1
        and int(f["right"]) + dx <= W - 2
        and int(f["top"]) + dy >= 1
        and int(f["bottom"]) + dy <= ART_H - 2
    )


def relative_size_delta(a: dict[str, float | int], b: dict[str, float | int]) -> float:
    w = abs(int(a["width"]) - int(b["width"])) / max(int(a["width"]), int(b["width"]))
    h = abs(int(a["height"]) - int(b["height"])) / max(int(a["height"]), int(b["height"]))
    return max(w, h)


def select_motion(frames: list[bytes]) -> dict[str, object]:
    """Choose a subtle, stable pair from the four original key poses or freeze on their medoid."""
    keyframes = frames[:4]
    feats = [feature(f) for f in keyframes]
    candidates = []
    pairwise = [[0.0] * 4 for _ in range(4)]
    for i in range(4):
        for j in range(i + 1, 4):
            raw_delta, _ = diff_art(keyframes[i], keyframes[j])
            pairwise[i][j] = pairwise[j][i] = raw_delta
            if raw_delta < 0.008:  # duplicated or visually indistinguishable cells are not motion
                continue
            a, b = feats[i], feats[j]
            shift_x = round(float(a["cx"]) - float(b["cx"]))
            shift_y = round(float(a["cy"]) - float(b["cy"]))
            shift_len = math.hypot(shift_x, shift_y)
            size_delta = relative_size_delta(a, b)
            if shift_len > 8 or size_delta > 0.05 or not safe_bbox_after_shift(b, shift_x, shift_y):
                continue
            aligned = shifted_pixels(keyframes[j], shift_x, shift_y)
            delta, changed = diff_art(keyframes[i], aligned)
            aligned_feature = feature(aligned)
            residual_center = math.hypot(
                float(a["cx"]) - float(aligned_feature["cx"]),
                float(a["cy"]) - float(aligned_feature["cy"]),
            )
            if delta <= 0.06 and changed <= 0.27 and residual_center <= 1.5:
                score = delta + 0.001 * (abs(shift_x) + abs(shift_y))
                candidates.append((score, i, j, delta, changed, shift_x, shift_y, size_delta, residual_center, raw_delta))
    if candidates:
        score, i, j, delta, changed, dx, dy, scale, residual, raw_delta = min(candidates)
        return {
            "mode": "micro-motion",
            "frame_a": i, "frame_b": j,
            "delta_before_alignment": raw_delta,
            "delta_after_alignment": delta,
            "changed_pixels_after_alignment": changed,
            "shift_x_128": dx, "shift_y_128": dy,
            "scale_delta": scale, "residual_center_px": residual,
            "profile_score": score,
            "candidate_pairs": len(candidates),
        }
    medoid = min(range(4), key=lambda i: sum(pairwise[i]))
    return {
        "mode": "still",
        "frame_a": medoid, "frame_b": None,
        "delta_before_alignment": 0.0,
        "delta_after_alignment": 0.0,
        "changed_pixels_after_alignment": 0.0,
        "shift_x_128": 0, "shift_y_128": 0,
        "scale_delta": 0.0, "residual_center_px": 0.0,
        "profile_score": 0.0,
        "candidate_pairs": 0,
    }


def motion_profile(label: str, meaning: str) -> tuple[str, list[int], list[int]]:
    text = label + meaning
    if any(x in text for x in ("挥", "送", "递", "接", "抱", "亲", "摸", "拍", "推", "举", "摊", "走", "赶", "吃", "喝", "咖啡", "拜托", "加油")):
        return "gesture-hold", [0, 0, 1, 1, 0, 0], [30, 20, 18, 24, 42, 22]
    if any(x in text for x in ("恭喜", "好运", "生日", "开心", "得意", "欧气", "笑", "点赞", "惊")):
        return "soft-pulse", [0, 1, 1, 0, 0, 0], [38, 18, 20, 26, 44, 26]
    if any(x in text for x in ("困", "累", "麻", "无语", "安静", "等待", "不想说话", "偷闲", "摸鱼", "休息")):
        return "rest-pause", [0, 0, 0, 1, 0, 0], [48, 20, 18, 22, 54, 24]
    return "quiet-reaction", [0, 0, 1, 0, 0, 0], [42, 20, 20, 22, 48, 24]


def composite_aligned_b(frame_a: pathlib.Path, frame_b: pathlib.Path, dx: int, dy: int, out: pathlib.Path) -> None:
    dx512, dy512 = dx * 4, dy * 4
    geometry = f"{dx512:+d}{dy512:+d}"
    run_magick(
        "-size", "512x512", "xc:white",
        "(", frame_b, "-crop", "512x390+0+0", "+repage", ")",
        "-geometry", geometry, "-compose", "over", "-composite",
        "(", frame_a, "-crop", "512x122+0+390", "+repage", ")",
        "-geometry", "+0+390", "-compose", "over", "-composite",
        out,
    )


def create_gif(sequence: list[tuple[pathlib.Path, int]], out: pathlib.Path, palette: pathlib.Path) -> None:
    args: list[object] = ["magick"]
    for path, delay in sequence:
        args.extend(("-delay", delay, "-dispose", "None", path))
    args.extend(("+dither", "-remap", palette, "-loop", 0, "-layers", "Optimize", out))
    subprocess.run(list(map(str, args)), check=True, stdout=subprocess.DEVNULL)


def audit_gif(path: pathlib.Path, expected_size: int) -> dict[str, object]:
    dims_delays = subprocess.check_output(
        ["magick", str(path), "-coalesce", "-format", "%w|%h|%T\\n", "info:"], text=True
    )
    frames = [tuple(map(int, line.split("|"))) for line in dims_delays.splitlines()]
    if not frames or any((w, h) != (expected_size, expected_size) for w, h, _ in frames):
        raise ValueError(f"canvas mismatch {path}: {frames}")
    verbose = subprocess.check_output(["magick", "identify", "-verbose", str(path)], text=True)
    loops = [int(x) for x in re.findall(r"^\s*Iterations:\s*(\d+)\s*$", verbose, re.M)]
    # ImageMagick may omit the Netscape loop extension for a true one-frame
    # still. That is safe because there is no frame cycle to jump across.
    # Animated outputs must explicitly carry an infinite loop extension.
    if len(frames) > 1 and (not loops or any(x != 0 for x in loops)):
        raise ValueError(f"infinite loop mismatch {path}: {loops}")
    if len(frames) == 1 and any(x != 0 for x in loops):
        raise ValueError(f"static loop metadata mismatch {path}: {loops}")
    pixels = decode_raw_128(path)
    if len(pixels) != len(frames):
        raise ValueError(f"decoded frame mismatch {path}: {len(pixels)} vs {len(frames)}")
    pair_metrics = [diff_art(a, b) for a, b in zip(pixels, pixels[1:] + pixels[:1])]
    return {
        "size": expected_size,
        "frames": len(frames),
        "duration_cs": sum(delay for _, _, delay in frames),
        "loop_count": 0,
        "loop_validation": "explicit-infinite-loop" if len(frames) > 1 else "single-frame-static-no-cycle",
        "mean_art_delta": statistics.mean(x[0] for x in pair_metrics),
        "peak_art_delta": max(x[0] for x in pair_metrics),
        "mean_changed_art_pixels": statistics.mean(x[1] for x in pair_metrics),
        "peak_changed_art_pixels": max(x[1] for x in pair_metrics),
        "loop_close_art_delta": pair_metrics[-1][0],
    }


def make_contact(ids: list[str], media_dir: pathlib.Path, out: pathlib.Path, before: bool) -> None:
    strips = []
    temp = out.parent / ".contact-frames"
    temp.mkdir(parents=True, exist_ok=True)
    for ident in ids:
        src = media_dir / f"{ident}.gif"
        strip = temp / f"{ident}.png"
        run_magick(
            src, "-coalesce", "-resize", "128x128!",
            "-background", "white", "-gravity", "south", "-splice", "0x22",
            "-font", FONT, "-pointsize", 13, "-fill", "#202c70", "-annotate", "+0+2", ident,
            "+append", strip,
        )
        strips.append(strip)
    subprocess.run(
        ["magick", "montage", "-font", FONT, *map(str, strips), "-tile", "1x", "-geometry", "+4+4",
         "-background", "#edf2fb", str(out)], check=True, stdout=subprocess.DEVNULL
    )
    shutil.rmtree(temp)


def verify_v002_sources(catalog: list[dict[str, object]]) -> dict[tuple[str, int], str]:
    manifest = json.loads(V002_MANIFEST.read_text(encoding="utf-8"))
    expected = {(x["id"], int(x["size"])): x["sha256"] for x in manifest["items"]}
    if manifest.get("version") != "v002" or len(expected) != 200:
        raise ValueError("published-v002 manifest is missing, malformed, or not 200 rows")
    for item in catalog:
        ident = str(item["id"])
        for size, path in ((240, SOURCE_240 / f"{ident}.gif"), (512, SOURCE_512 / f"{ident}.gif")):
            if not path.is_file() or sha256(path) != expected[(ident, size)]:
                raise ValueError(f"active v002 source changed or mismatched; refusing: {path}")
    return expected


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"Refusing to overwrite existing version output: {OUT}")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if len(catalog) != 100 or [x["id"] for x in catalog] != [f"{i:03d}" for i in range(1, 101)]:
        raise ValueError("catalog is not exactly IDs 001–100")
    verify_v002_sources(catalog)
    OUT.mkdir(parents=True)
    (OUT / "assets" / "512").mkdir(parents=True)
    (OUT / "assets" / "240").mkdir(parents=True)
    (OUT / "keyframes").mkdir()
    (OUT / "qa").mkdir()
    (OUT / "downloads").mkdir()
    temp_root = pathlib.Path(tempfile.mkdtemp(prefix="dafeiyu-v003-"))
    before_metrics: dict[str, dict[str, float]] = {}
    rows = []
    manifest_items = []
    try:
        for item in catalog:
            ident, label, meaning = str(item["id"]), str(item["label"]), str(item["meaning"])
            source = SOURCE_512 / f"{ident}.gif"
            source_frames = decode_raw_128(source)
            if len(source_frames) != 6:
                raise ValueError(f"expected six v002 keyframe slots: {ident} has {len(source_frames)}")
            source_step_metrics = [diff_art(a, b) for a, b in zip(source_frames, source_frames[1:] + source_frames[:1])]
            before_metrics[ident] = {
                "mean": statistics.mean(x[0] for x in source_step_metrics),
                "peak": max(x[0] for x in source_step_metrics),
                "changed": statistics.mean(x[1] for x in source_step_metrics),
                "peak_changed": max(x[1] for x in source_step_metrics),
            }
            source240 = decode_raw_128(SOURCE_240 / f"{ident}.gif")
            source240_steps = [diff_art(a, b) for a, b in zip(source240, source240[1:] + source240[:1])]
            before_metrics[ident]["mean240"] = statistics.mean(x[0] for x in source240_steps)
            before_metrics[ident]["peak240"] = max(x[0] for x in source240_steps)
            selection = select_motion(source_frames)
            item_tmp = temp_root / ident
            item_tmp.mkdir()
            subprocess.run(
                ["magick", str(source), "-coalesce", "-scene", "0", str(item_tmp / "frame-%02d.png")],
                check=True, stdout=subprocess.DEVNULL,
            )
            frame_a = item_tmp / f"frame-{int(selection['frame_a']):02d}.png"
            if selection["mode"] == "micro-motion":
                frame_b_source = item_tmp / f"frame-{int(selection['frame_b']):02d}.png"
                frame_b = item_tmp / "frame-b-aligned.png"
                composite_aligned_b(
                    frame_a, frame_b_source,
                    int(selection["shift_x_128"]), int(selection["shift_y_128"]), frame_b,
                )
                profile, positions, delays = motion_profile(label, meaning)
                sequence = [(frame_a if pos == 0 else frame_b, delay) for pos, delay in zip(positions, delays)]
            else:
                frame_b = None
                profile, positions, delays = "still", [0], [150]
                sequence = [(frame_a, 150)]
            palette = item_tmp / "palette.png"
            frame_paths = [p for p, _ in sequence]
            run_magick(*frame_paths, "-append", "-colors", 256, "-unique-colors", palette)
            gif512 = OUT / "assets" / "512" / f"{ident}.gif"
            gif240 = OUT / "assets" / "240" / f"{ident}.gif"
            create_gif(sequence, gif512, palette)
            run_magick(gif512, "-coalesce", "-resize", "240x240!", "+dither", "-colors", 128,
                       "-loop", 0, "-layers", "Optimize", gif240)
            kf_dir = OUT / "keyframes" / ident
            kf_dir.mkdir()
            shutil.copy2(frame_a, kf_dir / "A.png")
            if frame_b is not None:
                shutil.copy2(frame_b, kf_dir / "B-aligned.png")
            audit512 = audit_gif(gif512, 512)
            audit240 = audit_gif(gif240, 240)
            if audit512["peak_art_delta"] > 0.0601 or audit240["peak_art_delta"] > 0.0601:
                raise ValueError(f"comfort max step exceeded after encoding for {ident}: {audit512} / {audit240}")
            if audit512["loop_close_art_delta"] > 0.00001 or audit240["loop_close_art_delta"] > 0.00001:
                raise ValueError(f"loop did not return to the same pose for {ident}")
            after = {k: audit512[k] for k in ("mean_art_delta", "peak_art_delta", "peak_changed_art_pixels", "duration_cs", "frames")}
            row = {
                "id": ident, "label": label, "meaning": meaning,
                "mode": selection["mode"], "profile": profile,
                "source_keyframe_a": selection["frame_a"], "source_keyframe_b": selection["frame_b"],
                "delta_before_alignment": selection["delta_before_alignment"],
                "delta_after_alignment": selection["delta_after_alignment"],
                "changed_pixels_after_alignment": selection["changed_pixels_after_alignment"],
                "stabilization_dx_128": selection["shift_x_128"], "stabilization_dy_128": selection["shift_y_128"],
                "relative_scale_delta": selection["scale_delta"],
                "before_mean_art_delta": before_metrics[ident]["mean"],
                "before_peak_art_delta": before_metrics[ident]["peak"],
                "before_mean_changed_pixels": before_metrics[ident]["changed"],
                "before240_mean_art_delta": before_metrics[ident]["mean240"],
                "before240_peak_art_delta": before_metrics[ident]["peak240"],
                "after_mean_art_delta": audit512["mean_art_delta"],
                "after_peak_art_delta": audit512["peak_art_delta"],
                "after_mean_changed_pixels": audit512["mean_changed_art_pixels"],
                "after240_mean_art_delta": audit240["mean_art_delta"],
                "after240_peak_art_delta": audit240["peak_art_delta"],
                "after_frames_512": audit512["frames"], "after_duration_cs_512": audit512["duration_cs"],
                "after_frames_240": audit240["frames"], "after_duration_cs_240": audit240["duration_cs"],
                "hash512": sha256(gif512), "hash240": sha256(gif240),
                "sha512_bytes": gif512.stat().st_size, "sha240_bytes": gif240.stat().st_size,
            }
            rows.append(row)
            manifest_items.append({
                "id": ident, "label": label, "meaning": meaning,
                "mode": selection["mode"], "profile": profile,
                "sha512": row["hash512"], "sha240": row["hash240"],
                "bytes512": row["sha512_bytes"], "bytes240": row["sha240_bytes"],
                "audit512": audit512, "audit240": audit240,
            })
            shutil.rmtree(item_tmp)
            print(f"{ident} {label}: {selection['mode']} peak={audit512['peak_art_delta']:.4%} frames={audit512['frames']} duration={audit512['duration_cs']}cs")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    fieldnames = list(rows[0])
    with (OUT / "motion-index.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    baseline_values = [v for v in before_metrics.values()]
    after_mean = statistics.mean(float(r["after_mean_art_delta"]) for r in rows)
    before_mean = statistics.mean(v["mean"] for v in baseline_values)
    after_mean240 = statistics.mean(float(r["after240_mean_art_delta"]) for r in rows)
    before_mean240 = statistics.mean(v["mean240"] for v in baseline_values)
    after_peak_p95 = sorted(float(r["after_peak_art_delta"]) for r in rows)[94]
    before_peak_p95 = sorted(v["peak"] for v in baseline_values)[94]
    report = {
        "version": "v003-motion-calmed",
        "source_version": "published-v002",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "items": manifest_items,
        "aggregate": {
            "count": len(rows),
            "micro_motion_count": sum(r["mode"] == "micro-motion" for r in rows),
            "still_count": sum(r["mode"] == "still" for r in rows),
            "before_mean_art_delta_128": before_mean,
            "after_mean_art_delta_128": after_mean,
            "mean_delta_reduction_percent": 100 * (1 - after_mean / before_mean),
            "before_mean_art_delta_240": before_mean240,
            "after_mean_art_delta_240": after_mean240,
            "mean_delta_reduction_percent_240": 100 * (1 - after_mean240 / before_mean240),
            "before_peak_step_p95_128": before_peak_p95,
            "after_peak_step_p95_128": after_peak_p95,
            "peak_step_reduction_percent_p95": 100 * (1 - after_peak_p95 / before_peak_p95),
            "comfort_peak_limit": 0.06,
            "loop_close_limit": 0.00001,
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "MOTION-STANDARD.md").write_text(
        "# v003 舒缓动效标准\n\n"
        "- 对象：GIF 解码并 coalesce 后，缩至 128×128；只计算画面动作区域 y=0–97，排除固定字幕带。\n"
        "- 单步幅度：归一化 RGB 平均绝对差不超过 6%（全 3 通道、0–255）；changed pixel 指任一通道差值大于32。\n"
        "- 稳定：候选关键帧按前景质心作最多8px/128校正；相对宽/高变化不超过5%；位移后前景保留1px内边距。\n"
        "- 超过阈值的条目使用画面稳定的静止 GIF，不为保留动画而接受大跳变。\n"
        "- 循环：微动片段起末回到完全相同 A 帧，闭环差为0；每种含义按关键帧自身姿势和语义选择轻动作配置。\n"
        "- v002 根因：六帧序列来自四张独立2×2姿态图 `[0,1,2,3,2,1]`，延时统一为 `[28,14,18,18,18,14]` cs；不同关键姿态没有连续过渡，帧间抖动又在每个GIF里复用同一节奏。\n",
        encoding="utf-8",
    )
    high_ids = [x["id"] for x in sorted(rows, key=lambda r: float(r["before_mean_art_delta"]), reverse=True)[:8]]
    make_contact(high_ids, SOURCE_512, OUT / "qa" / "high-motion-before.png", before=True)
    make_contact(high_ids, OUT / "assets" / "512", OUT / "qa" / "high-motion-after.png", before=False)
    # One compact static-frame overview of the complete new active set.
    tiles = []
    temp = OUT / "qa" / ".overview-tiles"
    temp.mkdir()
    for item in catalog:
        ident = str(item["id"])
        tile = temp / f"{ident}.png"
        run_magick(
            str(OUT / "assets" / "512" / f"{ident}.gif") + "[0]", "-coalesce", "-resize", "96x96!",
            "-background", "white", "-gravity", "south", "-splice", "0x20", "-font", FONT,
            "-pointsize", 12, "-fill", "#202c70", "-annotate", "+0+2", ident, tile,
        )
        tiles.append(tile)
    subprocess.run(
        ["magick", "montage", "-font", FONT, *map(str, tiles), "-tile", "10x10", "-geometry", "+4+4",
         "-background", "#edf2fb", str(OUT / "qa" / "all-100-overview.png")],
        check=True, stdout=subprocess.DEVNULL,
    )
    shutil.rmtree(temp)
    print(json.dumps(report["aggregate"], ensure_ascii=False))


if __name__ == "__main__":
    main()
