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

def sanitize_tags(text):
    if not text:
        return text
    # Dọn dẹp khoảng trắng thừa bên trong thẻ ⟦ và ⟧
    text = re.sub(r'⟦\s+', '⟦', text)
    text = re.sub(r'\s+⟧', '⟧', text)
    text = re.sub(r'⟦/\s+', '⟦/', text)
    
    # Sửa lỗi quên gạch chéo thẻ đóng: ⟦field⟧giá trị⟦field⟧ -> ⟦field⟧giá trị⟦/field⟧
    fields = set(re.findall(r'⟦([a-zA-Z0-9_]+)⟧', text))
    for f in fields:
        pattern = r'⟦' + re.escape(f) + r'⟧(.*?)(⟦' + re.escape(f) + r'⟧|⟦/' + re.escape(f) + r'⟧)'
        def repl(match):
            content, next_tag = match.groups()
            if next_tag == f'⟦{f}⟧':
                return f'⟦{f}⟧{content}⟦/{f}⟧'
            return match.group(0)
        for _ in range(3):
            text, count = re.subn(pattern, repl, text)
            if count == 0:
                break
    return text

def auto_tag_manifest_fields(tagged_text, manifest):
    if not tagged_text or not manifest:
        return tagged_text
        
    all_surfaces = []
    for e in manifest:
        fld = e["field"]
        for s in e.get("surfaces", []):
            if s.strip() and len(s.strip()) > 1:
                all_surfaces.append((s.strip(), fld))
                
    # Sắp xếp theo độ dài giảm dần để khớp các chuỗi dài trước (tránh khớp nửa tên)
    all_surfaces.sort(key=lambda x: -len(x[0]))
    
    for surface, fld in all_surfaces:
        parts = re.split(r'(⟦/?.*?⟧)', tagged_text)
        stack = []
        changed = False
        for i in range(len(parts)):
            part = parts[i]
            if part.startswith('⟦') and part.endswith('⟧'):
                tag_content = part[1:-1]
                if tag_content.startswith('/'):
                    tag_name = tag_content[1:]
                    if stack and stack[-1] == tag_name:
                        stack.pop()
                else:
                    stack.append(tag_content)
            else:
                # Chỉ thay thế nếu nằm ngoài toàn bộ thẻ (stack rỗng)
                if not stack and surface in part:
                    # Tránh khớp từ con bên trong một từ tiếng Việt lớn hơn
                    pattern = r'(?<![a-zA-Z0-9_À-ỹ])' + re.escape(surface) + r'(?![a-zA-Z0-9_À-ỹ])'
                    new_part, count = re.subn(pattern, f"⟦{fld}⟧{surface}⟦/{fld}⟧", part)
                    if count > 0:
                        parts[i] = new_part
                        changed = True
        if changed:
            tagged_text = "".join(parts)
            
    return tagged_text

def sanitize_tags(text):
    if not text:
        return text
    # Dọn dẹp khoảng trắng thừa bên trong thẻ ⟦ và ⟧
    text = re.sub(r'⟦\s+', '⟦', text)
    text = re.sub(r'\s+⟧', '⟧', text)
    text = re.sub(r'⟦/\s+', '⟦/', text)
    
    # Sửa lỗi quên gạch chéo thẻ đóng: ⟦field⟧giá trị⟦field⟧ -> ⟦field⟧giá trị⟦/field⟧
    fields = set(re.findall(r'⟦([a-zA-Z0-9_]+)⟧', text))
    for f in fields:
        pattern = r'⟦' + re.escape(f) + r'⟧(.*?)(⟦' + re.escape(f) + r'⟧|⟦/' + re.escape(f) + r'⟧)'
        def repl(match):
            content, next_tag = match.groups()
            if next_tag == f'⟦{f}⟧':
                return f'⟦{f}⟧{content}⟦/{f}⟧'
            return match.group(0)
        for _ in range(3):
            text, count = re.subn(pattern, repl, text)
            if count == 0:
                break
    return text

def auto_close_unclosed_tags(text, profile):
    if not text or not profile:
        return text
        
    # Tìm các nhãn mở và đóng
    open_tags = re.findall(r'⟦([a-zA-Z0-9_]+)⟧', text)
    close_tags = re.findall(r'⟦/([a-zA-Z0-9_]+)⟧', text)
    
    unclosed_fields = []
    for f in set(open_tags):
        if open_tags.count(f) > close_tags.count(f):
            unclosed_fields.append(f)
            
    if not unclosed_fields:
        return text
        
    fl = pfields(profile)
    from core.manifest import build_manifest_for_used_fields
    manifest = build_manifest_for_used_fields(profile, unclosed_fields)
    
    # Tạo mapping field -> list of surfaces
    field_surfaces = {}
    for e in manifest:
        fld = e["field"]
        field_surfaces[fld] = sorted(e.get("surfaces", []), key=lambda x: -len(x))
        
    for fld in unclosed_fields:
        surfaces = field_surfaces.get(fld, [])
        if not surfaces:
            continue
            
        tag_str = f"⟦{fld}⟧"
        close_tag_str = f"⟦/{fld}⟧"
        
        parts = text.split(tag_str)
        new_text = parts[0]
        
        for i in range(1, len(parts)):
            part = parts[i]
            matched_surface = None
            for s in surfaces:
                s_clean = re.sub(r'\s+', '', s).lower()
                part_sub = part[:len(s) * 2]
                part_sub_clean = re.sub(r'\s+', '', part_sub).lower()
                
                if part_sub_clean.startswith(s_clean):
                    accum = ""
                    idx = 0
                    for ch in part:
                        if not ch.isspace():
                            accum += ch.lower()
                        idx += 1
                        if accum == s_clean:
                            break
                    if accum == s_clean:
                        matched_surface = part[:idx]
                        break
            
            if matched_surface:
                rest = part[len(matched_surface):]
                if not rest.strip().startswith(close_tag_str):
                    new_text += tag_str + matched_surface + close_tag_str + rest
                else:
                    new_text += tag_str + part
            else:
                new_text += tag_str + part
                
        text = new_text
        
    return text

def auto_tag_manifest_fields(tagged_text, manifest):
    if not tagged_text or not manifest:
        return tagged_text
        
    all_surfaces = []
    for e in manifest:
        fld = e["field"]
        for s in e.get("surfaces", []):
            if s.strip() and len(s.strip()) > 1:
                all_surfaces.append((s.strip(), fld))
                
    # Sắp xếp theo độ dài giảm dần để khớp các chuỗi dài trước (tránh khớp nửa tên)
    all_surfaces.sort(key=lambda x: -len(x[0]))
    
    for surface, fld in all_surfaces:
        parts = re.split(r'(⟦/?.*?⟧)', tagged_text)
        stack = []
        changed = False
        for i in range(len(parts)):
            part = parts[i]
            if part.startswith('⟦') and part.endswith('⟧'):
                tag_content = part[1:-1]
                if tag_content.startswith('/'):
                    tag_name = tag_content[1:]
                    if stack and stack[-1] == tag_name:
                        stack.pop()
                else:
                    stack.append(tag_content)
            else:
                # Chỉ thay thế nếu nằm ngoài toàn bộ thẻ (stack rỗng)
                if not stack and surface in part:
                    # Tránh khớp từ con bên trong một từ tiếng Việt lớn hơn
                    pattern = r'(?<![a-zA-Z0-9_À-ỹ])' + re.escape(surface) + r'(?![a-zA-Z0-9_À-ỹ])'
                    new_part, count = re.subn(pattern, f"⟦{fld}⟧{surface}⟦/{fld}⟧", part)
                    if count > 0:
                        parts[i] = new_part
                        changed = True
        if changed:
            tagged_text = "".join(parts)
            
    return tagged_text

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
        # Bỏ qua gọi API lập dàn ý để tránh lỗi 529 và tiết kiệm thời gian (lập dàn ý tự động)
        if register == "dialogue":
            outline = """1. Phần mở đầu: Chào hỏi và bắt đầu cuộc đối thoại giữa các nhân vật.
2. Phần nội dung: Trao đổi chi tiết hoàn cảnh có lồng ghép thông tin nhạy cảm liên quan đến thủ tục.
3. Phần kết: Kết thúc cuộc đối thoại hành chính."""
        elif register == "third_person":
            outline = """1. Phần mở đầu: Ghi nhận sự việc từ góc nhìn thứ ba, giới thiệu các nhân vật.
2. Phần nội dung: Tường thuật chi tiết hoàn cảnh có lồng ghép thông tin nhạy cảm liên quan đến thủ tục.
3. Phần kết: Ký tên/ghi rõ chức danh người lập báo cáo."""
        else:
            outline = """1. Phần mở đầu: Tiêu ngữ, thông tin cá nhân người làm đơn.
2. Phần nội dung: Trình bày chi tiết hoàn cảnh có lồng ghép thông tin nhạy cảm liên quan đến thủ tục.
3. Phần kết: Đề xuất kiến nghị và ký tên."""
        
        # Chọn các trường dữ liệu ngẫu nhiên (gồm core fields và target_spi)
        selected_fields = ["full_name", "dob", "cccd", "address", "phone"]
        if target_spi and target_spi not in selected_fields:
            selected_fields.append(target_spi)
            
        # Lấy thêm tối đa 1-2 trường phụ khác sẵn có trong profile và không bị trùng
        available_fields = [f for f in MECHANISM if f not in ("family_name", "middle_name", "given_name") and fl.get(f) is not None and str(fl.get(f)).strip() != ""]
        other_candidates = [f for f in available_fields if f not in selected_fields]
        if other_candidates:
            extra_count = random.randint(0, 1)
            if extra_count > 0:
                extra_fields = random.sample(other_candidates, min(extra_count, len(other_candidates)))
                selected_fields.extend(extra_fields)
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
        draft = sanitize_tags(draft)
        
        # Chiến lược hiệu đính có điều kiện (Conditional Revision):
        # Kiểm tra xem bản nháp (draft) đã có dán nhãn hợp lệ chưa. Nếu hợp lệ thì bỏ qua bước gọi API hiệu đính.
        no_revision = os.environ.get("SECUREPI_NO_REVISION") == "1"
        candidates = [(draft, False)] if no_revision else [(draft, False), (None, True)]
        for candidate_text, is_revised in candidates:
            if is_revised:
                print("      (Bản nháp chưa chuẩn nhãn, đang gọi API hiệu đính...)")
                revision_prompt = build_revision_prompt(filtered_fields_desc_str, banned_fields_desc_str, draft, register)
                raw_revised = call_gemini(revision_prompt, temperature=0.2)
                tagged = clean_output(raw_revised)
            else:
                tagged = candidate_text
            
            # Sửa các lỗi định dạng thẻ đóng mở (nếu có)
            tagged = sanitize_tags(tagged)
            # Tự động đóng các thẻ mở bị quên đóng
            tagged = auto_close_unclosed_tags(tagged, profile)
            
            # We dynamically discover or reuse which fields the LLM actually chose to tag
            allowed_fields = set(selected_fields)
            # Always allow core PII fields to be tagged if the LLM chose to write them
            allowed_fields.update(["full_name", "dob", "cccd", "address", "phone", "email"])
            if "family_relations" in selected_fields:
                allowed_fields.update(["address", "dob", "cccd", "phone", "email"])

            # Tự động bọc nhãn cho các thực thể rò rỉ
            full_manifest = build_manifest_for_used_fields(profile, allowed_fields)
            tagged = auto_tag_manifest_fields(tagged, full_manifest)

            if tagged_fields is None:
                attempt_tagged_fields = set(re.findall(r"⟦([a-zA-Z0-9_]+)⟧", tagged))
                attempt_tagged_fields = attempt_tagged_fields.intersection(allowed_fields)
                
                # Bắt buộc các trường critical hoặc SPI được chọn nếu xuất hiện trong văn bản thì phải được dán nhãn
                required_to_tag = {f for f in selected_fields if (f in CRITICAL or SENS.get(f) == "SPI") and fl.get(f) is not None and str(fl.get(f)).strip() != ""}
                
                clean_text_draft = re.sub(r"⟦/?.*?⟧", "", tagged)
                leaked = False
                for f in required_to_tag:
                    if f not in attempt_tagged_fields:
                        f_manifest = build_manifest_for_used_fields(profile, {f})
                        if f_manifest:
                            surfaces = f_manifest[0].get("surfaces", [])
                            if any(s.strip() and s.strip() in clean_text_draft for s in surfaces):
                                leaked = True
                                break
                                
                if leaked:
                    ext_ok_override = False
                else:
                    ext_ok_override = True
            else:
                attempt_tagged_fields = set(tagged_fields)
                allowed_fields.update(attempt_tagged_fields)
                ext_ok_override = True
            
            # Build manifest containing ONLY these used fields
            manifest = build_manifest_for_used_fields(profile, attempt_tagged_fields)
            
            # Choose a random surface variant for matching validation
            for e in manifest:
                if e.get("surfaces"):
                    e["prompt_surface"] = random.choice(e["surfaces"])
                else:
                    e["prompt_surface"] = ""
                    
            ext = extract_anchor_tags(tagged, [e["field"] for e in manifest if e.get("anchor")])
            if not ext_ok_override:
                ext["ok"] = False
            
            # Restrict spans to only allowed_fields
            ext["spans"] = [s for s in ext["spans"] if s["field"] in allowed_fields]
            
            clean = ext["clean_text"]
            
            # Coverage check (strictly on the dynamically constructed manifest)
            miss = coverage(clean, manifest)
            important = [f for f in miss if (f in CRITICAL or SENS.get(f) == "SPI") and f in selected_fields]
            last = (manifest, clean, ext, miss, attempt_tagged_fields)
            
            # Nếu thẻ hợp lệ và không thiếu trường quan trọng, bỏ qua bước tiếp theo
            if ext["ok"] and not important:
                break
        
        # Nếu đạt chuẩn ở bất kỳ bước nào trong vòng lặp candidate, thoát khỏi vòng lặp retry
        if last[2]["ok"] and not [f for f in last[3] if (f in CRITICAL or SENS.get(f) == "SPI") and f in selected_fields]:
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
    valid_forms = sorted(valid_forms, key=lambda x: x.get("template_id", ""))
    # Xáo trộn ngẫu nhiên biểu mẫu một cách xác định
    random.Random(42).shuffle(valid_forms)
    
    if not valid_forms:
        print("Không tìm thấy biểu mẫu hợp lệ nào trong form.json!")
        sys.exit(1)
        
    print(f"Tìm thấy {len(valid_forms)} biểu mẫu chứa văn bản mẫu trong form.json")
    
    # Nạp toàn bộ ngân hàng hồ sơ
    pool = load_profiles(80000)
    profile_lookup = {p["profile_id"]: p for p in pool}
    form_lookup = {f["template_id"]: f for f in valid_forms}
    
    # Lọc hồ sơ người lớn (18-85 tuổi) và sắp xếp tăng dần theo ID để đảm bảo thứ tự cố định
    adult_pool = [p for p in pool if (_age(pfields(p)) or 0) >= 18 and (_age(pfields(p)) or 999) <= 85]
    adult_pool = sorted(adult_pool, key=lambda x: x.get("profile_id", ""))
    # Xáo trộn ngẫu nhiên hồ sơ một cách xác định
    random.Random(100).shuffle(adult_pool)
    
    offset = int(os.environ.get("SECUREPI_OFFSET", "0"))
    total_needed = offset + n
    
    # Xác định chỉ số bắt đầu của hồ sơ cá nhân
    prof_offset = os.environ.get("SECUREPI_PROF_OFFSET")
    if prof_offset is not None:
        prof_start_idx = int(prof_offset)
    else:
        # Tự động phân chia dải hồ sơ dựa trên mô hình chạy để tránh trùng lặp
        if "glm-5" in MODEL or "kr/glm-5" in MODEL:
            prof_start_idx = 8263  # Model B (GLM-5) dùng dải hồ sơ thứ 2
        elif "deepseek-v4" in MODEL or "v4-flash" in MODEL:
            prof_start_idx = 16526 # Model C (DeepSeek V4) dùng dải hồ sơ thứ 3
        else:
            prof_start_idx = 0     # Model A (DeepSeek V3) hoặc mặc định dùng dải hồ sơ thứ 1
            
    print(f"Phân hoạch hồ sơ: Bắt đầu từ chỉ mục {prof_start_idx} trong ngân hàng {len(adult_pool)} hồ sơ người lớn.")
    
    out_name = os.environ.get("SECUREPI_OUT_NAME", "dataset.jsonl")
    ds = OUT / out_name
    
    # Định nghĩa file kế hoạch phát sinh (plan file)
    plan_override = os.environ.get("SECUREPI_PLAN_PATH")
    if plan_override:
        plan_path = Path(plan_override)
        if not plan_path.is_absolute():
            plan_path = OUT / plan_override
    else:
        plan_name = out_name.rsplit(".", 1)[0] + "_plan.json"
        plan_path = OUT / plan_name
    
    # Khởi tạo file trống ban đầu nếu là kế hoạch hoàn toàn mới và chạy từ offset 0
    if not plan_path.exists() and offset == 0:
        ds.write_text("", encoding="utf-8")
        
    plan = []
    if plan_path.exists():
        print(f"Phát hiện file kế hoạch cũ tại {plan_path}, đang tải...")
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Không thể đọc file kế hoạch cũ: {e}")
            
    # Nếu chưa có kế hoạch hoặc kế hoạch hiện tại ít dòng hơn số lượng yêu cầu total_needed, ta tạo/mở rộng kế hoạch
    if len(plan) < total_needed:
        print(f"Đang lập kế hoạch sinh mới/mở rộng cho {total_needed} dòng...")
        
        # Quét toàn bộ các file plan khác để thu thập các profile_id đã được sử dụng
        used_profile_ids = set()
        for p in OUT.glob("*_plan.json"):
            if p.resolve() == plan_path.resolve():
                continue
            try:
                other_plan = json.loads(p.read_text(encoding="utf-8"))
                for item in other_plan:
                    pid = item.get("profile_id")
                    if not pid and "profile" in item:
                        pid = item["profile"].get("profile_id")
                    if pid:
                        used_profile_ids.add(pid)
            except Exception as e:
                print(f"Bỏ qua đọc plan {p.name} khi quét trùng lặp: {e}")
                
        print(f"Phát hiện {len(used_profile_ids)} hồ sơ đã được lên kế hoạch ở các plan khác. Tiến hành loại bỏ trùng lặp...")
        available_adult_pool = [p for p in adult_pool if p.get("profile_id") not in used_profile_ids]
        print(f"Số lượng hồ sơ người lớn còn lại khả dụng: {len(available_adult_pool)}")
        
        if not available_adult_pool:
            print("LỖI: Không còn hồ sơ người lớn nào khả dụng để lập kế hoạch!")
            sys.exit(1)
            
        while len(plan) < total_needed:
            idx = len(plan)
            # Chọn biểu mẫu và hồ sơ hoàn toàn tuần tự/xác định từ pool khả dụng đã loại trùng
            form_meta = valid_forms[idx % len(valid_forms)]
            profile = available_adult_pool[(prof_start_idx + idx) % len(available_adult_pool)]
            pid = profile.get("profile_id")
            
            # Xác định trường SPI nhạy cảm mục tiêu một cách xác định
            dom = form_meta.get("domain", "economy_tech_other")
            target_candidates = DOMAIN_SPI_MAP.get(dom, [])
            fl = pfields(profile)
            available_target_spis = [f for f in target_candidates if fl.get(f) and str(fl.get(f)).strip()]
            if not available_target_spis:
                all_spis = [f for f in MECHANISM if SENS.get(f) == "SPI"]
                available_target_spis = [f for f in all_spis if fl.get(f) and str(fl.get(f)).strip()]
            
            target_spi = available_target_spis[idx % len(available_target_spis)] if available_target_spis else None
            
            plan.append({
                "index": idx,
                "profile_id": pid,
                "template_id": form_meta["template_id"],
                "target_spi": target_spi
            })
            
        plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Đã lưu kế hoạch sinh tại: {plan_path}")
        
    # Đọc danh sách các bản ghi đã được sinh thành công trước đó trong dataset
    generated_keys = set()
    if ds.exists():
        try:
            with open(ds, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        generated_keys.add((rec.get("profile_id"), rec.get("template_id")))
        except Exception as e:
            print(f"Lỗi khi đọc tệp tin dataset cũ: {e}")
            
    import threading
    from concurrent.futures import ThreadPoolExecutor

    write_lock = threading.Lock()
    workers = int(os.environ.get("SECUREPI_WORKERS", "1"))

    def process_item(i):
        item = plan[i]
        pid = item["profile_id"]
        tid = item["template_id"]
        target_spi = item["target_spi"]
        
        # Kiểm tra xem dòng này đã sinh chưa
        if (pid, tid) in generated_keys:
            return (pid, "Đã có", "-", "SKIPPED", "")
            
        profile = profile_lookup.get(pid)
        form_meta = form_lookup.get(tid)
        
        if not profile or not form_meta:
            print(f"[{i+1}/{total_needed}] LỖI: Không tìm thấy profile {pid} hoặc form {tid} trong hệ thống!")
            return (pid, "Lỗi lookup", "-", "ERR", "Missing metadata")
            
        print_prefix = f"[{i+1}/{total_needed}] {pid} | Biểu mẫu: {form_meta['record_type'][:30]} | SPI: {target_spi or 'None'}"
        try:
            rec = generate_one(profile, form_meta, target_spi=target_spi)
            rec_json = json.dumps(rec, ensure_ascii=False)
            
            # Ghi trực tiếp dòng này vào file dưới sự bảo vệ của write_lock
            with write_lock:
                with open(ds, "a", encoding="utf-8") as f:
                    f.write(rec_json + "\n")
                    
            m = rec["meta"]
            print(f"{print_prefix} -> OK ({m['n_spans']} nhãn)")
            return (pid, form_meta["record_type"][:30], m["n_spans"], m["tag_ok"], m["missing_coverage"])
        except Exception as e:
            print(f"{print_prefix} -> LỖI: {e}")
            return (pid, form_meta["record_type"][:30], "-", "ERR", str(e)[:50])

    # Lọc ra danh sách các chỉ mục cần sinh thực tế
    indices_to_process = []
    summary = []
    for i in range(offset, total_needed):
        item = plan[i]
        pid = item["profile_id"]
        tid = item["template_id"]
        if (pid, tid) in generated_keys:
            summary.append((pid, "Đã có", "-", "SKIPPED", ""))
        else:
            indices_to_process.append(i)

    print(f"Bắt đầu xử lý dải dòng từ chỉ mục {offset} đến {total_needed - 1}...")
    print(f"Đã sinh trong dataset: {len(generated_keys)} dòng.")
    print(f"Số dòng cần sinh mới thực tế: {len(indices_to_process)} dòng.")
    print(f"Model: {MODEL} | sinh dữ liệu theo kế hoạch với {workers} luồng\n")
    
    if indices_to_process:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = executor.map(process_item, indices_to_process)
            for res in results:
                summary.append(res)
            
    print("\n" + "=" * 60)
    ok_cnt = sum(1 for s in summary if s[3] is True or s[3] == "SKIPPED")
    print(f"Hoàn thành tiến trình! Thành công: {ok_cnt}/{n} dòng thuộc dải yêu cầu (bao gồm các dòng đã sinh trước đó).")
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
