# -*- coding: utf-8 -*-
import json
import re
import time
import unicodedata
import urllib.request
import urllib.error
from core.config import MODEL, KEY

NFC = lambda s: unicodedata.normalize("NFC", s)

def call_gemini(prompt, temperature=0.85):
    # Cổng gọi 9router cục bộ (Tương thích chuẩn OpenAI Chat Completions)
    url = "http://127.0.0.1:20128/v1/chat/completions"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {KEY}"
    }
    
    # 9router gọi local thường nhanh hơn, giảm sleep xuống 1s để tối ưu tốc độ
    time.sleep(1)
    
    print(f"      (Đang gọi model: {MODEL} qua 9Router...)")
    
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": False
    }
    data = json.dumps(body).encode("utf-8")
    j = None
    for attempt in range(4):                     # tự động thử lại nếu lỗi 503/500
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                j = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:200]
            if e.code in (500, 503) and attempt < 3:
                print(f"      (HTTP {e.code} tạm thời, thử lại sau {2*(attempt+1)}s...)")
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(f"API HTTP {e.code}: {detail}")
    
    if not j or "choices" not in j:
        err_msg = j.get("error", {}).get("message", "Unknown error") if j else "Empty response"
        raise RuntimeError(f"API Error: {err_msg}")
        
    return j["choices"][0]["message"]["content"].strip()

def clean_output(t):
    t = re.sub(r"```[a-zA-Z]*\n?", "", t)
    t = t.replace("«", "").replace("»", "")   # LLM (nhất là flash-lite) hay chép dấu phân định « » -> bỏ
    return NFC(t.strip())
