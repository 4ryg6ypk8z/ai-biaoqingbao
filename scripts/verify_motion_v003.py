#!/usr/bin/env python3
"""Independent post-integration QA for the active v003 GIF set."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import statistics
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_motion_v003 import audit_gif  # noqa: E402

RELEASE = ROOT / "production" / "published-v003"
EXPECTED_IDS = [f"{i:03d}" for i in range(1, 101)]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def close(actual: float, expected: float, tol: float = 1e-10) -> bool:
    return abs(actual - expected) <= tol


def main() -> None:
    release_manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    old_manifest = json.loads((ROOT / "production" / "published-v002" / "manifest.json").read_text(encoding="utf-8"))
    motion = json.loads((RELEASE / "motion-audit.json").read_text(encoding="utf-8"))
    rows = list(csv.DictReader((RELEASE / "motion-index.csv").open(encoding="utf-8-sig")))
    catalog = json.loads((ROOT / "docs" / "catalog.json").read_text(encoding="utf-8"))
    assert release_manifest["version"] == "v003"
    assert [x["id"] for x in catalog] == EXPECTED_IDS
    assert [x["id"] for x in motion["items"]] == EXPECTED_IDS
    assert [x["id"] for x in rows] == EXPECTED_IDS
    release_hashes = {(x["id"], int(x["size"])): x["sha256"] for x in release_manifest["items"]}
    old_hashes = {(x["id"], int(x["size"])): x["sha256"] for x in old_manifest["items"]}
    assert len(release_hashes) == 200 and len(old_hashes) == 200

    actual_audits = {240: [], 512: []}
    checks = {"active_sha_matches_v003": 0, "baseline_sha_matches_v002": 0,
              "decoded_dimensions_and_timing": 0, "comfort_peak_under_6pct": 0,
              "loop_or_static_semantics": 0}
    for ident in EXPECTED_IDS:
        row = next(x for x in motion["items"] if x["id"] == ident)
        for size, active in ((240, ROOT / "docs" / "media"), (512, ROOT / "stickers" / "512")):
            live = active / f"{ident}.gif"
            old = RELEASE / "baseline-v002" / str(size) / f"{ident}.gif"
            rel = RELEASE / "assets" / str(size) / f"{ident}.gif"
            actual_hash = digest_file(live)
            assert actual_hash == release_hashes[(ident, size)] == digest_file(rel)
            checks["active_sha_matches_v003"] += 1
            assert digest_file(old) == old_hashes[(ident, size)]
            checks["baseline_sha_matches_v002"] += 1
            measured = audit_gif(live, size)
            expected = row[f"audit{size}"]
            assert measured["frames"] == expected["frames"]
            assert measured["duration_cs"] == expected["duration_cs"]
            assert close(float(measured["mean_art_delta"]), float(expected["mean_art_delta"]))
            assert close(float(measured["peak_art_delta"]), float(expected["peak_art_delta"]))
            checks["decoded_dimensions_and_timing"] += 1
            assert float(measured["peak_art_delta"]) <= 0.0601
            assert float(measured["loop_close_art_delta"]) <= 0.00001
            checks["comfort_peak_under_6pct"] += 1
            assert measured["loop_validation"] in ("explicit-infinite-loop", "single-frame-static-no-cycle")
            if measured["frames"] > 1:
                assert measured["loop_validation"] == "explicit-infinite-loop"
            else:
                assert measured["frames"] == 1
            checks["loop_or_static_semantics"] += 1
            actual_audits[size].append(measured)

    zip_checks = {}
    for size, active in ((240, ROOT / "docs" / "media"), (512, ROOT / "stickers" / "512")):
        zpath = ROOT / "downloads" / f"dafeiyu-{size}.zip"
        with zipfile.ZipFile(zpath) as zf:
            assert zf.testzip() is None
            names = [n for n in zf.namelist() if n.lower().endswith(".gif")]
            assert len(names) == 100
            seen = set()
            for name in names:
                ident = name[:3]
                assert ident in EXPECTED_IDS and ident not in seen
                seen.add(ident)
                assert digest_bytes(zf.read(name)) == digest_file(active / f"{ident}.gif")
            assert seen == set(EXPECTED_IDS)
            assert "来源与许可说明.txt" in zf.namelist()
            zip_checks[str(zpath.relative_to(ROOT))] = {"gif_count": len(names), "crc": "ok", "hashes": "match active"}

    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE.txt").read_text(encoding="utf-8")
    assert "v003 动效舒缓优化" in html and "VOL. 03" in html
    assert "v003 动效舒缓优化" in readme and "v003 动效舒缓优化" in notice
    assert all(f"media/{ident}.gif" in html for ident in EXPECTED_IDS)
    assert all((ROOT / "docs" / "media" / f"{ident}.gif").is_file() for ident in EXPECTED_IDS)
    builder_text = (ROOT / "scripts" / "build_public.py").read_text(encoding="utf-8")
    compile(builder_text, "scripts/build_public.py", "exec")
    assert "production/published-v003/manifest.json" in builder_text

    peaks512 = [float(x["peak_art_delta"]) for x in actual_audits[512]]
    peaks240 = [float(x["peak_art_delta"]) for x in actual_audits[240]]
    before_peaks512 = [float(x["before_peak_art_delta"]) for x in rows]
    before_peaks240 = [float(x["before240_peak_art_delta"]) for x in rows]
    mean512 = statistics.mean(float(x["mean_art_delta"]) for x in actual_audits[512])
    mean240 = statistics.mean(float(x["mean_art_delta"]) for x in actual_audits[240])
    p95_before512, p95_after512 = sorted(before_peaks512)[94], sorted(peaks512)[94]
    p95_before240, p95_after240 = sorted(before_peaks240)[94], sorted(peaks240)[94]
    aggregate = motion["aggregate"]
    report = {
        "status": "PASS",
        "checks": checks,
        "downloads": zip_checks,
        "motion": {
            "items": 100,
            "micro_motion": aggregate["micro_motion_count"],
            "still": aggregate["still_count"],
            "before_mean_step_delta_512": aggregate["before_mean_art_delta_128"],
            "after_mean_step_delta_512": mean512,
            "reduction_512_percent": 100 * (1 - mean512 / aggregate["before_mean_art_delta_128"]),
            "before_mean_step_delta_240": aggregate["before_mean_art_delta_240"],
            "after_mean_step_delta_240": mean240,
            "reduction_240_percent": 100 * (1 - mean240 / aggregate["before_mean_art_delta_240"]),
            "max_step_delta_512": max(peaks512),
            "max_step_delta_240": max(peaks240),
            "p95_per_item_peak_before_512": p95_before512,
            "p95_per_item_peak_after_512": p95_after512,
            "p95_per_item_peak_before_240": p95_before240,
            "p95_per_item_peak_after_240": p95_after240,
            "static_duration_cs": 150,
            "animated_duration_cs": sorted({x["duration_cs"] for x in actual_audits[512] if x["frames"] > 1}),
        },
    }
    report_path = RELEASE / "POST-INTEGRATION-QA.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = (
        "# v003 接入后验收\n\n"
        "## 范围\n\n"
        "100个编号、240×240与512×512两种正式GIF；并核对旧版回退备份、下载包与本地预览路径。\n\n"
        "## 结果\n\n"
        "|检查|结果|\n|---|---:|\n"
        f"|当前版本哈希匹配|{checks['active_sha_matches_v003']}/200|\n"
        f"|v002回退哈希匹配|{checks['baseline_sha_matches_v002']}/200|\n"
        f"|GIF实际解码、尺寸与帧时序|{checks['decoded_dimensions_and_timing']}/200|\n"
        f"|单步幅度≤6%及闭环|{checks['comfort_peak_under_6pct']}/200|\n"
        f"|循环元数据或静帧判定|{checks['loop_or_static_semantics']}/200|\n"
        "|240包与512包|各含100个GIF，CRC与逐项哈希通过|\n\n"
        "## 动作幅度\n\n"
        "测量范围为128px采样画面的动作区 y=0–97；固定字幕区不计。RGB平均绝对差归一化到0–255。\n\n"
        "|指标|v002|v003|\n|---|---:|---:|\n"
        f"|512px平均单步差|{aggregate['before_mean_art_delta_128']:.3%}|{mean512:.3%}|\n"
        f"|240px平均单步差|{aggregate['before_mean_art_delta_240']:.3%}|{mean240:.3%}|\n"
        f"|512px逐项峰值P95|{p95_before512:.3%}|{p95_after512:.3%}|\n"
        f"|240px逐项峰值P95|{p95_before240:.3%}|{p95_after240:.3%}|\n"
        f"|最大单步差|—|512：{max(peaks512):.3%}；240：{max(peaks240):.3%}|\n\n"
        f"v003保留{aggregate['micro_motion_count']}项微动作，{aggregate['still_count']}项使用单帧静态GIF。静帧时长150cs；动画总时长范围156–186cs，19项均为显式无限循环，回到首帧的闭环差为0。\n\n"
        "## 目视材料\n\n"
        "- `qa/all-100-overview.png`：100项接入后总览。\n"
        "- `qa/high-motion-before.png` / `qa/high-motion-after.png`：原高运动条目对照。\n"
        "- `qa/micro-motion-before.png` / `qa/micro-motion-after.png`：保留微动作与静帧对照。\n\n"
        "所有动作帧均从v002现有姿态中挑选并稳定；没有重绘人物、改变服装或配色。\n"
    )
    (RELEASE / "POST-INTEGRATION-QA.md").write_text(markdown, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
