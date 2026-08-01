# -*- coding: utf-8 -*-
"""
SecurePrep — BỘ PHÂN LOẠI DOMAIN CHO BIỂU MẪU (Form Domain Classifier)
Tự động gán lĩnh vực (domain) cho các biểu mẫu trong form.json và lưu thành form_domains.json.
"""
import json
import re
import sys
from pathlib import Path

# reconfigure stdout for utf-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CODE_DIR = Path(__file__).resolve().parent
DATA_DIR = CODE_DIR.parent.parent / "data"

p_form = DATA_DIR / "form.json"
p_out = DATA_DIR / "form_domains.json"

def clean_record_type(text):
    text = text.lower()
    text = text.replace("trường hợp", " ")
    text = text.replace("khoa học", " ")
    text = text.replace("sinh học", " ")
    text = text.replace("hóa học", " ")
    text = text.replace("y học", " ")
    text = text.replace("du học", "study_abroad")
    return text

def classify_domain(record_type, agency):
    rt = clean_record_type(record_type)
    ag = (agency or "").lower()
    
    # 1. Y tế & Sức khỏe (medical_healthcare)
    medical_kw = [
        r"\by tế\b", r"\bbệnh\b", r"\bviện\b", r"\bkhám\b", r"\bchữa\b", r"\bdược\b", 
        r"\bthuốc\b", r"\bsức khỏe\b", r"\bthương tật\b", r"\bkhuyết tật\b", 
        r"\bgiám định y khoa\b", r"\bx-quang\b", r"\bbức xạ\b", r"\bphóng xạ\b", 
        r"\bsinh con\b", r"\bthai sản\b", r"\bbệnh án\b"
    ]
    if any(re.search(kw, rt) for kw in medical_kw) or "y tế" in ag:
        return "medical_healthcare"
        
    # 2. Bảo hiểm & An sinh (insurance_welfare)
    insurance_kw = [
        r"\bbảo hiểm\b", r"\bbhyt\b", r"\bbhxh\b", r"\btrợ cấp\b", r"\bhộ nghèo\b", 
        r"\bnghèo\b", r"\bkhó khăn\b", r"\bmiễn giảm\b"
    ]
    if any(re.search(kw, rt) for kw in insurance_kw) or "bảo hiểm" in ag:
        return "insurance_welfare"
        
    # 3. Tư pháp & Pháp lý (justice_legal)
    rt_no_toanha = rt.replace("tòa nhà", " ")
    justice_kw = [
        r"\btư pháp\b", r"\blý lịch\b", r"\bán\b", r"\btội\b", r"\btòa\b", 
        r"\bvi phạm\b", r"\bnhập ngũ\b", r"\bquân sự\b", r"\bnghĩa vụ\b", 
        r"\bphòng cháy\b", r"\bchữa cháy\b", r"\ban ninh\b", r"\btuyển dụng\b", 
        r"\bcông an\b", r"\bquốc phòng\b"
    ]
    if any(re.search(kw, rt_no_toanha) for kw in justice_kw) or "công an" in ag or "tư pháp" in ag or "quốc phòng" in ag:
        return "justice_legal"
        
    # 4. Hộ tịch & Gia đình (civil_family)
    civil_kw = [
        r"\bkhai sinh\b", r"\bkhai tử\b", r"\bkết hôn\b", r"\bly hôn\b", r"\bhộ tịch\b", 
        r"\btạm trú\b", r"\bthường trú\b", r"\bcư trú\b", r"\bnhân thân\b", r"\bgia đình\b",
        r"\bmâu thuẫn\b"
    ]
    if any(re.search(kw, rt) for kw in civil_kw):
        return "civil_family"
        
    # 5. Giáo dục & Đào tạo (education_training)
    edu_kw = [
        r"\bgiáo dục\b", r"\btrường\b", r"\blớp\b", r"\bhọc đường\b", r"\bhọc sinh\b", 
        r"\bsinh viên\b", r"\bhọc tập\b", r"\bhọc viện\b", r"\bgiảng dạy\b", 
        r"\bdạy học\b", r"study_abroad"
    ]
    if any(re.search(kw, rt) for kw in edu_kw) or "giáo dục" in ag:
        return "education_training"
        
    # 6. Tôn giáo & Dân tộc (religion_ethnicity)
    rel_kw = [
        r"\btôn giáo\b", r"\bđạo\b", r"\btín ngưỡng\b", r"\bdân tộc\b", r"\bđồng bào\b", 
        r"\bkhmer\b", r"\bchùa\b", r"\bnhà thờ\b", r"\bphật giáo\b", r"\bthiên chúa\b"
    ]
    if any(re.search(kw, rt) for kw in rel_kw) or "tôn giáo" in ag or "dân tộc" in ag:
        return "religion_ethnicity"
        
    # 7. Kinh tế, Kỹ thuật & Khác (economy_tech_other) - Mặc định
    return "economy_tech_other"

def main():
    if not p_form.exists():
        print(f"Không tìm thấy file {p_form}!")
        sys.exit(1)
        
    print(f"Đang đọc {p_form}...")
    with open(p_form, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    valid_forms = [item for item in data if item.get("template_id") and item.get("record_type") and any(f.get("form_raw_text") for f in item.get("attached_forms", []))]
    
    print(f"Đang phân loại {len(valid_forms)} biểu mẫu...")
    mapping = {}
    counts = {}
    
    for item in valid_forms:
        tid = item["template_id"]
        dom = classify_domain(item["record_type"], item.get("agency"))
        mapping[tid] = dom
        counts[dom] = counts.get(dom, 0) + 1
        
    print(f"Đang lưu file mapping vào {p_out}...")
    with open(p_out, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
        
    print("\n=== THÀNH CÔNG! THỐNG KÊ PHÂN BỔ ===")
    for dom, c in counts.items():
        pct = (c / len(valid_forms)) * 100
        print(f"- {dom:<25}: {c:<5} ({pct:.2f}%)")

if __name__ == "__main__":
    main()
