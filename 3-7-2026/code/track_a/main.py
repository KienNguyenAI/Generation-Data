# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import random
from pathlib import Path

# Add project code folder to path to allow core & track_a imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import (
    OUT, MODEL, SENS, FIELDS, MECHANISM, CUE_WORDS, BIRTH_CUES, CRITICAL, SENTINEL,
    load_profiles, pfields, load_all_form_metadata, get_form_metadata, get_all_form_metadata
)
from core.utils import (
    split_vietnamese_name, _age, render_cccd, render_phone, render_dob, render_address, render_full_name
)
from core.manifest import build_manifest_for_used_fields, extract_core_alias_name
from core.api import call_gemini, clean_output
from core.annotation import extract_anchor_tags, annotate, coverage
from track_a.prompts import (
    SUB_FORMATS, TONES, build_outline_prompt, build_draft_prompt, build_revision_prompt
)

# Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

DOMAIN_SPI_MAP = {
    "medical_healthcare": ["health_status", "health_insurance_no", "biometric", "sexual_orientation"],
    "insurance_welfare": ["health_insurance_no", "social_insurance_no", "private_life"],
    "justice_legal": ["criminal_record", "behavioral_data", "political_view", "location_data"],
    "civil_family": ["private_life", "religion", "ethnicity", "sexual_orientation", "eid_credentials"],
    "education_training": ["private_life", "ethnicity", "political_view"],
    "religion_ethnicity": ["religion", "ethnicity"],
    "economy_tech_other": ["bank_account", "eid_credentials", "location_data"]
}

def generate_one(profile, form_meta, register=None, outline=None, tagged_fields=None, target_spi=None):
    fl = pfields(profile)
    
    # 1. Choose or reuse register
    if not register:
        register = random.choice(["administrative", "dialogue", "third_person"])
        
    # Choose sub-format and tone
    sub_format_key = random.choice(list(SUB_FORMATS[register].keys()))
    sub_format_desc = SUB_FORMATS[register][sub_format_key]
    
    if register == "dialogue":
        valid_tones = ["cooperative_polite", "urgent_anxious", "frustrated_complaining", "casual_informal"]
    elif register == "third_person":
        valid_tones = ["casual_confidential", "urgent_anxious", "casual_informal"]
    else:
        valid_tones = ["formal_objective", "urgent_anxious", "frustrated_complaining"]
        
    tone_key = random.choice(valid_tones)
    tone_desc = TONES[tone_key]
    
    # 2. Compile all fields available in profile for the prompt
    fields_desc = []
    outline_fields_desc = []
    for field in MECHANISM:
        if field in ("family_name", "middle_name", "given_name"):
            continue
        val = fl.get(field)
        if val is None or str(val).strip() == "":
            continue
        
        name_vi = (FIELDS.get(field) or {}).get("name_vi", field)
        fields_desc.append(f"   - {name_vi} ({field}): «{val}»")
        outline_fields_desc.append(f"   - {name_vi} ({field})")
    fields_desc_str = "\n".join(fields_desc)
    outline_fields_desc_str = "\n".join(outline_fields_desc)
    
    # 3. Choose or reuse outline
    selected_fields = []
    if not outline:
        outline_prompt = build_outline_prompt(form_meta, outline_fields_desc_str, register, sub_format_desc, tone_desc, target_spi=target_spi)
        try:
            raw_outline = call_gemini(outline_prompt, temperature=0.5)
            outline = clean_output(raw_outline)
            
            # Extract selected fields
            match = re.search(r'(?:«|)?SELECTED_FIELDS:\s*(\[.*?\])(?:»|)?', raw_outline, re.IGNORECASE)
            if match:
                try:
                    selected_fields = json.loads(match.group(1))
                    selected_fields = [f.strip() for f in selected_fields if f.strip() in MECHANISM]
                except Exception:
                    selected_fields = []
            
            if not selected_fields:
                # Fallback: scan outline text for field keys
                for field in MECHANISM:
                    if field in raw_outline:
                        selected_fields.append(field)
                if not selected_fields:
                    selected_fields = ["full_name", "dob", "cccd", "address", "phone"]
            
            if target_spi and target_spi not in selected_fields:
                selected_fields.append(target_spi)
                
            # Clean SELECTED_FIELDS block from the outline to keep outline clean
            outline = re.sub(r'(?:«|)?SELECTED_FIELDS:\s*\[.*?\](?:»|)?', '', outline, flags=re.IGNORECASE).strip()
        except Exception as e:
            print(f"      (Lập dàn ý gặp lỗi: {e}. Sử dụng dàn ý mặc định...)")
            outline = """1. Phần mở đầu: Tiêu ngữ, thông tin người làm đơn/các nhân vật.
2. Phần nội dung: Trình bày chi tiết hoàn cảnh có lồng ghép thông tin nhạy cảm liên quan đến thủ tục.
3. Phần kết: Ký tên/ghi rõ họ tên."""
            selected_fields = ["full_name", "dob", "cccd", "address", "phone"]
            if target_spi and target_spi not in selected_fields:
                selected_fields.append(target_spi)
    else:
        # If outline is reused, extract selected_fields from outline if tagged_fields is None
        if tagged_fields is not None:
            selected_fields = list(tagged_fields)
        else:
            match = re.search(r'(?:«|)?SELECTED_FIELDS:\s*(\[.*?\])(?:»|)?', outline, re.IGNORECASE)
            if match:
                try:
                    selected_fields = json.loads(match.group(1))
                    selected_fields = [f.strip() for f in selected_fields if f.strip() in MECHANISM]
                except Exception:
                    selected_fields = []
            if not selected_fields:
                selected_fields = ["full_name", "dob", "cccd", "address", "phone"]

    # Filter fields_desc_str based on selected_fields, and build banned fields list
    filtered_fields_desc = []
    banned_fields_desc = []
    for field in MECHANISM:
        if field in ("family_name", "middle_name", "given_name"):
            continue
        val = fl.get(field)
        if val is None or str(val).strip() == "":
            continue
        
        name_vi = (FIELDS.get(field) or {}).get("name_vi", field)
        if field in selected_fields:
            display_val = str(val).strip()
            if field == "cccd": display_val = random.choice(render_cccd(display_val))
            elif field == "phone": display_val = random.choice(render_phone(display_val))
            elif field == "dob": display_val = random.choice(render_dob(display_val))
            elif field == "address": display_val = random.choice(render_address(display_val))
            elif field == "full_name": display_val = random.choice(render_full_name(display_val))
            filtered_fields_desc.append(f"   - {name_vi} ({field}): «{display_val}»")
        elif SENS.get(field) in ("SPI", "PII") or field in ("marital_status", "religion", "political_view", "sexual_orientation", "health_status", "criminal_record", "private_life"):
            banned_fields_desc.append(f"   - {name_vi} ({field})")
            
    filtered_fields_desc_str = "\n".join(filtered_fields_desc)
    banned_fields_desc_str = "\n".join(banned_fields_desc) if banned_fields_desc else "   (Không có)"

    last = None
    for attempt in range(1, 4):
        temp_draft = 0.85 if attempt == 1 else 0.7
        draft_prompt = build_draft_prompt(form_meta, filtered_fields_desc_str, banned_fields_desc_str, outline, register, sub_format_desc, tone_desc)
        raw_draft = call_gemini(draft_prompt, temperature=temp_draft)
        draft = clean_output(raw_draft)
        
        revision_prompt = build_revision_prompt(filtered_fields_desc_str, banned_fields_desc_str, draft, register)
        raw_revised = call_gemini(revision_prompt, temperature=0.2)
        tagged = clean_output(raw_revised)
        
        # We dynamically discover or reuse which fields the LLM actually chose to tag
        allowed_fields = set(selected_fields)
        # Always allow core PII fields to be tagged if the LLM chose to write them
        allowed_fields.update(["full_name", "dob", "cccd", "address", "phone", "email"])
        if "family_relations" in selected_fields:
            allowed_fields.update(["address", "dob", "cccd", "phone", "email"])

        if tagged_fields is None:
            attempt_tagged_fields = set(re.findall(r"⟦([a-zA-Z0-9_]+)⟧", tagged))
            attempt_tagged_fields = attempt_tagged_fields.intersection(allowed_fields)
        else:
            attempt_tagged_fields = set(tagged_fields)
            allowed_fields.update(attempt_tagged_fields)
        
        # Build manifest containing ONLY these used fields
        manifest = build_manifest_for_used_fields(profile, attempt_tagged_fields)
        
        # Choose a random surface variant for matching validation
        for e in manifest:
            if e.get("surfaces"):
                e["prompt_surface"] = random.choice(e["surfaces"])
            else:
                e["prompt_surface"] = ""
                
        ext = extract_anchor_tags(tagged, [e["field"] for e in manifest if e.get("anchor")])
        
        # Restrict spans to only allowed_fields
        ext["spans"] = [s for s in ext["spans"] if s["field"] in allowed_fields]
        
        clean = ext["clean_text"]
        
        # Coverage check (strictly on the dynamically constructed manifest)
        miss = coverage(clean, manifest)
        important = [f for f in miss if (f in CRITICAL or SENS.get(f) == "SPI") and f in selected_fields]
        last = (manifest, clean, ext, miss, attempt_tagged_fields)
        
        # If the tags are parsed successfully and no critical/SPI fields used by the LLM are missing
        if ext["ok"] and not important:
            break
        
    manifest, clean, ext, miss, final_tagged_fields = last
    spans = annotate(clean, manifest, ext["spans"])
    
    return {
        "profile_id": profile.get("profile_id"),
        "template_id": form_meta.get("template_id"),
        "source_url": form_meta.get("source_url"),
        "record_type": form_meta.get("record_type"),
        "agency": form_meta.get("agency"),
        "track": "B_form_driven",
        "model": MODEL,
        "register": register,
        "content": clean,
        "spans": [{"start": s["start"], "end": s["end"], "field": s["field"], "label": s["label"],
                   "text": clean[s["start"]:s["end"]], "via": s.get("via")} for s in spans],
        "meta": {
            "missing_coverage": miss, 
            "n_spans": len(spans), 
            "tag_ok": ext["ok"],
            "outline": outline,
            "tagged_fields": list(final_tagged_fields),
            "sub_format": sub_format_key,
            "tone": tone_key
        },
    }

def run_batch(n=10):
    OUT.mkdir(exist_ok=True)
    
    # Initialize form metadata cache
    load_all_form_metadata()
    valid_forms = [item for item in get_all_form_metadata().values() if item.get("form_raw_text") and item.get("record_type")]
    
    if not valid_forms:
        print("Không tìm thấy biểu mẫu hợp lệ nào trong form.json!")
        sys.exit(1)
        
    print(f"Tìm thấy {len(valid_forms)} biểu mẫu chứa văn bản mẫu trong form.json")
    
    pool = load_profiles(3000)
    # Trộn ngẫu nhiên hồ sơ người lớn (18-85 tuổi)
    adult_pool = [p for p in pool if (_age(pfields(p)) or 0) >= 18 and (_age(pfields(p)) or 999) <= 85]
    random.shuffle(adult_pool)
    
    if len(adult_pool) < n:
        print(f"Chỉ tìm thấy {len(adult_pool)} hồ sơ ≥18 tuổi trong pool, cần {n}.")
        sys.exit(1)
        
    print(f"Model: {MODEL} | sinh {n} dòng dữ liệu theo biểu mẫu ngẫu nhiên (Lựa chọn trường linh hoạt)\n")
    
    lines, summary = [], []
    for i in range(n):
        profile = adult_pool[i % len(adult_pool)]
        form_meta = random.choice(valid_forms)
        pid = profile.get("profile_id")
        
        # Determine target SPI based on domain mapping
        dom = form_meta.get("domain", "economy_tech_other")
        target_candidates = DOMAIN_SPI_MAP.get(dom, [])
        fl = pfields(profile)
        available_target_spis = [f for f in target_candidates if fl.get(f) and str(fl.get(f)).strip()]
        
        if not available_target_spis:
            all_spis = [f for f in MECHANISM if SENS.get(f) == "SPI"]
            available_target_spis = [f for f in all_spis if fl.get(f) and str(fl.get(f)).strip()]
            
        target_spi = random.choice(available_target_spis) if available_target_spis else None
        
        print(f"[{i+1}/{n}] {pid} | Biểu mẫu: {form_meta['record_type'][:30]} | SPI: {target_spi or 'None'}", end="", flush=True)
        try:
            rec = generate_one(profile, form_meta, target_spi=target_spi)
            lines.append(json.dumps(rec, ensure_ascii=False))
            m = rec["meta"]
            summary.append((pid, form_meta["record_type"][:30], m["n_spans"], m["tag_ok"], m["missing_coverage"]))
            print(f" -> OK ({m['n_spans']} nhãn)")
        except Exception as e:
            print(f" -> LỖI: {e}")
            summary.append((pid, form_meta["record_type"][:30], "-", "ERR", str(e)[:50]))
            
    ds = OUT / os.environ.get("SECUREPI_OUT_NAME", "dataset.jsonl")
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 60)
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"Hoàn thành sinh dữ liệu! Thành công: {ok_cnt}/{n} dòng.")
    print(f"Kết quả được lưu tại: {ds}")
    print("=" * 60)

def patch_profile_in_dataset(pid):
    OUT.mkdir(exist_ok=True)
    ds = OUT / os.environ.get("SECUREPI_OUT_NAME", "dataset.jsonl")
    if not ds.exists():
        print(f"Không tìm thấy file nguồn dữ liệu nào tại {ds}!")
        sys.exit(1)
        
    lines = ds.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines if line.strip()]
    
    # Find matching record
    found_idx = -1
    for idx, rec in enumerate(records):
        if rec.get("profile_id") == pid:
            found_idx = idx
            break
            
    load_all_form_metadata()
    pool = load_profiles(3000)
    profile = next((p for p in pool if p.get("profile_id") == pid), None)
    if not profile:
        print(f"Không tìm thấy hồ sơ {pid} trong ngân hàng hồ sơ!")
        sys.exit(1)

    if found_idx == -1:
        print(f"Không tìm thấy profile_id: {pid} trong {ds.name}. Tiến hành sinh mới...")
        valid_forms = [item for item in get_all_form_metadata().values() if item.get("form_raw_text") and item.get("record_type")]
        if not valid_forms:
            print("Không tìm thấy biểu mẫu hợp lệ nào trong form.json!")
            sys.exit(1)
        form_meta = random.choice(valid_forms)
        register = random.choice(["administrative", "dialogue", "third_person"])
        outline = None
        tagged_fields = None
    else:
        print(f"Tìm thấy hồ sơ {pid} tại dòng {found_idx + 1} của {ds.name}. Tiến hành sinh lại...")
        rec = records[found_idx]
        form_meta = get_all_form_metadata().get(rec["template_id"])
        if not form_meta:
            # Find by record_type
            for meta in get_all_form_metadata().values():
                if meta.get("record_type") == rec["record_type"]:
                    form_meta = meta
                    break
                    
        if not form_meta:
            print(f"Không tìm thấy biểu mẫu tương ứng: {rec['record_type']}")
            sys.exit(1)
            
        # Re-use register, outline, and tagged_fields from existing record metadata
        register = rec.get("register")
        outline = rec.get("meta", {}).get("outline")
        tagged_fields = rec.get("meta", {}).get("tagged_fields")
    
    # Determine target SPI based on domain mapping
    dom = form_meta.get("domain", "economy_tech_other")
    target_candidates = DOMAIN_SPI_MAP.get(dom, [])
    fl = pfields(profile)
    available_target_spis = [f for f in target_candidates if fl.get(f) and str(fl.get(f)).strip()]
    if not available_target_spis:
        all_spis = [f for f in MECHANISM if SENS.get(f) == "SPI"]
        available_target_spis = [f for f in all_spis if fl.get(f) and str(fl.get(f)).strip()]
    target_spi = random.choice(available_target_spis) if available_target_spis else None
    
    # Generate one clean record
    new_rec = generate_one(profile, form_meta, register=register, outline=outline, tagged_fields=tagged_fields, target_spi=target_spi)
    if found_idx == -1:
        records.append(new_rec)
    else:
        records[found_idx] = new_rec
    
    # Save back to dataset.jsonl
    dest = OUT / os.environ.get("SECUREPI_OUT_NAME", "dataset.jsonl")
    dest.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    print(f"Đã cập nhật thành công và lưu vào {dest}!")
    print("\n--- NỘI DUNG MỚI ---")
    print(new_rec["content"])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--patch" and len(sys.argv) > 2:
            patch_profile_in_dataset(sys.argv[2])
        elif arg.startswith("pf_"):
            patch_profile_in_dataset(arg)
        elif arg.isdigit():
            run_batch(int(arg))
        else:
            print("Tham số không hợp lệ. Sử dụng: python main.py [số lượng dòng | profile_id]")
    else:
        run_batch(2)
