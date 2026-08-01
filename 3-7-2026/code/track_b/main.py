# -*- coding: utf-8 -*-
import json
import re
import sys
import random
from pathlib import Path

# Add project code folder to path to allow core & track_b imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import (
    OUT, MODEL, SENS, FIELDS, MECHANISM, CUE_WORDS, BIRTH_CUES, CRITICAL, SENTINEL,
    load_profiles, pfields, load_all_form_metadata, get_form_metadata, get_all_form_metadata, CATALOG
)
from core.utils import _age
from core.manifest import build_manifest, realize_supplemental
from core.api import call_gemini, clean_output
from core.annotation import extract_anchor_tags, annotate, coverage
from track_b.prompts import build_outline_prompt, build_draft_prompt, build_revision_prompt

# Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def find_matching_template(scenario):
    if not get_all_form_metadata():
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
    for tid, meta in get_all_form_metadata().items():
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
    return random.choice(list(get_all_form_metadata().keys()))

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
    outline_prompt = build_outline_prompt(scenario, manifest, supplements, form_meta)
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
        draft_prompt = build_draft_prompt(scenario, manifest, supplements, outline, form_meta)
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

    ds = OUT / "dataset_v2.jsonl"
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 84)
    print(f"{'#':<3}{'profile':<11}{'scenario':<22}{'spans':<7}{'tag_ok':<8}missing")
    print("-" * 84)
    for i, (pid, sid, ns, ok, ms) in enumerate(summary, 1):
        print(f"{i:<3}{pid:<11}{sid:<22}{str(ns):<7}{str(ok):<8}{ms}")
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"\n{ok_cnt}/{n} tag_ok. Dataset v2 gộp -> {ds}")

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
            
    ds = OUT / "dataset_v2.jsonl"
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"{'#':<3}{'profile':<11}{'scenario (register)':<35}{'spans':<7}{'tag_ok':<8}missing")
    print("-" * 90)
    for i, (pid, sid, ns, ok, ms) in enumerate(summary, 1):
        print(f"{i:<3}{pid:<11}{sid:<35}{str(ns):<7}{str(ok):<8}{ms}")
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"\n{ok_cnt}/{n} tag_ok. Dataset v2 gộp -> {ds}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "register":
        run_batch_by_register(2)
    else:
        n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
        run_batch(n)
