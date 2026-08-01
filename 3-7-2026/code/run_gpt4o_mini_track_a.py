# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# Thêm thư mục code vào path để import core và track_a
sys.path.append(str(Path(__file__).resolve().parent))

# Cấu hình môi trường trước khi import cấu hình gốc
os.environ["SECUREPI_OUT_NAME"] = "dataset_gpt4o_mini_track_a.jsonl"

# Đọc model gốc trước khi ghi đè
original_model = os.environ.get("SECUREPI_MODEL", "gemini-flash-lite-latest")

# Đặt SECUREPI_MODEL sang gpt-4o-mini
os.environ["SECUREPI_MODEL"] = "openai/gpt-4o-mini"

ROUTER_KEY = "sk-ffb64cc12a0d42c9-1votbf-2e2a017b"
ROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"

# Import các file core và track_a
import core.api
import track_a.main
import core.config

# Lưu lại hàm gọi gốc
original_call_gemini = core.api.call_gemini

fallback_triggered = False

# Hàm gọi API qua 9router (với cơ chế tự động fallback về Gemini gốc)
def call_gpt4o_mini(prompt, temperature=0.85):
    global fallback_triggered
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {ROUTER_KEY}"
    }
    body = {
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": False
    }
    data = json.dumps(body).encode("utf-8")
    
    # 1. Thử gọi GPT-4o-Mini qua 9router
    try:
        req = urllib.request.Request(ROUTER_URL, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode("utf-8"))
        if j and "choices" in j:
            return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"\n      [LỖI] Không thể gọi GPT-4o-mini qua 9Router: {e}")
        
    # 2. Cơ chế Fallback về Gemini gốc
    if not fallback_triggered:
        print(f"      -> Kích hoạt chế độ fallback dùng Gemini ({original_model})...")
        fallback_triggered = True
        
    # Phục hồi model gốc cho tất cả cấu hình
    core.config.MODEL = original_model
    core.api.MODEL = original_model
    track_a.main.MODEL = original_model
    
    return original_call_gemini(prompt, temperature=temperature)

# Thay thế hàm gọi API bằng hàm gpt-4o-mini + fallback
core.api.call_gemini = call_gpt4o_mini
track_a.main.call_gemini = call_gpt4o_mini

# Ép hệ thống dùng model gpt-4o-mini trong phần ghi nhận metadata
core.config.MODEL = "openai/gpt-4o-mini"
core.api.MODEL = "openai/gpt-4o-mini"
track_a.main.MODEL = "openai/gpt-4o-mini"

# Monkeypatch hàm generate_one để cập nhật metadata model khi dùng fallback
original_generate_one = track_a.main.generate_one

def patched_generate_one(profile, form_meta, register=None, outline=None, tagged_fields=None, target_spi=None):
    global fallback_triggered
    fallback_triggered = False  # Reset trạng thái cho mỗi bản ghi
    
    # Chạy hàm gốc
    rec = original_generate_one(profile, form_meta, register, outline, tagged_fields, target_spi)
    
    # Nếu trong quá trình sinh có dùng fallback
    if fallback_triggered:
        rec["model"] = f"{original_model} (fallback)"
        
    # Đảm bảo reset lại cấu hình sang gpt-4o-mini sau khi xong 1 bản ghi
    core.config.MODEL = "openai/gpt-4o-mini"
    core.api.MODEL = "openai/gpt-4o-mini"
    track_a.main.MODEL = "openai/gpt-4o-mini"
    
    return rec

track_a.main.generate_one = patched_generate_one

if __name__ == "__main__":
    n = 2
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        n = int(sys.argv[1])
        
    print(f"Bắt đầu chạy thử nghiệm Pipeline Track A bằng GPT-4o-Mini...")
    print(f"API Endpoint: {ROUTER_URL}")
    print(f"API Key: {ROUTER_KEY}")
    print(f"Số lượng bản ghi cần tạo: {n}")
    print(f"File output mục tiêu: 3-7-2026/output/dataset_gpt4o_mini_track_a.jsonl")
    print("=" * 60)
    
    track_a.main.run_batch(n)
