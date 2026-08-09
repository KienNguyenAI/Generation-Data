# -*- coding: utf-8 -*-
import json
import re
import time
import os
import unicodedata
import urllib.request
import urllib.error
from core.config import MODEL, KEY, ENV

NFC = lambda s: unicodedata.normalize("NFC", s)

def call_gemini(prompt, temperature=0.85):
    direct_openrouter = os.environ.get("SECUREPI_DIRECT_OPENROUTER") == "1"
    if direct_openrouter:
        custom_url = os.environ.get("SECUREPI_CUSTOM_URL")
        if custom_url:
            url = custom_url
        else:
            url = "https://openrouter.ai/api/v1/chat/completions"
        key_to_use = ENV.get("DEEPSEEKV4FLASH")
        print(f"      (Đang gọi trực tiếp API từ .env: {MODEL} qua {url}...)")
    else:
        url = "http://127.0.0.1:20128/v1/chat/completions"
        key_to_use = KEY
        print(f"      (Đang gọi model: {MODEL} qua 9Router...)")
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {key_to_use}"
    }
    
    # 9router gọi local thường nhanh hơn, giảm sleep xuống 1s để tối ưu tốc độ
    time.sleep(1)
    
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "stream": False
    }
    data = json.dumps(body).encode("utf-8")
    j = None
    
    api_timeout = 120
    for attempt in range(8):                     # tự động thử lại nếu gặp lỗi tạm thời (HTTP/Timeout/Connection)
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=api_timeout) as resp:
                raw_str = resp.read().decode("utf-8")
                if "data: [DONE]" in raw_str:
                    raw_str = raw_str.split("data: [DONE]")[0].strip()
                j = json.loads(raw_str)
            if j and "choices" in j and len(j["choices"]) > 0:
                choice = j["choices"][0]
                content = choice.get("message", {}).get("content")
                finish_reason = choice.get("finish_reason")
                if content is None or finish_reason == "length":
                    reason = finish_reason or "unknown"
                    raise ValueError(f"API empty/truncated (finish_reason: {reason})")
            break
        except Exception as e:
            is_retryable = False
            err_msg = ""
            
            if isinstance(e, urllib.error.HTTPError):
                detail = e.read().decode("utf-8", "ignore")[:150]
                err_msg = f"HTTP {e.code}: {detail}"
                if e.code == 429 or (500 <= e.code < 600):
                    is_retryable = True
            elif isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError)) or "timed out" in str(e).lower():
                err_msg = f"Timeout/Lỗi kết nối: {str(e)[:150]}"
                is_retryable = True
            elif isinstance(e, ValueError) and "API empty/truncated" in str(e):
                err_msg = str(e)[:150]
                is_retryable = True
            else:
                err_msg = f"Lỗi khác: {str(e)[:150]}"
            
            if is_retryable and attempt < 7:
                sleep_time = min(8, 2 + attempt)
                print(f"      ({err_msg} - Thử lại {attempt+1}/8 sau {sleep_time}s...)")
                time.sleep(sleep_time)
                continue
            raise RuntimeError(f"API failed after multiple retries. Last error: {err_msg}")
            
    if not j or "choices" not in j:
        err_msg = j.get("error", {}).get("message", "Unknown error") if j else "Empty response"
        raise RuntimeError(f"API Error: {err_msg}")
        
    choice = j["choices"][0]
    content = choice.get("message", {}).get("content")
    if content is None:
        finish_reason = choice.get("finish_reason", "unknown")
        raise RuntimeError(f"API returned empty content. Finish reason: {finish_reason}. Response: {json.dumps(j, ensure_ascii=False)}")
        
    return content.strip()

def clean_output(t):
    # Loại bỏ khối suy nghĩ <think>...</think> của các dòng reasoning models
    t = re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL)
    if "<think>" in t:
        t = t.split("<think>")[0]
        
    t = re.sub(r"```[a-zA-Z]*\n?", "", t)
    t = t.replace("«", "").replace("»", "")   # LLM (nhất là flash-lite) hay chép dấu phân định « » -> bỏ
    return NFC(t.strip())
