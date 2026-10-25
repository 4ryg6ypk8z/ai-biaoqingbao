#!/usr/bin/env python3
"""Safely archive and activate the v003 motion-calmed sticker set."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "dafeiyu-100-v003"
V002 = ROOT / "production" / "published-v002"
PUBLISHED = ROOT / "production" / "published-v003"
CATALOG_PATH = ROOT / "docs" / "catalog.json"
ACTIVE_DIRS = {240: ROOT / "docs" / "media", 512: ROOT / "stickers" / "512"}
ZIP_PATHS = {240: ROOT / "downloads" / "dafeiyu-240.zip", 512: ROOT / "downloads" / "dafeiyu-512.zip"}
TEXT_PATHS = [ROOT / "README.md", ROOT / "NOTICE.txt", ROOT / "docs" / "index.html"]


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copy_tree(src: pathlib.Path, dest: pathlib.Path) -> None:
    shutil.copytree(src, dest, copy_function=shutil.copy2)


def write_zip(target: pathlib.Path, size: int, rows: list[dict[str, object]], asset_root: pathlib.Path,
              notice_path: pathlib.Path) -> None:
    folder = asset_root / str(size)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=7) as zf:
        for item in rows:
            ident, label = str(item["id"]), str(item["label"])
            zf.write(folder / f"{ident}.gif", f"{ident}-{label}.gif")
        zf.write(notice_path, "来源与许可说明.txt")
    with zipfile.ZipFile(target) as zf:
        if zf.testzip() is not None:
            raise ValueError(f"ZIP CRC failure: {target}")
        names = zf.namelist()
        gif_names = [n for n in names if n.lower().endswith(".gif")]
        if len(gif_names) != 100 or len({n[:3] for n in gif_names}) != 100:
            raise ValueError(f"ZIP does not contain 100 unique GIFs: {target}")


def verify_gif(path: pathlib.Path, size: int, expected_hash: str) -> dict[str, object]:
    if not path.is_file() or sha256(path) != expected_hash:
        raise ValueError(f"asset hash mismatch: {path}")
    import subprocess
    lines = subprocess.check_output(
        ["magick", str(path), "-coalesce", "-format", "%w|%h|%T\\n", "info:"], text=True
    ).splitlines()
    frames = [tuple(map(int, line.split("|"))) for line in lines]
    if not frames or any((w, h) != (size, size) for w, h, _ in frames):
        raise ValueError(f"asset dimensions invalid: {path} {frames}")
    if len(frames) > 1:
        verbose = subprocess.check_output(["magick", "identify", "-verbose", str(path)], text=True)
        if not any(line.strip() == "Iterations: 0" for line in verbose.splitlines()):
            raise ValueError(f"animated asset lacks infinite-loop metadata: {path}")
    return {"frames": len(frames), "duration_cs": sum(delay for _, _, delay in frames),
            "size": size, "loop_validation": "explicit-infinite-loop" if len(frames) > 1 else "single-frame-static-no-cycle"}


def safe_replace(source: pathlib.Path, target: pathlib.Path) -> None:
    temp = target.with_name(f".{target.name}.v003-tmp")
    if temp.exists():
        raise ValueError(f"refusing to overwrite stale temp file: {temp}")
    shutil.copy2(source, temp)
    os.replace(temp, target)


def replace_text(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected exactly one text anchor: {old!r}")
    return text.replace(old, new, 1)


def prepare_text_updates(stage: pathlib.Path, archive: pathlib.Path) -> dict[pathlib.Path, pathlib.Path]:
    staged_docs = stage / "project-text"
    staged_docs.mkdir()
    updates: dict[pathlib.Path, pathlib.Path] = {}
    for source in TEXT_PATHS:
        target = staged_docs / source.name
        shutil.copy2(source, target)
        updates[source] = target

    readme = updates[ROOT / "README.md"]
    text = readme.read_text(encoding="utf-8")
    text = replace_text(text, "**持续更新 · v002 全套修订（2026-10-25）**。",
                        "**持续更新 · v003 动效舒缓优化（2026-10-25）**。")
    text = replace_text(text,
                        "当前100个已全部替换为 v002 修订版，后续继续完善动作一致性、更多场景与平台适配。",
                        "当前100个已全部更新为 v003 舒缓动效版：512×512 与 240×240 两种尺寸均已接入。")
    readme.write_text(text, encoding="utf-8")

    notice = updates[ROOT / "NOTICE.txt"]
    text = notice.read_text(encoding="utf-8")
    text = replace_text(text, "当前发布：v002 全套修订，2026-10-25；100个编号全部替换。",
                        "当前发布：v003 动效舒缓优化，2026-10-25；100个编号的240×240与512×512 GIF均已更新。")
    notice.write_text(text, encoding="utf-8")

    index = updates[ROOT / "docs" / "index.html"]
    text = index.read_text(encoding="utf-8")
    text = replace_text(text, "v002 全套修订 · 持续更新", "v003 动效舒缓优化 · 持续更新")
    text = replace_text(text, "VOL. 02", "VOL. 03")
    index.write_text(text, encoding="utf-8")

    archive_text = archive / "project-text"
    archive_text.mkdir()
    for original, staged in updates.items():
        source_copy = archive_text / original.relative_to(ROOT)
        source_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, source_copy)
        # Keep the final text snapshot alongside the source asset set.
        final_copy = archive / "project-text-v003" / original.relative_to(ROOT)
        final_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, final_copy)
    return updates


def patch_public_builder(staged_script: pathlib.Path) -> None:
    src = ROOT / "scripts" / "build_public.py"
    shutil.copy2(src, staged_script)
    s = staged_script.read_text(encoding="utf-8")
    old = "corrected=(R/'production/published-v002/manifest.json').exists();m="
    new = "release_version='v003' if (R/'production/published-v003/manifest.json').exists() else ('v002' if (R/'production/published-v002/manifest.json').exists() else 'v001');corrected=release_version!='v001';m="
    if s.count(old) != 1:
        raise ValueError("build_public.py version-detection anchor changed")
    s = s.replace(old, new, 1)
    marker = "items=m['items'];assert len(items)==100"
    dynamic = "items=m['items'];assert len(items)==100;release_name={'v003':'v003 动效舒缓优化','v002':'v002 全套修订','v001':'持续更新中'}[release_version];release_edition={'v003':'03','v002':'02','v001':'01'}[release_version]"
    if s.count(marker) != 1:
        raise ValueError("build_public.py item marker changed")
    s = s.replace(marker, dynamic, 1)
    s = s.replace("s=s.replace('持续更新中','v002 全套修订 · 持续更新')",
                  "s=s.replace('持续更新中',release_name+' · 持续更新')")
    s = s.replace("s=s.replace('当前已制作100个，','当前100个已全部替换为 v002 修订版，')",
                  "s=s.replace('当前已制作100个，',f'当前100个已全部替换为 {release_version} 版，')")
    s = s.replace("if target.name=='README.md':s=s.replace('**持续更新**。','**持续更新 · v002 全套修订（2026-10-25）**。',1)",
                  "if target.name=='README.md':s=s.replace('**持续更新**。',f'**持续更新 · {release_name}（2026-10-25）**。',1)")
    s = s.replace(".replace('VOL. 01','VOL. 02')", ".replace('VOL. 01',f'VOL. {release_edition}')")
    if "v002 全套修订 · 持续更新" in s or "VOL. 02" in s:
        raise ValueError("build_public.py retains a hard-coded v002 preview label")
    compile(s, str(src), "exec")
    staged_script.write_text(s, encoding="utf-8")


def main() -> None:
    if PUBLISHED.exists():
        raise SystemExit(f"Refusing to overwrite an existing release: {PUBLISHED}")
    if not OUT.is_dir() or not V002.is_dir():
        raise ValueError("v002 source or v003 build output is missing")
    stage = ROOT / "production" / ".published-v003-staging"
    if stage.exists():
        raise SystemExit(f"Refusing to overwrite existing staging directory: {stage}")
    v002_manifest = json.loads((V002 / "manifest.json").read_text(encoding="utf-8"))
    source_hashes = {(x["id"], int(x["size"])): x["sha256"] for x in v002_manifest["items"]}
    output = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    rows = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    expected_ids = [f"{i:03d}" for i in range(1, 101)]
    if [x["id"] for x in rows] != expected_ids or len(output["items"]) != 100:
        raise ValueError("catalog or motion manifest is not exactly IDs 001–100")

    # Stale or user-edited active artwork blocks integration before any write.
    for item in rows:
        ident = item["id"]
        for size, active in ACTIVE_DIRS.items():
            path = active / f"{ident}.gif"
            if not path.is_file() or sha256(path) != source_hashes[(ident, size)]:
                raise ValueError(f"active asset differs from v002; refusing replacement: {path}")
    manifest_by_id = {x["id"]: x for x in output["items"]}
    if list(manifest_by_id) != expected_ids:
        raise ValueError("v003 manifest IDs or order are invalid")
    for item in rows:
        ident = str(item["id"])
        entry = manifest_by_id[ident]
        for size, key in ((512, "sha512"), (240, "sha240")):
            source = OUT / "assets" / str(size) / f"{ident}.gif"
            measured = verify_gif(source, size, str(entry[key]))
            audit = entry[f"audit{size}"]
            if measured["frames"] != audit["frames"] or measured["duration_cs"] != audit["duration_cs"]:
                raise ValueError(f"frame timing changed from motion audit: {source}")
            if audit["peak_art_delta"] > 0.0601 or audit["loop_close_art_delta"] > 0.00001:
                raise ValueError(f"comfort threshold failed: {source}")

    stage.mkdir()
    archive = stage / "release"
    archive.mkdir()
    copy_tree(OUT / "assets", archive / "assets")
    copy_tree(OUT / "keyframes", archive / "keyframes")
    copy_tree(OUT / "qa", archive / "qa")
    shutil.copy2(OUT / "motion-index.csv", archive / "motion-index.csv")
    shutil.copy2(OUT / "MOTION-STANDARD.md", archive / "MOTION-STANDARD.md")
    shutil.copy2(OUT / "manifest.json", archive / "motion-audit.json")
    shutil.copy2(ROOT / "scripts" / "build_motion_v003.py", archive / "build_motion_v003.py")

    rollback = archive / "baseline-v002"
    rollback.mkdir()
    rollback_hashes = []
    for size, active in ACTIVE_DIRS.items():
        backup_dir = rollback / str(size)
        backup_dir.mkdir()
        for item in rows:
            ident = str(item["id"])
            source = active / f"{ident}.gif"
            shutil.copy2(source, backup_dir / source.name)
            rollback_hashes.append({"path": str(source.relative_to(ROOT)), "sha256": sha256(source)})
    for size, zippath in ZIP_PATHS.items():
        shutil.copy2(zippath, rollback / zippath.name)
        rollback_hashes.append({"path": str(zippath.relative_to(ROOT)), "sha256": sha256(zippath)})
    for path in TEXT_PATHS:
        dest = rollback / "project-text" / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        rollback_hashes.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
    builder_backup = rollback / "scripts" / "build_public.py"
    builder_backup.parent.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "build_public.py", builder_backup)
    rollback_hashes.append({"path": "scripts/build_public.py", "sha256": sha256(builder_backup)})
    shutil.copy2(V002 / "manifest.json", rollback / "published-v002-manifest.json")

    # Project manifest follows the existing published-v002 format.
    published_items = []
    for item in rows:
        ident = str(item["id"])
        for size, key in ((240, "sha240"), (512, "sha512")):
            published_items.append({"id": ident, "size": size, "sha256": manifest_by_id[ident][key]})
    (archive / "manifest.json").write_text(
        json.dumps({"version": "v003", "variant": "motion-calmed", "source": "production/published-v003/assets",
                    "items": published_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (rollback / "rollback-hashes.json").write_text(
        json.dumps(rollback_hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    temp_zips = archive / "downloads"
    temp_zips.mkdir()
    text_updates = prepare_text_updates(stage, archive)
    notice_stage = text_updates[ROOT / "NOTICE.txt"]
    for size in (240, 512):
        write_zip(temp_zips / f"dafeiyu-{size}.zip", size, rows, archive / "assets", notice_stage)
    # Preserve final download bundles inside the release folder.
    shutil.copy2(temp_zips / "dafeiyu-240.zip", archive / "dafeiyu-240.zip")
    shutil.copy2(temp_zips / "dafeiyu-512.zip", archive / "dafeiyu-512.zip")

    changelog = (
        "# v003 动效舒缓优化\n\n"
        "- 更新范围：100/100 含义；512×512 与 240×240 两种 GIF，共200项。\n"
        "- 原因：v002 将四张独立姿态拼入六帧循环，关键帧之间无连续过渡，且未做画面配准，造成大幅跳变。\n"
        "- 修复：仅从原有姿态帧中挑选符合舒适阈值的细微帧差，局部对齐主体但不缩放、不旋转、不重绘角色；未达阈值的条目使用稳定单帧。\n"
        f"- 512px动作区平均单步RGB差：{output['aggregate']['before_mean_art_delta_128']:.3%} → {output['aggregate']['after_mean_art_delta_128']:.3%}。\n"
        f"- 240px动作区平均单步RGB差：{output['aggregate']['before_mean_art_delta_240']:.3%} → {output['aggregate']['after_mean_art_delta_240']:.3%}。\n"
        f"- 单步动作区归一化RGB平均差峰值上限为6%；v003保留微动作{output['aggregate']['micro_motion_count']}项，其余{output['aggregate']['still_count']}项为稳定静态GIF；逐项数据见 MOTION-STANDARD.md、motion-index.csv。\n"
        "- 当前本地预览与两份下载ZIP更新到v003；没有提交、推送或外部发布。\n"
    )
    (archive / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    patch_public_builder(stage / "build_public.py")
    shutil.copy2(stage / "build_public.py", archive / "build_public.py")

    # Snapshots and archive are complete before replacing live mappings.
    os.replace(archive, PUBLISHED)
    replaced: list[tuple[pathlib.Path, pathlib.Path]] = []
    try:
        for item in rows:
            ident = str(item["id"])
            for size, active in ACTIVE_DIRS.items():
                target = active / f"{ident}.gif"
                backup = PUBLISHED / "assets" / str(size) / f"{ident}.gif"
                safe_replace(backup, target)
                replaced.append((target, PUBLISHED / "baseline-v002" / str(size) / f"{ident}.gif"))
        for size, target in ZIP_PATHS.items():
            safe_replace(PUBLISHED / "downloads" / target.name, target)
            replaced.append((target, PUBLISHED / "baseline-v002" / target.name))
        for target, staged in text_updates.items():
            safe_replace(staged, target)
            replaced.append((target, PUBLISHED / "baseline-v002" / "project-text" / target.relative_to(ROOT)))
        # Keep the version-aware public build logic current so rebuilding locally does not relabel v003 as v002.
        safe_replace(stage / "build_public.py", ROOT / "scripts" / "build_public.py")
        replaced.append((ROOT / "scripts" / "build_public.py", PUBLISHED / "baseline-v002" / "scripts" / "build_public.py"))

        for item in rows:
            ident = str(item["id"])
            entry = manifest_by_id[ident]
            for size, key in ((512, "sha512"), (240, "sha240")):
                verify_gif(ACTIVE_DIRS[size] / f"{ident}.gif", size, str(entry[key]))
        for size, target in ZIP_PATHS.items():
            with zipfile.ZipFile(target) as zf:
                if zf.testzip() is not None:
                    raise ValueError(f"active download ZIP CRC failure: {target}")
                gif_names = [n for n in zf.namelist() if n.lower().endswith(".gif")]
                if len(gif_names) != 100:
                    raise ValueError(f"active download ZIP missing IDs: {target}")
        preview_dir = ROOT / "docs" / "media"
        if len(list(preview_dir.glob("*.gif"))) != 100:
            raise ValueError(f"docs preview does not contain 100 GIFs: {preview_dir}")
        (PUBLISHED / "integration.json").write_text(json.dumps({
            "status": "active-local-v003",
            "changed_paths": [str(p.relative_to(ROOT)) for p, _ in replaced],
            "active_gif_count": 200,
            "download_zip_count": 2,
            "external_publish": False,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        for target, backup in reversed(replaced):
            if backup.is_file():
                safe_replace(backup, target)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    print(json.dumps({"status": "active-local-v003", "published": str(PUBLISHED),
                      "updated_gifs": 200, "micro_motion": output["aggregate"]["micro_motion_count"],
                      "still": output["aggregate"]["still_count"],
                      "downloads": [str(x) for x in ZIP_PATHS.values()]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
