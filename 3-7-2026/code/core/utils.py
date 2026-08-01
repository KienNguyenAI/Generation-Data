# -*- coding: utf-8 -*-
import re

def _stable_hash(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) % (2**32)
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

NOW_YEAR = 2026
def _age(fl):
    try:
        return NOW_YEAR - int(str(fl.get("dob", "")).split("/")[-1])
    except Exception:
        return None

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
