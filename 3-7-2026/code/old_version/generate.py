#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecurePrep — BỘ SINH THẬT (Track B, scenario-first) bằng Gemini — bản Python.
Chạy:  python Generation-Data/generate.py
Cần:   f:/NCKH/project/.env chứa GEMINI_API=...   (tự nạp, KHÔNG in ra)
Chỉ dùng THƯ VIỆN CHUẨN (json, re, urllib, unicodedata) — không cần pip install gì.
"""
import json, re, os, sys, time, unicodedata, urllib.request, urllib.error, random
from pathlib import Path

# Windows console mặc định cp1252 -> ép UTF-8 để in tiếng Việt không lỗi
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "Data"
OUT = ROOT / "output"
MODEL = os.environ.get("SECUREPI_MODEL", "gemini-flash-lite-latest")  # sạch + rảnh; Gemma-4 hay 500/ra rác tiếng Anh. Ép Gemma: SECUREPI_MODEL=gemma-4-26b-a4b-it
NFC = lambda s: unicodedata.normalize("NFC", s)

# ---------------- cấu hình / dữ liệu ----------------
def load_env(p):
    out = {}
    if not p.exists(): return out
    for l in p.read_text(encoding="utf-8").splitlines():
        if "=" not in l or l.strip().startswith("#"): continue
        i = l.index("="); out[l[:i].strip()] = l[i+1:].strip().strip('"').strip("'")
    return out

# Thử tải từ các đường dẫn và tên file khác nhau (.env, .evn ở ROOT hoặc thư mục cha)
ENV = {}
for path in [ROOT / ".env", ROOT / ".evn", ROOT.parent / ".env", ROOT.parent / ".evn"]:
    ENV.update(load_env(path))

KEY = (ENV.get("GEMINI_API") or ENV.get("GEMINI_API_KEY") or 
       ENV.get("Gemini_API_Key") or ENV.get("GOOGLE_API_KEY") or 
       os.environ.get("GEMINI_API") or os.environ.get("GEMINI_API_KEY"))
if not KEY:
    print("Không tìm thấy GEMINI_API hoặc Gemini_API_Key trong .env/.evn"); sys.exit(1)

SCHEMA = json.loads((DATA / "pii_schema.json").read_text(encoding="utf-8"))
CATALOG = json.loads((DATA / "scenario_catalog.json").read_text(encoding="utf-8"))
FIELDS = {f["field"]: f for f in SCHEMA["fields"]}
SENS = {f["field"]: f["sensitivity"] for f in SCHEMA["fields"]}

def load_profiles(limit=50):
    out = []
    for l in (DATA / "profile_bank.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip(): out.append(json.loads(l))
        if len(out) >= limit: break
    return out

pfields = lambda p: p.get("fields", p)
SENTINEL = "[[LLM_GENERATE]]"
CUE_WORDS = {
    "political_view": ["chính trị", "quan điểm", "đảng", "đoàn", "tư tưởng", "thành phần", "đảng tịch", "đại diện", "quần chúng", "đảng viên", "đoàn viên", "dự bị"],
    "religion": ["tôn giáo", "đạo", "tín ngưỡng", "phật", "chúa", "thờ"],
    "ethnicity": ["dân tộc", "đồng bào", "người", "kinh", "tày", "thái", "mường", "khmer"],
    "gender": ["giới tính", "nam", "nữ"],
    "marital_status": ["hôn nhân", "kết hôn", "độc thân", "ly hôn", "góa", "vợ", "chồng", "tình trạng"],
    "nationality": ["quốc tịch", "công dân", "việt nam"]
}

# ---------------- ANNOTATE 3 lớp (đã gồm mọi fix) ----------------
BL, BR = r"(?<!\w)", r"(?!\w)"
MECHANISM = {
    "full_name": "verbatim", "address": "verbatim",
    "dob": "date",   # date có cue "sinh" -> tránh gán ngày ký/ngày làm đơn (cùng bề mặt, khác vai trò)
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
NAME_CUES = ["họ và tên", "họ tên", "người làm đơn", "người khai", "người ký", "ký tên", "tên:",
             # ngữ cảnh văn xuôi/chữ ký (fix given_name bị bỏ nhãn trong prose):
             "tên gọi", "thường gọi", "được gọi", "gọi là", "tôi là", "tôi tên", "trân trọng", "kính đơn", "ký:", "người viết đơn",
             # nhãn dẫn cho HỌ và CHỮ ĐỆM (family_name / middle_name đứng riêng):
             "mang họ", "họ là", "họ của", "họ:", "chữ đệm", "tên đệm", "chữ lót"]
BIRTH_CUES = ["sinh ngày", "ngày sinh", "năm sinh"]  # nhãn dẫn cho dob (loại ngày ký/ngày văn bản)

def _is_own_line(text, a, b):
    """span [a,b] nằm trên MỘT DÒNG chỉ chứa đúng tên (chữ ký trần)."""
    ls = text.rfind("\n", 0, a); ls = 0 if ls < 0 else ls + 1
    le = text.find("\n", b); le = len(text) if le < 0 else le
    return text[ls:le].strip() == text[a:b]

def _guarded(text, surface):
    if not surface: return []
    return [(m.start(), m.start() + len(m.group(0))) for m in re.finditer(BL + re.escape(surface) + BR, text, re.IGNORECASE)]

def match_verbatim(text, surfaces):
    out = []
    for s in surfaces: out += _guarded(text, s)
    return list(dict.fromkeys(out))

def match_cue_context(text, surfaces, cue_words, max_back=80):
    # cửa sổ = từ RANH GIỚI CÂU gần nhất (. ; \n ! ?) trước match, cap max_back ký tự
    low = text.lower(); cues = [c.lower() for c in (cue_words or [])]; out = []
    for s in surfaces:
        for (a, b) in _guarded(text, s):
            lo = max(0, a - max_back); seg = text[lo:a]
            rel = max(seg.rfind("."), seg.rfind(";"), seg.rfind("\n"), seg.rfind("!"), seg.rfind("?"))
            pre = low[(lo + rel + 1) if rel >= 0 else lo:a]
            if any(c in pre for c in cues): out.append((a, b))
    return list(dict.fromkeys(out))

def _ov(a, b): return a[0] < b[1] and b[0] < a[1]

def match_name_component(text, surfaces, claimed, max_back=30):
    low = text.lower(); out = []
    claimed_sp = [(c["start"], c["end"]) for c in claimed]
    for s in surfaces:
        for sp in _guarded(text, s):
            if any(_ov(sp, c) for c in claimed_sp): continue
            
            # Proper name component must be capitalized or uppercase in Vietnamese
            matched_val = text[sp[0]:sp[1]]
            if matched_val and not matched_val[0].isupper():
                continue
                
            pre = low[max(0, sp[0] - max_back):sp[0]]
            # nhãn dẫn: cue có sẵn HOẶC đại từ xưng hô hoặc mẫu tổng quát "tên … là/:"
            has_cue = (
                any(c in pre for c in NAME_CUES) or 
                re.search(r"tên[^.\n]{0,20}(là|:)", pre) is not None or
                any(re.search(r"\b" + re.escape(h) + r"\b", pre) for h in ["anh", "chị", "ông", "bà", "cháu", "cô", "chú", "bác", "bạn", "đồng chí"])
            )
            if has_cue or _is_own_line(text, sp[0], sp[1]): out.append(sp)   # nhãn dẫn HOẶC chữ ký trần
    return list(dict.fromkeys(out))

# dung sai thẻ đóng: chấp nhận ⟦/field⟧ (chuẩn) HOẶC ⟧ trần (LLM hay đóng thiếu)
_OPEN, _CLOSE = "⟦", "⟧"

def extract_anchor_tags(tagged, anchor_fields=None):
    """1-pass, dung sai cao (cho cả model yếu), hỗ trợ thẻ lồng nhau (nested tags):
    - ⟦field⟧nội dung⟦/field⟧  (chuẩn)
    - ⟦field⟧nội dung⟧          (đóng thiếu)
    - ⟦nội dung⟧                (generic, KHÔNG có tên field) -> gán theo hàng đợi anchor_fields
    offset tính trong CÙNG một lượt -> luôn nhất quán.
    """
    tagged = NFC(tagged)
    fields_q = list(anchor_fields or [])
    clean = ""
    spans = []
    stack = []
    i = 0
    k = 0
    n = len(tagged)
    
    while i < n:
        if tagged[i] == _OPEN:
            j = tagged.find(_CLOSE, i + 1)
            if j != -1:
                tag_content = tagged[i + 1:j]
                
                # Case 1: Close tag, e.g. ⟦/field_name⟧
                if tag_content.startswith('/'):
                    field = tag_content[1:]
                    match_idx = -1
                    for idx in range(len(stack) - 1, -1, -1):
                        if stack[idx][0] == field:
                            match_idx = idx
                            break
                    if match_idx != -1:
                        fld, start = stack.pop(match_idx)
                        spans.append({
                            "field": fld,
                            "label": SENS.get(fld, fld),
                            "start": start,
                            "end": len(clean),
                            "value": clean[start:],
                            "via": "anchor_tag"
                        })
                    i = j + 1
                    continue
                
                # Case 2: Open tag, e.g. ⟦field_name⟧
                elif re.fullmatch(r"[a-zA-Z_]+", tag_content):
                    stack.append((tag_content, len(clean)))
                    i = j + 1
                    continue
                
                # Case 3: Generic tag, e.g. ⟦giá_trị_nhạy_cảm⟧
                else:
                    fld = fields_q[min(k, len(fields_q) - 1)] if fields_q else None
                    start = len(clean)
                    clean += tag_content
                    if fld:
                        spans.append({
                            "field": fld,
                            "label": SENS.get(fld, fld),
                            "start": start,
                            "end": len(clean),
                            "value": tag_content,
                            "via": "anchor_tag"
                        })
                        k += 1
                    i = j + 1
                    continue
                    
        clean += tagged[i]
        i += 1
        
    while stack:
        fld, start = stack.pop()
        spans.append({
            "field": fld,
            "label": SENS.get(fld, fld),
            "start": start,
            "end": len(clean),
            "value": clean[start:],
            "via": "anchor_tag"
        })
        
    ok = (_OPEN not in clean) and (_CLOSE not in clean)
    return {"clean_text": clean, "spans": spans, "ok": ok}

def resolve_overlaps(spans, pre=None):
    accepted = list(pre or [])
    for s in sorted(spans, key=lambda x: -(x["end"] - x["start"])):
        if not any(_ov((s["start"], s["end"]), (a["start"], a["end"])) for a in accepted):
            accepted.append(s)
    return sorted(accepted, key=lambda x: x["start"])

_mech = lambda field: MECHANISM.get(field, "verbatim")
def _tag(sp, e, via):
    return {"start": sp[0], "end": sp[1], "field": e["field"],
            "label": e.get("label", e["field"]), "subject_id": e.get("subject_id"),
            "subject": e.get("subject"), "via": via}

def annotate(clean_text, manifest, anchor_spans=None):
    text = NFC(clean_text); pre = [dict(s) for s in (anchor_spans or [])]
    verb, cue = [], []
    for e in manifest:
        m = _mech(e["field"])
        if m == "verbatim":
            for sp in match_verbatim(text, e.get("surfaces", [])): verb.append(_tag(sp, e, "verbatim"))
        elif m == "cue_context":
            for sp in match_cue_context(text, e.get("surfaces", []), e.get("cue_words")): cue.append(_tag(sp, e, "cue_context"))
        elif m == "date":   # dob cần nhãn "sinh"; ngày ký -> O
            for sp in match_cue_context(text, e.get("surfaces", []), e.get("cue_words") or BIRTH_CUES): cue.append(_tag(sp, e, "date"))
    claimed = resolve_overlaps(verb + cue, pre)
    namec = []
    for e in manifest:
        if _mech(e["field"]) == "name_component":
            for sp in match_name_component(text, e.get("surfaces", []), claimed): namec.append(_tag(sp, e, "name_component"))
            
    all_resolved = resolve_overlaps(verb + cue + namec, pre)
    
    dyn_family = next((e["surfaces"][0] for e in manifest if e["field"] == "family_name" and e.get("surfaces") and not e.get("subject")), "")
    dyn_middle = next((e["surfaces"][0] for e in manifest if e["field"] == "middle_name" and e.get("surfaces") and not e.get("subject")), "")
    dyn_given = next((e["surfaces"][0] for e in manifest if e["field"] == "given_name" and e.get("surfaces") and not e.get("subject")), "")
    
    final_spans = []
    for s in all_resolved:
        if s["field"] == "full_name":
            subj = s.get("subject")
            if subj:
                fam = next((e["surfaces"][0] for e in manifest if e["field"] == "family_name" and e.get("surfaces") and e.get("subject") == subj), "")
                mid = next((e["surfaces"][0] for e in manifest if e["field"] == "middle_name" and e.get("surfaces") and e.get("subject") == subj), "")
                giv = next((e["surfaces"][0] for e in manifest if e["field"] == "given_name" and e.get("surfaces") and e.get("subject") == subj), "")
            else:
                fam = dyn_family
                mid = dyn_middle
                giv = dyn_given
                
            span_text = text[s["start"]:s["end"]]
            for field, val in [("family_name", fam), ("middle_name", mid), ("given_name", giv)]:
                if not val:
                    continue
                match = re.search(r'\b' + re.escape(val) + r'\b', span_text, re.IGNORECASE)
                if match:
                    final_spans.append({
                        "start": s["start"] + match.start(),
                        "end": s["start"] + match.end(),
                        "field": field,
                        "label": s["label"],
                        "subject_id": s.get("subject_id"),
                        "subject": s.get("subject"),
                        "via": "name_component"
                    })
        else:
            final_spans.append(s)
            
    return sorted(final_spans, key=lambda x: x["start"])

# ---------------- REALIZE ----------------
def render_dob(v):
    v = v.strip()
    m = v.split("/")
    if len(m) == 3:
        day, month, year = m[0], m[1], m[2]
        day_s = day.zfill(2)
        month_s = month.zfill(2)
        return [
            v,
            f"{day_s}/{month_s}/{year}",
            f"{day_s}-{month_s}-{year}",
            f"{year}-{month_s}-{day_s}",
            f"{day} tháng {month} năm {year}",
            f"ngày {day} tháng {month} năm {year}",
            f"{day_s}.{month_s}.{year}"
        ]
    return [v]

def render_cccd(v):
    v = v.strip(); o = [v]
    if re.fullmatch(r"\d{12}", v):
        o.append(f"{v[0:4]} {v[4:8]} {v[8:12]}")
        o.append(f"{v[0:3]} {v[3:6]} {v[6:9]} {v[9:12]}")
        o.append(f"{v[0:3]}-{v[3:6]}-{v[6:9]}-{v[9:12]}")
    return o

def render_phone(v):
    v = v.strip(); o = [v]
    if re.fullmatch(r"\d{10}", v):
        o.append(f"{v[0:4]} {v[4:7]} {v[7:10]}")
        o.append(f"{v[0:4]}.{v[4:7]}.{v[7:10]}")
        o.append(f"+84 {v[1:4]} {v[4:7]} {v[7:10]}")
        o.append(f"+84{v[1:]}")
        o.append(f"({v[0:4]}) {v[4:7]} {v[7:10]}")
    return o

def render_full_name(v):
    v = v.strip(); o = [v]
    o.append(v.upper())
    parts = v.split()
    if len(parts) >= 2:
        o.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
    return list(dict.fromkeys(o))
def render_address(v):
    v = v.strip(); o = [v]
    for target in ["thành phố TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "TP.Hồ Chí Minh"]:
        if target in v:
            o.append(v.replace(target, "Hồ Chí Minh"))
            o.append(v.replace(target, "thành phố Hồ Chí Minh"))
            o.append(v.replace(target, "TP. Hồ Chí Minh"))
            o.append(v.replace(target, "TP.HCM"))
            o.append(v.replace(target, "TP HCM"))
    o = [re.sub(r"\s+", " ", s).strip() for s in o]
    return list(dict.fromkeys(o))

def render_political_view(v):
    v = v.strip()
    if v == "Quần chúng":
        return ["chưa vào Đảng", "chưa kết nạp Đảng", "không tham gia đảng phái", "chưa gia nhập Đảng", "quần chúng"]
    elif v == "Không" or v == "Không khai báo quan điểm chính trị":
        return ["không tham gia đảng phái", "chưa vào Đảng", "không có đảng tịch"]
    return [v]

def render_religion(v):
    v = v.strip()
    if v == "Không" or v == "Không tôn giáo":
        return ["không theo tôn giáo nào", "không theo đạo", "không có tôn giáo", "không tôn giáo"]
    return [v]


def _stable_hash(s):
    h = 2166136261
    for ch in s: h = ((h ^ ord(ch)) * 16777619) % (2**32)
    return h

def generate_fallback_value(field, seed_str):
    h = _stable_hash(seed_str)
    def rand_digit(offset):
        return str((h + offset) * 179426549 % 10)
    
    if field == "cccd":
        return "".join(rand_digit(i) for i in range(12))
    elif field == "phone":
        return "09" + "".join(rand_digit(i) for i in range(8))
    elif field == "email":
        return f"user_{h % 90000 + 10000}@gmail.com"
    elif field == "tax_code":
        return "".join(rand_digit(i) for i in range(10))
    elif field == "social_insurance_no":
        return "".join(rand_digit(i) for i in range(10))
    elif field == "health_insurance_no":
        prefixes = ["DN", "GD", "HC", "HS", "CH", "TE"]
        prefix = prefixes[h % len(prefixes)]
        digits = "".join(rand_digit(i) for i in range(13))
        return prefix + digits
    elif field == "passport_number":
        prefixes = ["B", "C", "D"]
        prefix = prefixes[h % len(prefixes)]
        digits = "".join(rand_digit(i) for i in range(7))
        return prefix + digits
    elif field == "driver_license":
        return "".join(rand_digit(i) for i in range(12))
    elif field == "vehicle_plate":
        prov = ["29", "30", "59", "43", "75", "37"]
        p = prov[h % len(prov)]
        let = ["A", "B", "C", "D", "F", "H", "K"]
        l = let[(h >> 4) % len(let)]
        digits = "".join(rand_digit(i + 8) for i in range(5))
        return f"{p}{l}-{digits}"
    elif field == "bank_account":
        return "".join(rand_digit(i) for i in range(12))
    return ""

def split_vietnamese_name(full_name):
    parts = full_name.strip().split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return "", "", parts[0]
    if len(parts) == 2:
        return parts[0], "", parts[1]
    
    family = parts[0]
    given = parts[-1]
    middle = " ".join(parts[1:-1])
    return family, middle, given

def build_manifest(profile, scenario):
    fl = pfields(profile)
    want = (set(scenario.get("cooccur_fields", [])) | set(scenario.get("spi_targets", []))) - {"political_view"}
    name_parts = {"family_name", "middle_name", "given_name"}
    
    full_name_val = fl.get("full_name", "")
    dyn_family, dyn_middle, dyn_given = split_vietnamese_name(full_name_val) if full_name_val else ("", "", "")
    
    manifest = []
    
    for field in MECHANISM:
        if not (field in want or (field in name_parts and "full_name" in want)): continue
        
        if field == "family_name" and dyn_family:
            val = dyn_family
        elif field == "middle_name" and dyn_middle:
            val = dyn_middle
        elif field == "given_name" and dyn_given:
            val = dyn_given
        else:
            raw = fl.get(field)
            val = "" if raw is None else str(raw).strip()
        if not val:
            val = generate_fallback_value(field, f"{profile.get('profile_id')}|{scenario['id']}|{field}")
            if not val: continue
            
        m = MECHANISM[field]
        if val == SENTINEL: m = "anchor_tag"   # sentinel -> LLM SINH + bọc thẻ, KHÔNG verbatim
        label = SENS.get(field, "PII"); name_vi = (FIELDS.get(field) or {}).get("name_vi", field)
        if m == "verbatim":
            if field == "cccd":
                surfaces = render_cccd(val)
            elif field == "phone":
                surfaces = render_phone(val)
            elif field == "address":
                surfaces = render_address(val)
            elif field == "full_name":
                surfaces = render_full_name(val)
            else:
                surfaces = [val]
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces})
        elif m == "date":
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": render_dob(val), "cue_words": BIRTH_CUES})
        elif m == "name_component":
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": [val]})
        elif m == "cue_context":
            surfaces = [val]
            if field == "political_view":
                surfaces = render_political_view(val)
            elif field == "religion":
                surfaces = render_religion(val)
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces, "cue_words": CUE_WORDS.get(field, [])})
        elif m == "anchor_tag":
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": [], "anchor": True, "seed_value": None if val == SENTINEL else val})
            
    for e in manifest:
        e["derived"] = (e["field"] in name_parts and "full_name" in want and e["field"] not in want)
    return manifest

# ---------------- ATTRIBUTES bổ sung (PrivaSIS-style, Constraint-First) ----------------

def realize_supplemental(profile, scenario, profiles, base_seed):
    """Sinh các attribute RIÊNG của kịch bản (code kiểm soát -> LLM không phải bịa).
    Trả (extra_manifest, prompt_lines, distractors).
    - org         -> nhãn O (không annotate), cấp cho prompt.
    - doc_code    -> nhãn O + distractor (12 số cạnh CCCD, vấn đề 4).
    - person      -> MƯỢN tên/địa chỉ 1 profile khác trong bank -> nhãn thật (PII đa chủ thể).
    """
    sa = scenario.get("supplemental_attributes", [])
    extra, prompt_lines, distractors = [], [], []
    for a in sa:
        seed = _stable_hash(base_seed + "|" + a.get("key", ""))
        kind = a.get("kind")
        if kind == "org":
            pool = a.get("pool") or ["Ủy ban nhân dân phường"]
            val = pool[seed % len(pool)]
            prompt_lines.append(f"   - Cơ quan/nơi nhận: «{val}» (dùng đúng, không bịa cơ quan khác)")
        elif kind == "doc_code":
            fmt = a.get("format", "num12")
            val = "".join(str((seed >> (i * 3)) % 10) for i in range(12)) if fmt == "num12" else f"{seed % 9000 + 1000}/QĐ"
            prompt_lines.append(f"   - {a.get('desc','Mã hồ sơ/số văn bản')}: «{val}» (là MÃ GIẤY TỜ, KHÔNG phải số định danh cá nhân)")
            distractors.append({"key": a.get("key"), "value": val, "label": "O"})
        elif kind == "person":
            rp = profiles[seed % len(profiles)]
            if rp.get("profile_id") == profile.get("profile_id"):
                rp = profiles[(seed + 1) % len(profiles)]
            fl2 = pfields(rp)
            rel = a.get("relation", "người thân")
            
            # Lấy danh sách các trường cần trích xuất (mặc định là full_name)
            fields = list(a.get("fields", ["full_name"]))
            has_fullname = "full_name" in fields
            if has_fullname:
                for fld in ["family_name", "middle_name", "given_name"]:
                    if fld not in fields:
                        fields.append(fld)
            if a.get("with_address") and "address" not in fields:
                fields.append("address")
                
            sub_lines = []
            full_name_val2 = fl2.get("full_name", "")
            dyn_family2, dyn_middle2, dyn_given2 = split_vietnamese_name(full_name_val2) if full_name_val2 else ("", "", "")
            
            for f in fields:
                is_derived = (f in ["family_name", "middle_name", "given_name"] and has_fullname and f not in a.get("fields", []))
                
                if f == "family_name" and dyn_family2:
                    val = dyn_family2
                elif f == "middle_name" and dyn_middle2:
                    val = dyn_middle2
                elif f == "given_name" and dyn_given2:
                    val = dyn_given2
                else:
                    val = str(fl2.get(f, "")).strip()
                if not val:
                    continue
                label = SENS.get(f, "PII")
                name_vi = (FIELDS.get(f) or {}).get("name_vi", f)
                
                # Biến thể định dạng (cccd, phone, dob...)
                if f == "cccd":
                    surfaces = render_cccd(val)
                elif f == "phone":
                    surfaces = render_phone(val)
                elif f == "dob":
                    surfaces = render_dob(val)
                elif f == "address":
                    surfaces = render_address(val)
                elif f == "political_view":
                    surfaces = render_political_view(val)
                elif f == "religion":
                    surfaces = render_religion(val)
                elif f == "full_name":
                    surfaces = render_full_name(val)
                else:
                    surfaces = [val]
                
                extra.append({
                    "field": f, "label": label, "name_vi": f"{name_vi} của {rel}",
                    "mechanism": "date" if f == "dob" else "verbatim",
                    "surfaces": surfaces, "subject": rel, "derived": is_derived
                })
                
                # Thêm vào mô tả của prompt
                if not is_derived:
                    sub_lines.append(f"{name_vi}: «{surfaces[0]}»")
                
            if sub_lines:
                prompt_lines.append(f"   - Nhân vật {rel}: " + ", ".join(sub_lines) + " (dùng đúng, KHÔNG tự ý thay đổi hay bịa)")
    return extra, prompt_lines, distractors

# ---------------- PROMPT ----------------
def build_outline_prompt(scenario, manifest, supplements=None):
    # Tóm tắt các trường sẽ cần xuất hiện để LLM lên dàn ý
    fields_desc = []
    for e in manifest:
        if e.get("derived"): continue
        if e.get("anchor"):
            fields_desc.append(f"   - {e['name_vi']} (loại nhạy cảm, cần viết tự nhiên và bọc thẻ ⟦{e['field']}⟧)")
        else:
            fields_desc.append(f"   - {e['name_vi']} (loại thông tin định danh cố định)")
    fields_desc_str = "\n".join(fields_desc)
    
    supp_desc = []
    if supplements:
        for s in supplements:
            clean_s = re.sub(r'«[^»]+»', '[giá trị cụ thể]', s)
            supp_desc.append(clean_s)
    supp_desc_str = "\n".join(supp_desc) if supp_desc else "   (không có)"
    
    register = scenario.get("register", "administrative")
    if register == "dialogue":
        persona = "Bạn là người biên soạn kịch bản hội thoại/cuộc trò chuyện tiếng Việt tự nhiên (ví dụ: cuộc trao đổi giữa bác sĩ và bệnh nhân, tư vấn viên và khách hàng, hoặc giữa hai người thân/bạn bè)."
        task_desc = "xác định bối cảnh cuộc trò chuyện và lập dàn ý chi tiết (Bước 1 & 2) cho cuộc hội thoại"
        rule_outline = "Liệt kê cấu trúc các lượt nói/chủ đề trao đổi chính giữa các nhân vật (ví dụ: 1. Chào hỏi và khai thác lý do, 2. Trao đổi chi tiết về tình trạng/hoàn cảnh, 3. Kết luận và giải pháp)."
    elif register == "third_person":
        persona = "Bạn là một điều tra viên, chuyên viên xác minh hoặc người quan sát độc lập ghi nhận thông tin từ góc nhìn thứ ba."
        task_desc = "xác định mục đích báo cáo và lập dàn ý chi tiết (Bước 1 & 2) cho một văn bản báo cáo/xác minh từ góc nhìn thứ ba"
        rule_outline = "Liệt kê cấu trúc 3 phần (Mở đầu ghi nhận sự việc, Thân bài tường thuật/xác minh chi tiết về đối tượng, Kết luận/Đề xuất). Tuyệt đối cấm sử dụng ngôi thứ nhất 'tôi', phải dùng ngôi thứ ba (ví dụ: 'ông Nguyễn Bảo Long', 'chủ thể')."
    else:
        persona = "Bạn là một chuyên gia soạn thảo văn bản hành chính và pháp lý tại Việt Nam."
        task_desc = "xác định mục đích viết đơn và lập dàn ý chi tiết (Bước 1 & 2) cho một văn bản hành chính hoặc đời sống"
        rule_outline = "Liệt kê cấu trúc 3 phần (Mở bài, Thân bài, Kết bài). Trong đó phần Thân bài phải nêu rõ 2 - 3 ý chính sẽ dùng để trình bày chi diện hoàn cảnh và đề xuất nhằm thuyết phục người đọc."

    return f"""{persona}
Nhiệm vụ của bạn là {task_desc} dựa trên thông tin sau:
- Chủ đề kịch bản: "{scenario['title']}"
- Lý do/Bối cảnh xuất hiện văn bản: {scenario.get('disclosure_reason', '')}
- Phong cách ngôn ngữ: {register}

Các thông tin nhân thân và nghiệp vụ bắt buộc phải tích hợp sau này:
{fields_desc_str}
Thông tin bổ sung bắt buộc:
{supp_desc_str}

Yêu cầu thực hiện:
1. Xác định mục đích và giới hạn (Bước 1): Xác định loại văn bản/cuộc trò chuyện cụ thể phù hợp nhất. Xác định văn phong tự nhiên, phù hợp bối cảnh.
2. Lập dàn ý nhanh (Bước 2): {rule_outline}

Hãy trả về kết quả dưới dạng Markdown phân cấp rõ ràng (chỉ trả về dàn ý, tuyệt đối chưa viết nội dung chi tiết của văn bản/cuộc trò chuyện)."""

def build_draft_prompt(scenario, manifest, supplements, outline):
    verb = [f"   - {e['name_vi']}: «{e.get('prompt_surface') or e['surfaces'][0]}»" for e in manifest if e["mechanism"] != "anchor_tag" and e["surfaces"] and not e.get("derived")]
    anchors = []
    for e in manifest:
        if e.get("anchor"):
            how = f'viết lại tự nhiên đúng ý: "{e["seed_value"]}"' if e.get("seed_value") else "tự viết nội dung hợp bối cảnh"
            anchors.append(f"   - {e['name_vi']} ({how}) → bọc: ⟦{e['field']}⟧nội dung⟦/{e['field']}⟧")
    
    gn = next((e for e in manifest if e["field"] == "given_name"), None)
    gn_val = gn["surfaces"][0] if gn else ""
    
    verb_str = "\n".join(verb)
    anchor_str = "\n".join(anchors) if anchors else "   (không có)"
    supp_str = "\n".join(supplements) if supplements else "   (không có)"
    
    register = scenario.get("register", "administrative")
    if register == "dialogue":
        persona = "Bạn là người biên soạn hội thoại/cuộc trò chuyện tiếng Việt tự nhiên."
        rule_prose = "1) VIẾT DẠNG CUỘC TRÒ CHUYỆN/HỘI THOẠI HÀNG NGÀY: Viết bản nháp dưới dạng lời thoại đối đáp qua lại tự nhiên giữa các nhân vật (ví dụ: Bác sĩ - Bệnh nhân, Chuyên viên - Công dân, A - B). Sử dụng danh xưng/tiền tố lời thoại rõ ràng (ví dụ: 'Bác sĩ:', 'Bệnh nhân:'). Lồng ghép khéo léo và tự nhiên các thông tin cá nhân và nhạy cảm vào các lượt thoại đối đáp."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng ghi chú kết thúc cuộc hội thoại (ví dụ: [Kết thúc cuộc trò chuyện với {gn_val}])."
    elif register == "third_person":
        persona = "Bạn là người ghi nhận/báo cáo thông tin từ góc nhìn thứ ba."
        rule_prose = "1) VIẾT DẠNG BÁO CÁO/NARRATIVE GÓC NHÌN THỨ BA: Viết bản nháp dưới dạng lời kể, báo cáo xác minh hoặc biên bản tường thuật từ góc nhìn thứ ba. TUYỆT ĐỐI CẤM sử dụng ngôi thứ nhất 'tôi', 'chúng tôi' để chỉ đối tượng xác minh. Phải dùng ngôi thứ ba (ví dụ: 'ông Nguyễn Bảo Long', 'bà Nguyễn Thị Lan', 'chủ thể'). Triển khai văn bản mạch lạc, không dùng dấu gạch đầu dòng danh sách."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng phần ký tên/chức danh của người lập biên bản hoặc người xác minh: «{gn_val}»."
    else:
        persona = "Bạn là người soạn thảo văn bản hành chính/đời sống tiếng Việt."
        rule_prose = "1) VIẾT DẠNG ĐOẠN VĂN XUÔI LIÊN TỤC: Triển khai chi tiết văn bản dựa trên dàn ý thành văn bản hành chính hoàn chỉnh, mạch lạc. TUYỆT ĐỐI KHÔNG dùng các dấu gạch đầu dòng (- hoặc *), không viết kiểu danh sách liệt kê \"Nhãn: giá trị\" (như không viết 'Số điện thoại: 0123...', '- Dân tộc: Kinh'). Bạn PHẢI lồng ghép toàn bộ thông tin cá nhân vào các câu văn xuôi hành chính tự nhiên và liên tục trong các đoạn văn."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng phần ký tên; chỉ ghi tên gọi: «{gn_val}»."

    return f"""{persona} Hãy thực hiện viết bản nháp (Bước 3) cho văn bản/cuộc trò chuyện dựa trên kịch bản và dàn ý dưới đây.

[DÀN Ý ĐÃ LẬP]
{outline}

QUY TẮC BẮT BUỘC KHI VIẾT NHÁP:
{rule_prose}
1b) VIẾT TỰ NHIÊN, TRÁNH LẶP TỪ KHÔ CỨNG: Tránh diễn đạt lặp từ hoặc ghép nhãn thô cứng, thiếu tự nhiên (ví dụ: tránh viết "tôn giáo là không tôn giáo" mà hãy viết "không theo tôn giáo nào"; tránh viết "án tích là không có án tích" mà hãy viết "chưa từng bị kết án"). Hãy viết câu văn mượt mà và tự nhiên, phù hợp với văn cảnh thực tế.
2) Các thông tin sau PHẢI xuất hiện và DÙNG ĐÚNG NGUYÊN VĂN (copy y hệt, không đổi định dạng, không thêm/bớt ký tự, không tách/gộp số). LƯU Ý: dấu « » chỉ để đánh dấu giá trị, TUYỆT ĐỐI KHÔNG chép « » vào văn bản:
{verb_str}
2b) Thông tin bổ sung bắt buộc phải có trong văn bản (dùng đúng nguyên văn, không tự chế):
{supp_str}
3) Nội dung nhạy cảm đặc thù — viết tự nhiên trong câu và BỌC bằng thẻ ⟦field⟧nội dung⟦/field⟧. Thẻ chỉ ôm ĐÚNG cụm thông tin nhạy cảm ngắn gọn (1 mệnh đề hoặc cụm từ), không bọc cả đoạn dài, không lồng thẻ:
{anchor_str}
NGUYÊN TẮC VÀNG KHI DÁN NHÃN CÁC TRƯỜNG TỰ DO (như health_status, private_life, criminal_record, political_view, religion, sexual_orientation, v.v.):
NGUYÊN TẮC VÀNG VỀ TÍNH ĐỊNH DANH (IDENTIFIABILITY PRINCIPLE): Chỉ được bọc thẻ cho các thông tin có tính định danh cụ thể (chứa tên riêng, số liệu, chẩn đoán chi tiết hoặc mối quan hệ gắn với tên cụ thể). TUYỆT ĐỐI CẤM gán nhãn hoặc bọc thẻ cho các danh từ chung, đại từ, hoặc từ chỉ nhóm/quan hệ khái quát (ví dụ: CẤM bọc "vợ chồng", "cả hai con chung", "con cái", "bố mẹ", "gia đình", "bệnh nhân", "sức khỏe", "bệnh tật", "án tích", "pháp luật", "tôn giáo", "đi lễ").
- Hãy bọc thẻ đầy đủ cho các câu hoặc cụm từ mô tả trực tiếp tình trạng nhạy cảm đó. Với ⟦health_status⟧, bạn chỉ được bọc các mô tả trực tiếp về bệnh lý, chẩn đoán, triệu chứng lâm sàng (ví dụ: "mắc bệnh lý hen phế quản", "thường xuyên khó thở"). TUYỆT ĐỐI KHÔNG bọc phần mô tả hệ quả đối với đời sống, sinh hoạt cá nhân hay khả năng lao động vào thẻ ⟦health_status⟧ (các phần này nếu kịch bản yêu cầu sẽ bọc vào thẻ ⟦private_life⟧, nếu không thì để trống không bọc thẻ).
- Đặc biệt với trường án tích (criminal_record): Chỉ dán nhãn các câu/mệnh đề nêu trực tiếp tội danh, hành vi phạm tội, quyết định kết án cụ thể hoặc mức hình phạt (ví dụ: "bị Tòa án tuyên phạt 06 tháng tù treo về tội trộm cắp tài sản"). TUYỆT ĐỐI KHÔNG dán nhãn các câu mô tả chung chung về nỗ lực cải tạo, hoàn lương, sống gương mẫu, chấp hành tốt pháp luật tại địa phương hoặc tái hòa nhập cộng đồng để tránh gây nhiễu ranh giới nhãn.
- Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ (ví dụ: "⟦family_relations⟧con gái là Phạm Như Giang⟦/family_relations⟧" hoặc "⟦family_relations⟧mẹ ruột là Nguyễn Thu Thùy Hiền⟦/family_relations⟧"). TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧. Các thông tin chi tiết đó phải nằm ngoài thẻ này để hệ thống tự động dán nhãn riêng biệt (ví dụ: cccd, dob, address, phone).
- Không chỉ dán nhãn từ khóa đơn độc (ví dụ: tránh dán mỗi từ "bệnh" hoặc "kết án"), mà hãy dán nhãn trọn vẹn cả mệnh đề mô tả (ví dụ: bọc cả cụm "⟦health_status⟧bị suy giảm chức năng vận động⟦/health_status⟧" hoặc "⟦private_life⟧không còn khả năng lao động kiếm sống⟦/private_life⟧").
- Tránh bọc cả câu phức tạp hay đoạn dài. Phân rã ranh giới rõ ràng: Nếu một câu có cả phần bệnh trạng (health_status) và phần hậu quả ảnh hưởng đời tư (private_life) (ví dụ: "bị hen phế quản nên không thể đi làm"), hãy bọc riêng biệt thành "⟦health_status⟧bị hen phế quản⟦/health_status⟧ nên ⟦private_life⟧không thể đi làm⟦/private_life⟧". Chỉ gộp chung mệnh đề nhân quả vào một nhãn duy nhất nếu cả hai vế cùng thuộc về một trường thông tin.
Nếu có thêm bất kỳ thông tin cá nhân/nhạy cảm phụ trợ nào khác tự phát sinh khi viết, bạn cũng có thể tự bọc thẻ (ví dụ: ⟦full_name⟧Tên người phụ⟦/full_name⟧ hoặc ⟦phone⟧SĐT phụ⟦/phone⟧).
4) QUAN TRỌNG: Tuyệt đối KHÔNG tự ý bịa thêm bất kỳ số định danh, số điện thoại, ngày tháng năm sinh hoặc tên riêng nào khác ngoài danh sách ở mục 2 và 2b (trừ khi chúng được bọc trong các thẻ nhãn tương ứng ở quy tắc 3).
5) Không để lại ô trống dạng [ ], dấu … hay chỗ chờ điền; nếu không có thông tin thì bỏ hẳn mục đó.
{rule_sign}
7) CHỈ trả về nội dung văn bản nháp. KHÔNG giải thích gì thêm, KHÔNG dùng dấu ```."""

def build_revision_prompt(scenario, manifest, supplements, draft):
    pii_list = []
    for e in manifest:
        if e["mechanism"] != "anchor_tag" and e["surfaces"] and not e.get("derived"):
            pii_list.append(f"- {e['name_vi']}: {e.get('prompt_surface') or e['surfaces'][0]}")
    if supplements:
        for s in supplements:
            pii_list.append(s.strip())
            
    pii_list_str = "\n".join(pii_list)
    
    register = scenario.get("register", "administrative")
    if register == "dialogue":
        rule_format = "1) ĐẢM BẢO ĐỐI ĐÁP TỰ NHIÊN VÀ PHÙ HỢP BỐI CẢNH: Sửa lỗi nếu cuộc hội thoại diễn đạt gượng ép hoặc rập khuôn. Chỉnh sửa lời thoại trôi chảy, tự nhiên và phù hợp với tính cách/vai trò của từng nhân vật."
    elif register == "third_person":
        rule_format = "1) BẢO TOÀN GÓC NHÌN THỨ BA: Sửa các lỗi nếu văn bản dùng ngôi thứ nhất 'tôi' để chỉ đối tượng. Chuyển đổi toàn bộ thành ngôi thứ ba khách quan, trang trọng và mạch lạc."
    else:
        rule_format = "1) ĐẢM BẢO VĂN XUÔI LIÊN TỤC: Sửa lỗi nếu bản nháp sử dụng các dấu gạch đầu dòng (- hoặc *) hoặc viết kiểu danh sách liệt kê \"Nhãn: giá trị\". Bạn phải chuyển đổi và lồng ghép toàn bộ thông tin này thành các câu văn xuôi hành chính trôi chảy, liên tục trong các đoạn văn (tuyệt đối không để lại dạng danh sách liệt kê). Chỉnh sửa câu chữ mạch lạc, trang trọng và tự nhiên."

    return f"""Bạn là một Biên tập viên văn bản tiếng Việt chuyên nghiệp. Nhiệm vụ của bạn là rà soát và hiệu đính (Bước 4) bản nháp dưới đây nhằm tối ưu hóa chất lượng văn bản.

[BẢN NHÁP CỦA BẠN]
{draft}

QUY TẮC HIỆU ĐÍNH BẮT BUỘC:
{rule_format}
1b) SỬA LỖI DIỄN ĐẠT THÔ CỨNG: Sửa các lỗi diễn đạt rập khuôn hoặc ghép nhãn gượng ép (ví dụ: sửa "tôn giáo là không tôn giáo" thành "không theo tôn giáo nào"; sửa "án tích là không có án tích" thành "chưa từng bị kết án").
2) BẢO TOÀN DỮ LIỆU: Giữ nguyên vẹn 100% các giá trị PII/SPI và thông tin bổ sung quan trọng đã xuất hiện ở bản nháp dưới đây. Tuyệt đối không sửa đổi bất kỳ ký tự nào của các thông tin này:
{pii_list_str}
3) Chuẩn hóa thẻ đóng mở: Đảm bảo mọi thẻ nhạy cảm bắt đầu bằng ⟦field⟧ đều phải kết thúc bằng ⟦/field⟧ tương ứng (ví dụ: sửa lỗi đóng thiếu dạng ⟧ trần hoặc thiếu dấu gạch chéo `/`). Không lồng thẻ vào nhau.
Rà soát kỹ và dán nhãn đầy đủ cho các trường tự do (health_status, private_life, criminal_record, political_view, religion, sexual_orientation). Đảm bảo tuân thủ NGUYÊN TẮC VÀNG VỀ TÍNH ĐỊNH DANH: chỉ bọc thẻ cho các thông tin có tính định danh cụ thể, TUYỆT ĐỐI CẤM dán nhãn cho các danh từ/đại từ chỉ nhóm/quan hệ chung chung (như "vợ chồng", "cả hai con chung", "con cái", "gia đình", "sức khỏe", "bệnh tật", "án tích", v.v.).
- Với ⟦health_status⟧, bạn chỉ được bọc các mô tả trực tiếp về bệnh lý, chẩn đoán, triệu chứng lâm sàng. TUYỆT ĐỐI KHÔNG bọc phần mô tả hệ quả đối với đời sống, sinh hoạt hay công việc vào thẻ ⟦health_status⟧ (các phần này nếu kịch bản yêu cầu sẽ bọc vào thẻ ⟦private_life⟧, nếu không thì để trống không bọc thẻ).
- Tránh bọc cả câu phức tạp hay đoạn dài. Phân rã ranh giới rõ ràng: Nếu một câu có cả phần bệnh trạng (health_status) và phần hậu quả ảnh hưởng đời tư (private_life), hãy bọc riêng biệt thành "⟦health_status⟧[bệnh trạng]⟦/health_status⟧ nên ⟦private_life⟧[hậu quả]⟦/private_life⟧". Chỉ gộp chung mệnh đề nhân quả vào một nhãn duy nhất nếu cả hai vế cùng thuộc về một trường thông tin.
- Đặc biệt với án tích (criminal_record), chỉ dán nhãn các câu/mệnh đề nêu cụ thể tội danh, hành vi phạm tội hoặc hình phạt cụ thể; TUYỆT ĐỐI KHÔNG dán nhãn các câu mô tả nỗ lực cải tạo, hoàn lương, sống gương mẫu hoặc tái hòa nhập cộng đồng nhằm tránh làm nhiễu ranh giới nhãn.
- Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ (ví dụ: "⟦family_relations⟧con gái là Phạm Như Giang⟦/family_relations⟧" hoặc "⟦family_relations⟧mẹ ruột là Nguyễn Thu Thùy Hiền⟦/family_relations⟧"). TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧.
4) KHÔNG tự ý bổ sung thêm thông tin cá nhân (tên riêng, số điện thoại, địa chỉ) mới nào khác vào văn bản (trừ khi chúng được dán nhãn thẻ đúng quy cách).
5) CHỈ trả về nội dung văn bản đã được hiệu đính. KHÔNG giải thích, KHÔNG markdown chứa ```."""

# ---------------- gọi Gemini ----------------
def call_gemini(prompt, temperature=0.85):
    time.sleep(4)  # Tránh lỗi quota rate limit (HTTP 429)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    gen_cfg = {"temperature": temperature, "maxOutputTokens": 8192, "topP": 0.95}
    if MODEL.startswith("gemini-2.5") or MODEL.startswith("gemini-3"):
        gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}   # chỉ model thinking mới nhận; Gemma sẽ lỗi nếu gửi
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen_cfg}
    data = json.dumps(body).encode("utf-8")
    j = None
    for attempt in range(4):                     # auto-retry 503/500 (quá tải/lỗi tạm), KHÔNG retry 429 (hết quota)
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
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
    if "error" in j:
        raise RuntimeError(f"API {j['error'].get('code')}: {j['error'].get('message')}")
    parts = ((j.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()

def clean_output(t):
    t = re.sub(r"```[a-zA-Z]*\n?", "", t)
    t = t.replace("«", "").replace("»", "")   # LLM (nhất là flash-lite) hay chép dấu phân định « » -> bỏ
    return NFC(t.strip())

# ---------------- coverage ----------------
def coverage(clean, manifest):
    miss = []
    for e in manifest:
        if e["mechanism"] == "anchor_tag" or e.get("anchor"): continue
        if e.get("derived"): continue
        found = (len(match_cue_context(clean, e["surfaces"], e.get("cue_words") or BIRTH_CUES)) > 0
                 if e["mechanism"] in ("cue_context", "date") else any(s in clean for s in e["surfaces"]))
        if not found: miss.append(e["field"])
    return miss

CRITICAL = {"full_name", "cccd", "phone", "dob", "address"}

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

def find_matching_template(scenario):
    load_all_form_metadata()
    if not FORM_METADATA_CACHE:
        return None
    sid = scenario["id"]
    title = scenario.get("title", "")
    
    # Từ khóa tìm kiếm dựa trên ID kịch bản hoặc Tiêu đề
    keywords = []
    if "health" in sid or "discharge" in sid:
        keywords = ["bệnh án", "ra viện", "sức khỏe", "y tế"]
    elif "crim" in sid:
        keywords = ["án tích", "xóa án tích", "lý lịch tư pháp", "tòa án"]
    elif "religion" in sid:
        keywords = ["tôn giáo", "sinh hoạt tôn giáo", "tín ngưỡng"]
    elif "poverty" in sid or "priv_poverty" in sid:
        keywords = ["hộ nghèo", "cận nghèo", "nghèo"]
    elif "party" in sid:
        keywords = ["đảng viên", "kết nạp đảng", "lý lịch đảng viên"]
    elif "syll" in sid:
        keywords = ["sơ yếu lý lịch", "lý lịch tự khai", "tự thuật"]
    elif "loc" in sid or "verify" in sid:
        keywords = ["xác minh", "biên bản", "định vị"]
    elif "sexori" in sid or "hotich" in sid:
        keywords = ["hộ tịch", "khai sinh", "cải chính"]
    elif "bio" in sid:
        keywords = ["sinh trắc", "căn cước", "vân tay", "ảnh"]
    else:
        keywords = [title.lower()]

    matches = []
    for tid, meta in FORM_METADATA_CACHE.items():
        rec_type = (meta.get("record_type") or "").lower()
        raw_text = (meta.get("form_raw_text") or "").lower()
        
        score = sum(1 for kw in keywords if kw in rec_type or kw in raw_text)
        if score > 0:
            matches.append((score, tid))
            
    if matches:
        matches.sort(reverse=True, key=lambda x: x[0])
        max_score = matches[0][0]
        candidates = [tid for score, tid in matches if score == max_score]
        return random.choice(candidates)
    
    # Dự phòng: lấy đại 1 cái ngẫu nhiên trong danh sách biểu mẫu thực tế
    return random.choice(list(FORM_METADATA_CACHE.keys()))

# ---------------- sinh 1 mẫu (có regen) ----------------
def generate_one(profile, scenario, profiles):
    # Lấy thông tin tham chiếu biểu mẫu
    seed_info = scenario.get("seed") or {}
    template_id = seed_info.get("template_id")
    if not template_id:
        template_id = find_matching_template(scenario)
    form_meta = get_form_metadata(template_id) if template_id else {}

    manifest = build_manifest(profile, scenario)
    extra, supplements, distractors = realize_supplemental(
        profile, scenario, profiles, f"{profile.get('profile_id')}|{scenario['id']}")
    manifest = manifest + extra                      # thêm attribute person (PII đa chủ thể)
    
    # Chọn một biến thể ngẫu nhiên cho mỗi trường để đưa vào prompt nhằm tăng tính đa dạng
    for e in manifest:
        if e.get("surfaces"):
            e["prompt_surface"] = random.choice(e["surfaces"])
        else:
            e["prompt_surface"] = ""
    
    # Bước 1 & 2: Lập dàn ý (Outline)
    outline_prompt = build_outline_prompt(scenario, manifest, supplements)
    try:
        raw_outline = call_gemini(outline_prompt, temperature=0.5)
        outline = clean_output(raw_outline)
    except Exception as e:
        print(f"      (Lập dàn ý gặp lỗi: {e}. Sử dụng dàn ý mặc định...)")
        outline = """1. Phần mở đầu: Tiêu ngữ, ngày tháng địa điểm, thông tin khai báo nhân thân của chủ thể.
2. Phần nội dung: Trình bày chi tiết hoàn cảnh thực tế, nêu rõ các thông tin nhạy cảm liên quan đến sự việc.
3. Phần kết: Đưa ra lời cam đoan/yêu cầu giải quyết, chữ ký xác nhận của chủ thể."""
        
    last = None
    for attempt in range(1, 4):
        # Giảm dần temperature để viết nháp chính xác hơn khi bị lỗi
        temp_draft = 0.85 if attempt == 1 else 0.7
        
        # Bước 3: Viết bản nháp
        draft_prompt = build_draft_prompt(scenario, manifest, supplements, outline)
        raw_draft = call_gemini(draft_prompt, temperature=temp_draft)
        draft = clean_output(raw_draft)
        
        # Bước 4: Sửa bài (Hiệu đính)
        revision_prompt = build_revision_prompt(scenario, manifest, supplements, draft)
        raw_revised = call_gemini(revision_prompt, temperature=0.2)
        tagged = clean_output(raw_revised)
        
        # Phân tích thẻ
        ext = extract_anchor_tags(tagged, [e["field"] for e in manifest if e.get("anchor")])
        clean = ext["clean_text"]
        miss = coverage(clean, manifest)
        important = [f for f in miss if f in CRITICAL or SENS.get(f) == "SPI"]
        last = (manifest, clean, ext, miss)
        if ext["ok"] and not important: 
            break
        print(f"   [regen {attempt}] ok_tag={ext['ok']} important_miss={important}")
        
    manifest, clean, ext, miss = last
    spans = annotate(clean, manifest, ext["spans"])
    return {
        "profile_id": profile.get("profile_id"),
        "scenario": scenario["id"],
        "template_id": form_meta.get("template_id"),
        "source_url": form_meta.get("source_url"),
        "record_type": form_meta.get("record_type"),
        "agency": form_meta.get("agency"),
        "form_raw_text": form_meta.get("form_raw_text"),
        "track": "B",
        "model": MODEL,
        "content": clean,
        "spans": [{"start": s["start"], "end": s["end"], "field": s["field"], "label": s["label"],
                   "text": clean[s["start"]:s["end"]], "via": s.get("via")} for s in spans],
        "meta": {"missing_coverage": miss, "n_spans": len(spans), "tag_ok": ext["ok"], "distractors": distractors},
    }

# ---------------- BATCH ----------------
NOW_YEAR = 2026
def _age(fl):
    try: return NOW_YEAR - int(str(fl.get("dob", "")).split("/")[-1])
    except Exception: return None

# 8 kịch bản phân biệt, phủ đa dạng SPI (đã bỏ sc_party_vetting và sc_bio_enroll)
DEFAULT_SCENARIOS = ["sc_health_welfare", "sc_crim_erase", "sc_syll_selfdeclare", "sc_priv_poverty",
                     "sc_health_discharge", "sc_sexori_medical", "sc_religion_activity",
                     "sc_loc_verify"]

POOL_SIZE = 3000   # cố định để mượn thân nhân DETERMINISTIC (generate & reannotate phải giống nhau)

def run_batch(n=10):
    OUT.mkdir(exist_ok=True)
    pool = load_profiles(POOL_SIZE)                  # pool lớn: chọn hồ sơ + mượn thân nhân
    
    # Trộn ngẫu nhiên kịch bản để phân bổ đều
    all_scenarios = list(CATALOG["scenarios"])
    random.shuffle(all_scenarios)
    
    # Trộn ngẫu nhiên hồ sơ người lớn (18-85 tuổi)
    adult_pool = [p for p in pool if (_age(pfields(p)) or 0) >= 18 and (_age(pfields(p)) or 999) <= 85]
    random.shuffle(adult_pool)
    
    if len(adult_pool) < n:
        raise SystemExit(f"Chỉ tìm được {len(adult_pool)} hồ sơ ≥18 trong pool, cần {n}.")
        
    print(f"Model: {MODEL} | batch {n} row (hồ sơ và kịch bản ngẫu nhiên)\n")

    lines, summary = [], []
    for i in range(n):
        profile = adult_pool[i % len(adult_pool)]
        scenario = all_scenarios[i % len(all_scenarios)]
        pid = profile.get("profile_id")
        print(f"[{i+1}/{n}] {pid} (tuổi {_age(pfields(profile))}) × {scenario['id']} — {scenario['title']}")
        try:
            rec = generate_one(profile, scenario, pool)
            lines.append(json.dumps(rec, ensure_ascii=False))
            m = rec["meta"]
            summary.append((pid, scenario["id"], m["n_spans"], m["tag_ok"], m["missing_coverage"]))
            print(f"      -> {m['n_spans']} spans | tag_ok={m['tag_ok']} | miss={m['missing_coverage']}")
        except Exception as e:
            print("      LỖI:", e)
            summary.append((pid, scenario["id"], "-", "ERR", str(e)[:50]))

    ds = OUT / "dataset.jsonl"
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 84)
    print(f"{'#':<3}{'profile':<11}{'scenario':<22}{'spans':<7}{'tag_ok':<8}missing")
    print("-" * 84)
    for i, (pid, sid, ns, ok, ms) in enumerate(summary, 1):
        print(f"{i:<3}{pid:<11}{sid:<22}{str(ns):<7}{str(ok):<8}{ms}")
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"\n{ok_cnt}/{n} tag_ok. Dataset gộp -> {ds}")

def run_batch_by_register(docs_per_register=2):
    OUT.mkdir(exist_ok=True)
    pool = load_profiles(POOL_SIZE)
    adult_pool = [p for p in pool if (_age(pfields(p)) or 0) >= 18 and (_age(pfields(p)) or 999) <= 85]
    random.shuffle(adult_pool)
    
    scenarios_by_register = {}
    for scenario in CATALOG["scenarios"]:
        reg = scenario.get("register", "administrative")
        scenarios_by_register.setdefault(reg, []).append(scenario)
        
    selected_pairs = []
    profile_idx = 0
    
    for reg, sc_list in sorted(scenarios_by_register.items()):
        scs = list(sc_list)
        random.shuffle(scs)
        for i in range(docs_per_register):
            sc = scs[i % len(scs)]
            prof = adult_pool[profile_idx % len(adult_pool)]
            profile_idx += 1
            selected_pairs.append((prof, sc))
            
    n = len(selected_pairs)
    print(f"Model: {MODEL} | batch {n} row ({docs_per_register} row cho mỗi văn phong)\n")
    
    lines, summary = [], []
    for i, (profile, scenario) in enumerate(selected_pairs):
        pid = profile.get("profile_id")
        reg = scenario.get("register", "administrative")
        print(f"[{i+1}/{n}] {pid} (tuổi {_age(pfields(profile))}) × {scenario['id']} ({reg}) — {scenario['title']}")
        try:
            rec = generate_one(profile, scenario, pool)
            lines.append(json.dumps(rec, ensure_ascii=False))
            m = rec["meta"]
            summary.append((pid, f"{scenario['id']} ({reg})", m["n_spans"], m["tag_ok"], m["missing_coverage"]))
            print(f"      -> {m['n_spans']} spans | tag_ok={m['tag_ok']} | miss={m['missing_coverage']}")
        except Exception as e:
            print("      LỖI:", e)
            summary.append((pid, f"{scenario['id']} ({reg})", "-", "ERR", str(e)[:50]))
            
    ds = OUT / "dataset.jsonl"
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"{'#':<3}{'profile':<11}{'scenario (register)':<35}{'spans':<7}{'tag_ok':<8}missing")
    print("-" * 90)
    for i, (pid, sid, ns, ok, ms) in enumerate(summary, 1):
        print(f"{i:<3}{pid:<11}{sid:<35}{str(ns):<7}{str(ok):<8}{ms}")
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"\n{ok_cnt}/{n} tag_ok. Dataset gộp -> {ds}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "register":
        run_batch_by_register(2)
    else:
        n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
        run_batch(n)
