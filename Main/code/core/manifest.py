# -*- coding: utf-8 -*-
import re
from core.config import MECHANISM, SENS, FIELDS, SENTINEL, pfields, BIRTH_CUES, CUE_WORDS
from core.utils import (
    split_vietnamese_name, render_cccd, render_phone, render_address,
    render_full_name, render_dob, render_political_view, render_religion,
    generate_fallback_value, _stable_hash
)

def extract_core_alias_name(val):
    if not val:
        return ""
    val = str(val).strip()
    prefixes = [
        "thường gọi là", "còn được gọi là", "còn được biết đến với tên gọi khác:",
        "tên gọi khác:", "tên khác:", "pháp danh"
    ]
    for p in prefixes:
        if val.lower().startswith(p):
            val = val[len(p):].strip()
    val = re.sub(r"^[:\s,\-]+", "", val).strip()
    return val

def build_manifest_for_used_fields(profile, tagged_fields):
    fl = pfields(profile)
    full_name_val = fl.get("full_name", "")
    dyn_family, dyn_middle, dyn_given = split_vietnamese_name(full_name_val) if full_name_val else ("", "", "")
    
    # Extract core alias name if present
    alias_val = fl.get("name_alias", "")
    a_fam, a_mid, a_giv = ("", "", "")
    if alias_val:
        core_alias = extract_core_alias_name(alias_val)
        if core_alias:
            a_fam, a_mid, a_giv = split_vietnamese_name(core_alias)

    used = set(tagged_fields)
    # If LLM used full_name or name_alias, we add individual name components
    # to allow annotate to perform post-hoc name splitting correctly
    if "full_name" in used or "name_alias" in used:
        used.update(["family_name", "middle_name", "given_name"])
        
    manifest = []
    name_parts = {"family_name", "middle_name", "given_name"}
    
    for field in used:
        if field not in MECHANISM:
            continue
        
        m = MECHANISM.get(field, "verbatim")
        label = SENS.get(field, "PII")
        name_vi = (FIELDS.get(field) or {}).get("name_vi", field)
        
        if field in name_parts:
            surfaces = []
            if field == "family_name":
                if dyn_family: surfaces.append(dyn_family)
                if a_fam: surfaces.append(a_fam)
            elif field == "middle_name":
                if dyn_middle:
                    surfaces.append(dyn_middle)
                    parts = dyn_middle.split()
                    if len(parts) > 1:
                        surfaces.extend(parts)
                if a_mid:
                    surfaces.append(a_mid)
                    parts = a_mid.split()
                    if len(parts) > 1:
                        surfaces.extend(parts)
            elif field == "given_name":
                if dyn_given:
                    surfaces.append(dyn_given)
                    parts = dyn_given.split()
                    if len(parts) > 1:
                        surfaces.extend(parts)
                if a_giv:
                    surfaces.append(a_giv)
                    parts = a_giv.split()
                    if len(parts) > 1:
                        surfaces.extend(parts)
            
            surfaces = list(dict.fromkeys([s for s in surfaces if s]))
            if not surfaces:
                continue
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces})
            continue
            
        val = fl.get(field)
        if val is None or str(val).strip() == "":
            continue
        val = str(val).strip()
        
        is_anchor = (m == "anchor_tag" or val == SENTINEL)
        
        if is_anchor:
            manifest.append({
                "field": field,
                "label": label,
                "name_vi": name_vi,
                "mechanism": m,
                "anchor": True,
                "seed_value": None if val == SENTINEL else val
            })
        else:
            if m == "verbatim":
                if field == "cccd": surfaces = render_cccd(val)
                elif field == "phone": surfaces = render_phone(val)
                elif field == "address": surfaces = render_address(val)
                elif field == "full_name": surfaces = render_full_name(val)
                else: surfaces = [val]
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces})
            elif m == "date":
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": render_dob(val), "cue_words": BIRTH_CUES})
            elif m == "cue_context":
                surfaces = [val]
                if field == "political_view":
                    surfaces = render_political_view(val)
                elif field == "religion":
                    surfaces = render_religion(val)
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces, "cue_words": CUE_WORDS.get(field, [])})
            else:
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": [val]})
                
    for e in manifest:
        e["derived"] = (e["field"] in name_parts and e["field"] not in ["full_name"])
        
    return manifest

def build_manifest(profile, scenario):
    fl = pfields(profile)
    want = (set(scenario.get("cooccur_fields", [])) | set(scenario.get("spi_targets", []))) - {"political_view"}
    name_parts = {"family_name", "middle_name", "given_name"}
    
    full_name_val = fl.get("full_name", "")
    dyn_family, dyn_middle, dyn_given = split_vietnamese_name(full_name_val) if full_name_val else ("", "", "")
    
    manifest = []
    
    for field in MECHANISM:
        if not (field in want or (field in name_parts and "full_name" in want)):
            continue
        
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
            if not val:
                continue
            
        m = MECHANISM[field]
        if val == SENTINEL:
            m = "anchor_tag"   # sentinel -> LLM SINH + bọc thẻ, KHÔNG verbatim
        label = SENS.get(field, "PII")
        name_vi = (FIELDS.get(field) or {}).get("name_vi", field)
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

def realize_supplemental(profile, scenario, profiles, base_seed):
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
                if "family_relations" not in fields:
                    fields.append("family_relations")
            if a.get("with_address") and "address" not in fields:
                fields.append("address")
                
            sub_lines = []
            full_name_val2 = fl2.get("full_name", "")
            dyn_family2, dyn_middle2, dyn_given2 = split_vietnamese_name(full_name_val2) if full_name_val2 else ("", "", "")
            
            for f in fields:
                is_derived = (f in ["family_name", "middle_name", "given_name", "family_relations"] and has_fullname and f not in a.get("fields", []))
                
                if f == "family_name" and dyn_family2:
                    val = dyn_family2
                elif f == "middle_name" and dyn_middle2:
                    val = dyn_middle2
                elif f == "given_name" and dyn_given2:
                    val = dyn_given2
                elif f == "family_relations" and full_name_val2:
                    val = full_name_val2
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
                elif f == "family_relations":
                    surfaces = [
                        f"{rel} là {full_name_val2}",
                        f"{rel} của tôi là {full_name_val2}",
                        f"{rel}, {full_name_val2}",
                        f"người {rel} là {full_name_val2}",
                        f"người {rel} của tôi là {full_name_val2}"
                    ]
                    if rel == "con":
                        surfaces.append(f"con tôi là {full_name_val2}")
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
