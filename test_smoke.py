# -*- coding: utf-8 -*-
"""冒烟测试: 扫描 → 模拟打标 → 分组 → 选保留 → 原地重命名 → 撤销。运行: python test_smoke.py"""
import json
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import app as pc

tmp = Path(tempfile.mkdtemp(prefix="pc_test_"))
pc.APP_DIR = tmp / "apphome"
pc.THUMB_DIR = pc.APP_DIR / "thumbs"
pc.init_db(pc.APP_DIR / "db.sqlite")

# 1. 生成测试图: 3 种"衣着"(颜色区分) × 4 张 (2 姿势 × 2 朝向)
folder = tmp / "photos"
folder.mkdir()
colors = ["白", "红", "蓝"]
paths = []
for ci, cname in enumerate(colors):
    for k in range(4):
        p = folder / f"IMG_{ci}_{k}.png"
        img = Image.new("RGB", (300, 400), [(240, 240, 240), (200, 40, 40), (40, 80, 200)][ci])
        ImageDraw.Draw(img).text((10, 10), f"{cname}-{k}", fill=(0, 0, 0))
        img.save(p)
        paths.append(p)

pc.db_exec("INSERT INTO project(folder, created_at) VALUES(?,?)", (str(folder), "2026-09-21T00:00:00"))
pc.scan_folder(folder, False, 1)
rows = pc.db_all("SELECT * FROM photo ORDER BY path")
assert len(rows) == 12, f"扫描应得 12 张, 实得 {len(rows)}"
assert len(list(pc.THUMB_DIR.glob("*.jpg"))) == 12, "缩略图应生成 12 张"

# 2. 模拟打标: 每种颜色内 k=0,1 同姿势同朝向, k=2,3 各不同 → 每色 3 组, 共 9 组
for i, r in enumerate(rows):
    ci, k = i // 4, i % 4
    pose, ori = [("站立-叉腰", "正面"), ("站立-叉腰", "正面"), ("行走", "正面"), ("行走", "右侧45°")][k]
    pc.db_exec("UPDATE photo SET status='tagged', clothing=?, pose=?, orientation=?, scale='全身', quality=? WHERE id=?",
               (json.dumps({"type": "连衣裙", "color_main": colors[ci], "pattern": "纯色"}, ensure_ascii=False),
                pose, ori, 3 + (i % 3), r["id"]))

# 3. 分组
data = pc.compute_groups(1, "medium", 0)
assert len(data["groups"]) == 9, f"medium 粒度应得 9 组, 实得 {len(data['groups'])}"
merged = pc.compute_groups(1, "medium", 3)
assert len(merged["groups"]) <= 3, "target=3 应合并到 ≤3 组"
assert all(g["name"].startswith("G") for g in data["groups"]), "组名应以 G 开头"
assert "叉腰" in data["groups"][0]["name"], "组名应含姿势简称"

# 4. 每组选 1 张保留
for g in data["groups"]:
    r = pc.select_photo(1, g["members"][0]["id"])
    assert r.get("selected") == 1, "选择应成功"
keepers = pc.db_all("SELECT COUNT(*) FROM photo WHERE selected=1")[0][0]
assert keepers == 9, f"应选 9 张保留, 实得 {keepers}"
# 换选: 再点一张, 同组互斥
g0 = data["groups"][0]
pc.select_photo(1, g0["members"][1]["id"])
n0 = pc.db_one("SELECT COUNT(*) FROM photo WHERE id IN (%s) AND selected=1" % ",".join("?" * len(g0["members"])),
               [m["id"] for m in g0["members"]])[0]
assert n0 == 1, "同组只应有 1 张保留"

# 5. 原地重命名
res = pc.apply_renames(1)
assert res["renamed"] == 12, f"应重命名 12 张, 实得 {res['renamed']}"
files = sorted(p.name for p in folder.iterdir())
assert all(f.startswith("G") for f in files), f"文件应全部改为组名: {files[:3]}"
assert sum("_精选" in f for f in files) == 9, "每组保留 1 张应有 _精选 标记"
assert Path(res["manifest"]).exists(), "manifest.csv 应生成"

# 6. 撤销
res2 = pc.undo_renames(1)
assert res2["restored"] == 12, f"应还原 12 个文件名, 实得 {res2['restored']}"
files2 = sorted(p.name for p in folder.iterdir())
assert files2 == sorted(p.name for p in paths), "撤销后应恢复全部原文件名"

pc._conn.close()
shutil.rmtree(tmp)
print("OK 冒烟测试全部通过 (扫描/分组/合并/互斥选择/重命名/撤销)")
