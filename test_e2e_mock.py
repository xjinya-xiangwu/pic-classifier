# -*- coding: utf-8 -*-
"""e2e 测试: mock OpenAI 兼容服务验证识别成功路径; 配置错误时验证熔断与失败原因下发。
运行: python test_e2e_mock.py
(成功路径里本机 mock 需临时放行公网校验, 仅测试内 patch, 产品代码不变)
"""
import json
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from PIL import Image, ImageDraw

import app as pc

tmp = Path(tempfile.mkdtemp(prefix="pc_e2e_"))
pc.APP_DIR = tmp / "apphome"
pc.THUMB_DIR = pc.APP_DIR / "thumbs"
pc.init_db(pc.APP_DIR / "db.sqlite")

TAG = {"has_model": True,
       "clothing": {"type": "连衣裙", "color_main": "白", "pattern": "纯色"},
       "pose": "站立-叉腰", "orientation": "正面", "scale": "全身",
       "quality": {"score": 4, "flags": []}}


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"choices": [{"message": {"content": json.dumps(TAG, ensure_ascii=False)}}],
                           "usage": {"prompt_tokens": 640, "completion_tokens": 1030}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


mock = ThreadingHTTPServer(("127.0.0.1", 9411), Mock)
threading.Thread(target=mock.serve_forever, daemon=True).start()

folder = tmp / "photos"
folder.mkdir()
for i in range(40):
    img = Image.new("RGB", (300, 400), (200, 40 * i % 256, 40))
    ImageDraw.Draw(img).text((10, 10), f"p{i}", fill=(0, 0, 0))
    img.save(folder / f"IMG_{i}.jpg")

pid = pc.db_exec("INSERT INTO project(folder, created_at) VALUES(?,?)", (str(folder), "t")).lastrowid
pc.scan_folder(folder, False, pid)


def wait_tag_done(seconds=30):
    for _ in range(seconds * 4):
        time.sleep(0.25)
        if not pc.STATE["tag"]:
            return


# --- 成功路径 ---
pc.save_settings({"base_url": "http://127.0.0.1:9411/v1", "model": "mock-model",
                  "api_key": "sk-test", "concurrency": 3})
_real_check = pc.check_public_http_url
pc.check_public_http_url = lambda url: None  # 仅测试内放行本机 mock
pc.start_tagging(pid)
wait_tag_done()
pc.check_public_http_url = _real_check
tagged = pc.db_one("SELECT COUNT(*) FROM photo WHERE status='tagged'")[0]
assert tagged == 40, f"40 张应全部识别成功, 实得 {tagged}"
st = pc.state_payload()
assert st["project"]["tagged"] == 40 and st["groups"], "state 应含分组"
print("OK 成功路径: 40 张识别成功并生成分组")

# --- 失败路径: 指向环回地址, 产品公网校验应拦截并触发熔断 ---
pc.db_exec("UPDATE photo SET status='scanned' WHERE project_id=?", (pid,))
pc.save_settings({"base_url": "http://127.0.0.1:1/v1"})
pc.start_tagging(pid)
wait_tag_done()
failed = pc.db_one("SELECT COUNT(*) FROM photo WHERE status='failed'")[0]
untouched = pc.db_one("SELECT COUNT(*) FROM photo WHERE status='scanned'")[0]
assert failed >= 5, f"至少失败 5 张才熔断, 实得 {failed}"
assert failed <= 15, f"熔断后失败数应远小于 40 (含少量在途), 实得 {failed}"
assert untouched > 0, "熔断后应仍有未处理照片"
st = pc.state_payload()
fe = st["project"]["failed_errors"]
assert fe and "127.0.0.1" in fe[0]["msg"], f"失败原因应下发给前端, 实得 {fe}"
print(f"OK 失败路径: 熔断于 {failed} 张失败 / {40 - untouched} 张处理, 原因 =", fe[0]["msg"][:60])

pc._conn.close()
mock.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
print("OK e2e 全部通过 (成功路径 / 熔断 / 失败原因下发)")
