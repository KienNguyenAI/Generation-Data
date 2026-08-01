# -*- coding: utf-8 -*-
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "output"
MODEL = os.environ.get("SECUREPI_MODEL", "nvidia/deepseek-ai/deepseek-v4-flash")

# ---------------- load env ----------------
def load_env(p):
    out = {}
    if not p.exists():
        return out
    for l in p.read_text(encoding="utf-8").splitlines():
        if "=" not in l or l.strip().startswith("#"):
            continue
        i = l.index("=")
        out[l[:i].strip()] = l[i+1:].strip().strip('"').strip("'")
    return out

ENV = {}
for path in [ROOT / ".env", ROOT / ".evn", ROOT.parent / ".env", ROOT.parent / ".evn"]:
    ENV.update(load_env(path))

KEY = (ENV.get("api") or ENV.get("GEMINI_API") or ENV.get("GEMINI_API_KEY") or 
       ENV.get("Gemini_API_Key") or ENV.get("GOOGLE_API_KEY") or 
       os.environ.get("api") or os.environ.get("GEMINI_API") or os.environ.get("GEMINI_API_KEY"))


if not KEY:
    print("Không tìm thấy api (9router) hoặc GEMINI_API hoặc Gemini_API_Key trong .env/.evn")
    sys.exit(1)

# ---------------- load schema / catalog ----------------
SCHEMA = json.loads((DATA / "pii_schema.json").read_text(encoding="utf-8"))
CATALOG = json.loads((DATA / "scenario_catalog.json").read_text(encoding="utf-8"))
FIELDS = {f["field"]: f for f in SCHEMA["fields"]}
SENS = {f["field"]: f["sensitivity"] for f in SCHEMA["fields"]}

# Mechanism definition
MECHANISM = {
    "full_name": "verbatim", "address": "verbatim",
    "dob": "date",
    "cccd": "verbatim", "phone": "verbatim", "email": "verbatim", "bank_account": "verbatim",
    "passport_number": "verbatim", "driver_license": "verbatim", "vehicle_plate": "verbatim",
    "tax_code": "verbatim", "social_insurance_no": "verbatim", "health_insurance_no": "verbatim",
    "family_name": "name_component", "middle_name": "name_component", "given_name": "name_component",
    "ethnicity": "cue_context", "religion": "cue_context", "political_view": "cue_context",
    "gender": "cue_context", "marital_status": "cue_context", "nationality": "cue_context",
    "name_alias": "anchor_tag", "family_relations": "anchor_tag", "health_status": "anchor_tag",
    "criminal_record": "anchor_tag", "location_data": "anchor_tag", "private_life": "anchor_tag",
    "biometric": "anchor_tag", "behavioral_data": "anchor_tag",
    "sexual_orientation": "anchor_tag", "eid_credentials": "anchor_tag",
}

CUE_WORDS = {
    "political_view": ["chính trị", "quan điểm", "đảng", "đoàn", "tư tưởng", "thành phần", "đảng tịch", "đại diện", "quần chúng", "đảng viên", "đoàn viên", "dự bị"],
    "religion": ["tôn giáo", "đạo", "tín ngưỡng", "phật", "chúa", "thờ"],
    "ethnicity": ["dân tộc", "đồng bào", "người", "kinh", "tày", "thái", "mường", "khmer"],
    "gender": ["giới tính", "nam", "nữ"],
    "marital_status": ["hôn nhân", "kết hôn", "độc thân", "ly hôn", "góa", "vợ", "chồng", "tình trạng"],
    "nationality": ["quốc tịch", "công dân", "việt nam"]
}

BIRTH_CUES = ["sinh ngày", "ngày sinh", "năm sinh"]
CRITICAL = {"full_name", "cccd", "phone", "dob", "address"}

# Profile loader helper
def load_profiles(limit=50):
    out = []
    for l in (DATA / "profile_bank.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            out.append(json.loads(l))
        if len(out) >= limit:
            break
    return out

pfields = lambda p: p.get("fields", p)
SENTINEL = "[[LLM_GENERATE]]"

# ---------------- form metadata cache ----------------
FORM_METADATA_CACHE = None

def load_all_form_metadata():
    global FORM_METADATA_CACHE
    if FORM_METADATA_CACHE is not None:
        return
    p = DATA / "form.json"
    if not p.exists():
        FORM_METADATA_CACHE = {}
        return
    print("   (Đang nạp thông tin tham chiếu từ form.json...)")
    try:
        domains = {}
        p_domains = DATA / "form_domains.json"
        if p_domains.exists():
            try:
                with open(p_domains, "r", encoding="utf-8") as fd:
                    domains = json.load(fd)
            except Exception as ed:
                print(f"   Lỗi nạp form_domains.json: {ed}")
                
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        FORM_METADATA_CACHE = {
            item["template_id"]: {
                "template_id": item.get("template_id"),
                "record_type": item.get("record_type"),
                "agency": item.get("agency"),
                "source_url": item.get("source_url"),
                "domain": domains.get(item.get("template_id"), "economy_tech_other"),
                "form_raw_text": "\n\n".join([
                    f["form_raw_text"] for f in item.get("attached_forms", [])
                    if f.get("form_raw_text")
                ])
            }
            for item in data if "template_id" in item
        }
        print(f"   (Đã nạp xong metadata của {len(FORM_METADATA_CACHE)} biểu mẫu)")
    except Exception as e:
        print(f"   Lỗi nạp metadata từ form.json: {e}")
        FORM_METADATA_CACHE = {}

def get_form_metadata(template_id):
    load_all_form_metadata()
    return FORM_METADATA_CACHE.get(template_id, {})

def get_all_form_metadata():
    load_all_form_metadata()
    return FORM_METADATA_CACHE
