# -*- coding: utf-8 -*-
"""
build_profiles.py — Đúc profile_bank (two-stage generation).

Ăn:  profile_core.json (từ vựng)  +  pii_schema.json (format/builder/value_pool + nhãn)
Đẻ:  profile_bank.jsonl  (mỗi dòng 1 profile đã validate + consistency + quasi-key)

KHÔNG dùng synthetic_output.json. Mọi field SPI lấy value_pool/weights TỪ SCHEMA
(không hard-code) => đa dạng, chống sập. CCCD/GPLX suy từ dob+gender (đúng cấu trúc).

Chạy:  python build_profiles.py --n 30000 --out profile_bank.jsonl --seed 42
"""
import json, random, argparse, re, datetime, unicodedata, sys
from collections import Counter, defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ----------------------------------------------------------------------------- helpers
def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def wchoice(rng, d):
    """weighted choice từ dict {key: weight} hoặc list[(key,w)]."""
    items = list(d.items()) if isinstance(d, dict) else list(d)
    keys = [k for k, _ in items]; ws = [float(w) for _, w in items]
    return rng.choices(keys, weights=ws, k=1)[0]

def deaccent(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("Đ", "D").replace("đ", "d")

def slug(s):
    return re.sub(r"[^a-z0-9.]", "", deaccent(s).lower().replace(" ", "."))

def rand_digits(rng, n):
    return "".join(str(rng.randint(0, 9)) for _ in range(n))

def gen_from_regex(rng, pat):
    """Sinh chuỗi ngẫu nhiên khớp pattern ĐƠN GIẢN dùng trong schema placeholders:
       hỗ trợ \\d{n} \\d{a,b} \\d [A-Z] nhóm (...)? và literal."""
    out = []; i = 0; n = len(pat)
    while i < n:
        c = pat[i]
        if c == "\\" and i + 1 < n and pat[i+1] == "d":
            i += 2
            lo = hi = 1
            if i < n and pat[i] == "{":
                j = pat.index("}", i); spec = pat[i+1:j]; i = j + 1
                if "," in spec: lo, hi = map(int, spec.split(","))
                else: lo = hi = int(spec)
            out.append(rand_digits(rng, rng.randint(lo, hi)))
        elif c == "[":
            j = pat.index("]", i); cls = pat[i+1:j]; i = j + 1
            if cls == "A-Z": ch = chr(rng.randint(65, 90))
            elif cls == "0-9": ch = str(rng.randint(0, 9))
            else: ch = cls[0]
            if i < n and pat[i] == "{":
                j = pat.index("}", i); cnt = int(pat[i+1:j]); i = j + 1
                ch = "".join(chr(rng.randint(65,90)) if cls=="A-Z" else str(rng.randint(0,9)) for _ in range(cnt))
            out.append(ch)
        elif c == "(":
            j = pat.index(")", i); grp = pat[i+1:j]; i = j + 1
            opt = i < n and pat[i] == "?"
            if opt: i += 1
            if (not opt) or rng.random() < 0.5:
                out.append(gen_from_regex(rng, grp))
        else:
            out.append(c); i += 1
    return "".join(out)

# ----------------------------------------------------------------------------- date
def rand_dob(rng, core, min_year=None, max_year=None):
    years = {y: w for y, w in core["birth_year_weights"].items()
             if (min_year is None or int(y) >= min_year) and (max_year is None or int(y) <= max_year)}
    y = int(wchoice(rng, years))
    m = rng.randint(1, 12)
    if m == 2:
        dmax = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    elif m in (4, 6, 9, 11): dmax = 30
    else: dmax = 31
    d = rng.randint(1, dmax)
    return d, m, y

def fmt_dob(d, m, y, sep="/"):
    return f"{d:02d}{sep}{m:02d}{sep}{y}"

# ----------------------------------------------------------------------------- name
def build_name(rng, core, ethnicity, gender):
    """Trả family_name (họ) + middle_name (chữ đệm) + given_name (tên)."""
    g = "Nam" if gender == "Nam" else ("Nu" if gender == "Nữ" else rng.choice(["Nam", "Nu"]))
    order = "surname_first"
    no = core["name_order_by_ethnic"]
    if ethnicity in no["given_first"]: order = "given_first"
    elif ethnicity in no["given_only"]: order = "given_only"

    fam = mid = giv = ""
    if order == "given_only":
        giv = rng.choice(core["ten"][g])
        full = giv
    elif ethnicity == "Ê Đê":
        pre = "Y" if g == "Nam" else "H'"
        base = rng.choice(core["ten_dan_toc"]["ede_ten"])
        fam = rng.choice(core["ho_dan_toc"]["Ê Đê"])
        giv = f"{pre} {base}" if pre == "Y" else f"{pre}{base}"
        full = f"{giv} {fam}"
    elif ethnicity == "Gia Rai":
        fam = rng.choice(core["ho_dan_toc"]["Gia Rai"])
        giv = rng.choice(core["ten_dan_toc"]["giarai_ten"] + core["ten"][g])
        full = f"{fam} {giv}"            # tên-trước-họ-sau, họ là cụm Rơ Châm/Siu...
    else:
        # surname_first (Kinh + đa số)
        if ethnicity in core["ho_dan_toc"]:
            fam = rng.choice(core["ho_dan_toc"][ethnicity])
        elif rng.random() < 0.03:
            fam = rng.choice(core["ho_kep"])
        else:
            fam = wchoice(rng, core["ho"])
        if rng.random() < 0.75:                                  # chữ đệm (có thể bỏ); đôi khi 2 token
            mid = rng.choice(core["ten_dem"][g])
            if rng.random() < 0.15:
                mid = mid + " " + rng.choice(core["ten_dem"][g])
        pool = list(core["ten"][g])
        if ethnicity == "Khmer": pool += core["ten_dan_toc"]["khmer_ten"]
        if ethnicity == "Chăm":  pool += core["ten_dan_toc"]["cham_ten"]
        if ethnicity == "Mông":  pool += core["ten_dan_toc"]["mong_ten"]
        giv = rng.choice(pool)
        full = " ".join(x for x in [fam, mid, giv] if x)
    return {"full_name": full, "family_name": fam, "middle_name": mid, "given_name": giv, "name_order": order}

# ----------------------------------------------------------------------------- geo / address
def pick_province(rng, core):
    # trọng số = pop * vung_weight
    vw = core["vung_weights"]
    weights = {name: info["pop"] * vw.get(info["region"], 0.1) for name, info in core["tinh_2025"].items()}
    return wchoice(rng, weights)

def build_address(rng, core, province, ood=False):
    info = core["tinh_2025"][province]
    prov_label = ("thành phố " if info["type"] == "thành phố" else "tỉnh ") + province
    if ood and rng.random() < 0.5:
        # OOD: đặc khu đảo / vùng xa / nước ngoài
        bucket = rng.choice(["dac_khu_dao", "vung_xa", "nuoc_ngoai"])
        place = rng.choice(core["extended_places"][bucket])
        if bucket == "nuoc_ngoai":
            return {"text": place, "house_number": "", "street": "", "ward": "", "province": "", "scheme": "ood_foreign"}
        return {"text": f"{place}, {prov_label}", "house_number": "", "street": "", "ward": place, "province": prov_label, "scheme": "ood_remote"}

    house = f"số {rng.randint(1, 350)}" + (rng.choice(["", "", f"/{rng.randint(1,40)}", f"/{rng.randint(1,40)}{rng.choice('AB')}"]))
    street = "đường " + rng.choice(core["duong_names"])
    urban = info["type"] == "thành phố" or rng.random() < 0.45
    if urban:
        ward = "phường " + rng.choice(core["phuong_names"])
    else:
        ward = "xã " + rng.choice(core["xa_names"])
    legacy = rng.random() < 0.18  # một phần hồ sơ cũ 3 cấp
    if legacy:
        district = ("quận " + str(rng.randint(1, 12))) if urban else ("huyện " + rng.choice(core["xa_names"]))
        text = f"{house} {street}, {ward}, {district}, {prov_label}"
        scheme = "legacy_3cap"
    else:
        # đôi khi có thôn/xóm cho vùng nông thôn
        ham = (rng.choice(core["hamlet_pool"]) + ", ") if (not urban and rng.random() < 0.4) else ""
        text = f"{house} {street}, {ham}{ward}, {prov_label}"
        scheme = "new_2cap"
    return {"text": text, "house_number": house, "street": street, "ward": ward, "province": prov_label, "scheme": scheme}

# ----------------------------------------------------------------------------- ID builders
def century_gender_digit(rng, gender, year):
    base = {1900: 0, 2000: 2, 2100: 4}[(year // 100) * 100] if (year // 100) * 100 in (1900, 2000, 2100) else 0
    if gender == "Nam": off = 0
    elif gender == "Nữ": off = 1
    else: off = rng.choice([0, 1])
    return str(base + off)

def build_cccd(rng, core, cccd_code, gender, year):
    cg = century_gender_digit(rng, gender, year)
    yy = f"{year % 100:02d}"
    seq = rand_digits(rng, 6)
    # tránh chuỗi quá 'sạch'
    if seq in ("000000", "123456", "111111"): seq = rand_digits(rng, 6)
    return cccd_code + cg + yy + seq

def build_gplx(rng, cccd_code, gender, year):
    prov2 = cccd_code[1:]  # bỏ số 0 đầu -> 2 số
    cg = century_gender_digit(rng, gender, year)
    exam_year = rng.randint(year + 18, 2025)
    return f"{prov2}{cg}{exam_year % 100:02d}{rand_digits(rng, 7)}"

def build_phone(rng, core):
    carrier = wchoice(rng, core["carrier_weights"])
    pre = rng.choice(core["phone_prefix_by_carrier"][carrier])
    return pre + rand_digits(rng, 7)

def build_plate(rng, core, province):
    code = rng.choice(core["tinh_2025"][province]["plate"])
    series = rng.choice("ABCDEFGHKLMNPSTUVXYZ")
    if rng.random() < 0.6:
        return f"{code}{series}-{rand_digits(rng,3)}.{rand_digits(rng,2)}"
    return f"{code}{series}-{rand_digits(rng,5)}"

def build_bank_account(rng, core):
    """Số TK độ dài BIẾN THIÊN theo ngân hàng (6-19) hoặc số thẻ 16 số — khớp diversity của schema."""
    if rng.random() < 0.25:
        return f"9704 {rand_digits(rng,4)} {rand_digits(rng,4)} {rand_digits(rng,4)}"  # thẻ NAPAS giả
    return rand_digits(rng, rng.choice([8, 9, 10, 11, 12, 13, 13, 14, 14, 16, 19]))

print("build_profiles PART A ok")

# ----------------------------------------------------------------------------- schema-driven field realizer
_REF_ALIAS = {"health": "healthcare"}
_FALLBACK_POOLS = {
    "hospitals": ["Bệnh viện Bạch Mai", "Bệnh viện Đa khoa tỉnh", "Bệnh viện Chợ Rẫy", "Bệnh viện Đại học Y Hà Nội", "Trung tâm Y tế huyện"],
    "banks": ["Vietcombank", "BIDV", "Agribank", "Techcombank", "MB Bank"],
    "conditions": ["tăng huyết áp", "tiểu đường type 2", "hen phế quản"],
}
def _deep_find_list(obj, key):
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], list) and obj[key]:
            return obj[key]
        for v in obj.values():
            r = _deep_find_list(v, key)
            if r: return r
    return None
def resolve_ref(core, ref):
    parts = [_REF_ALIAS.get(p, p) for p in ref.replace("profile_core.", "").split(".")]
    cur = core
    for p in parts:
        cur = cur[p] if isinstance(cur, dict) and p in cur else None
        if cur is None: break
    if isinstance(cur, list) and cur:
        return cur
    leaf = parts[-1]
    return _deep_find_list(core, leaf) or _FALLBACK_POOLS.get(leaf, [])

def short_address(rng, core):
    prov = pick_province(rng, core); info = core["tinh_2025"][prov]
    lab = ("thành phố " if info["type"] == "thành phố" else "tỉnh ") + prov
    ward = ("phường " + rng.choice(core["phuong_names"])) if rng.random() < 0.5 else ("xã " + rng.choice(core["xa_names"]))
    return f"{ward}, {lab}"

def money_vnd(rng):
    amt = rng.choice([rng.randint(1, 50) * 1_000_000, rng.randint(50, 990) * 100_000, rng.randint(1, 30) * 10_000_000])
    return f"{amt:,}".replace(",", ".")

def resolve_type(rng, core, t, spec, ctx):
    if t == "full_name_like":
        g = ctx.get("_name_gender") or rng.choice(["Nam", "Nữ"])
        return build_name(rng, core, "Kinh", g)["full_name"]
    if t == "given_name_like":
        g = ctx.get("_name_gender") or rng.choice(["Nam", "Nữ"])
        return rng.choice(core["ten"]["Nam" if g == "Nam" else "Nu"])
    if t == "phone": return build_phone(rng, core)
    if t == "phone_or_cccd": return ctx.get("cccd") if (ctx.get("cccd") and rng.random() < 0.5) else build_phone(rng, core)
    if t == "address_short": return short_address(rng, core)
    if t == "date":
        r = spec.get("range", [1990, 2024]); y = rng.randint(r[0], r[1])
        d, m = rng.randint(1, 28), rng.randint(1, 12); return fmt_dob(d, m, y)
    if t == "int": lo, hi = spec.get("range", [1, 5]); return str(rng.randint(lo, hi))
    if t == "year": lo, hi = spec.get("range", [1980, 2024]); return str(rng.randint(lo, hi))
    if t == "float":
        lo, hi = spec.get("range", [0, 100]); dec = spec.get("decimals", [4, 6])
        return f"{rng.uniform(lo, hi):.{rng.randint(dec[0], dec[1])}f}"
    if t == "digits": return rand_digits(rng, spec.get("len", 3))
    if t == "money_vnd": return money_vnd(rng)
    if t == "ascii_slug_from_name": return slug(ctx.get("full_name", "nguoi.dung"))
    return ""

def resolve_placeholder(rng, core, token, spec, ctx):
    if not isinstance(spec, dict): return token
    if "const" in spec: return spec["const"]
    if "pool" in spec: return rng.choice(spec["pool"])
    if "pattern" in spec:
        if token == "{ip}":
            return ".".join(str(rng.randint(0, 255)) for _ in range(4))
        if token == "{time}":
            return f"{rng.randint(0, 23)}:{rng.randint(0, 59):02d}"
        return gen_from_regex(rng, spec["pattern"])
    if "ref" in spec:
        opts = resolve_ref(core, spec["ref"]); return rng.choice(opts) if opts else ""
    if "type" in spec: return resolve_type(rng, core, spec["type"], spec, ctx)
    return ""

_RELATION_GENDER = {
    "cha": "Nam", "bố": "Nam", "ba": "Nam", "chồng": "Nam", "con trai": "Nam", "anh trai": "Nam",
    "em trai": "Nam", "ông": "Nam", "chú": "Nam", "bác": "Nam", "cậu": "Nam", "cháu trai": "Nam", "anh": "Nam",
    "mẹ": "Nữ", "má": "Nữ", "vợ": "Nữ", "con gái": "Nữ", "chị gái": "Nữ", "em gái": "Nữ",
    "bà": "Nữ", "cô": "Nữ", "dì": "Nữ", "cháu gái": "Nữ", "chị": "Nữ",
}
_NEUTRAL_REL = ("con là", "con,", "em ruột", "giám hộ", "người liên hệ", "người thân", "cháu")
def _gender_from_relation(text):
    t = text.lower()
    for kw in sorted(_RELATION_GENDER, key=len, reverse=True):   # cụm dài trước ('con trai' trước 'anh')
        if kw in t:
            return _RELATION_GENDER[kw]
    return None
def _name_gender_for(work, ctx, rng):
    g = _gender_from_relation(work)
    if g:
        return g                                                 # quan hệ có giới tính rõ
    low = work.lower()
    if any(w in low for w in _NEUTRAL_REL):
        return rng.choice(["Nam", "Nữ"])                          # người thân trung tính -> ngẫu nhiên
    sg = ctx.get("gender")
    return sg if sg in ("Nam", "Nữ") else rng.choice(["Nam", "Nữ"])  # bí danh chủ thể -> theo chủ thể

def fill(rng, core, text, placeholders, ctx):
    placeholders = placeholders or {}
    work = text
    if "{relation}" in work:                                      # bốc quan hệ TRƯỚC để biết giới tính
        rspec = placeholders.get("{relation}", {})
        rel = rng.choice(rspec["pool"]) if "pool" in rspec else "người thân"
        work = work.replace("{relation}", rel)
    lctx = dict(ctx)
    lctx["_name_gender"] = _name_gender_for(work, ctx, rng)
    def repl(m):
        tok = m.group(0)
        spec = placeholders.get(tok)
        if spec is None:
            name = tok.strip("{}")
            default = {"name": {"type": "full_name_like"}, "given_name": {"type": "given_name_like"},
                       "phone": {"type": "phone"}, "place": {"type": "address_short"},
                       "placeA": {"type": "address_short"}, "placeB": {"type": "address_short"},
                       "date": {"type": "date"}, "year": {"type": "year"}, "amount": {"type": "money_vnd"},
                       "slug": {"type": "ascii_slug_from_name"}, "login": {"type": "phone_or_cccd"},
                       "ten_dang_nhap": {"type": "phone_or_cccd"}}.get(name, {})
            return resolve_placeholder(rng, core, tok, default, lctx)
        return resolve_placeholder(rng, core, tok, spec, lctx)
    return re.sub(r"\{[a-zA-Z0-9_]+\}", repl, work)

_CONNECTORS = ("tại", "số", "ngày", "gần", "là", "của")
def _dangling(s):
    w = s.rstrip().split()
    return bool(w) and w[-1] in _CONNECTORS
def _bad_for_gender(out, ctx):
    return ("mang thai" in out) and ctx.get("gender") != "Nữ"
def realize_field(rng, core, meta, ctx):
    """Sinh giá trị cho field categorical/template_pool LẤY value_pool/weights TỪ SCHEMA.
       Bền vững: re-roll nếu còn {placeholder}, chuỗi cụt (vd 'tại '), hoặc mâu thuẫn giới tính (Nam + 'mang thai')."""
    fmt = meta.get("format") or {}
    pool = fmt.get("value_pool") or fmt.get("value_templates")
    if not pool: return None
    weights = fmt.get("weights")
    out = ""
    for _ in range(8):
        val = wchoice(rng, dict(zip(pool, weights))) if weights and len(weights) == len(pool) else rng.choice(pool)
        out = fill(rng, core, val, fmt.get("placeholders"), ctx)
        if ("{" not in out) and (not _dangling(out)) and (not _bad_for_gender(out, ctx)):
            return out
    w = out.rstrip().split()                       # phương án cuối: cắt connector thừa ở đuôi
    while w and w[-1] in _CONNECTORS:
        w.pop()
    return " ".join(w)

# ----------------------------------------------------------------------------- assemble one profile
def age_bucket(age):
    if age < 22: return "duoi_22"
    if age < 30: return "22_30"
    if age < 50: return "30_50"
    return "tren_50"

def pick_occupation(rng, core, age):
    if age < 18: return "học sinh"
    if age < 23 and rng.random() < 0.5: return "sinh viên"
    if age >= 60 and rng.random() < 0.6: return "hưu trí"
    return rng.choice(core["nghe_nghiep"])

def build_profile(rng, core, PII, idx, this_year=2025, bake_llm=False, llm_scale=1.0):
    ood_flags = []
    ood = rng.random() < 0.08
    # ethnicity
    ethnicity = wchoice(rng, core["dan_toc"])
    if ood and rng.random() < 0.4:
        ethnicity = rng.choice(["Rơ Măm", "Brâu", "Ơ Đu", "Pu Péo", "Si La", "Cống"]); ood_flags.append("rare_ethnicity")
    gender = wchoice(rng, {"Nam": 0.49, "Nữ": 0.49, "Khác": 0.02})
    # dob
    if ood and rng.random() < 0.3:
        d, m, y = rand_dob(rng, core, 1935, 1945) if rng.random() < 0.5 else rand_dob(rng, core, 2018, 2024)
        ood_flags.append("extreme_age")
    else:
        d, m, y = rand_dob(rng, core)
    age = this_year - y
    nm = build_name(rng, core, ethnicity, gender)
    if ood and ethnicity == "Kinh" and rng.random() < 0.3:
        _fn = rng.choice(["John Smith", "Kim Min-jun", "Tanaka Yuki", "Lee Ji-eun"])
        _p = _fn.split()
        nm = {"full_name": _fn, "family_name": _p[-1] if len(_p) > 1 else "",
              "middle_name": "", "given_name": _p[0], "name_order": "foreign"}
        ood_flags.append("foreign_name")

    # nationality + province + address
    foreign_nat = ood and rng.random() < 0.3
    nationality = rng.choice(["Hoa Kỳ", "Hàn Quốc", "Nhật Bản", "Pháp"]) if foreign_nat else "Việt Nam"
    province = pick_province(rng, core)
    addr = build_address(rng, core, province, ood=ood)
    if addr["scheme"].startswith("ood"): ood_flags.append("ood_address")

    # CCCD (hoặc không có với người nước ngoài)
    cccd_code = rng.choice(core["tinh_2025"][province]["old_codes"])
    has_cccd = not (foreign_nat and rng.random() < 0.7)
    cccd = build_cccd(rng, core, cccd_code, gender, y) if has_cccd else ""
    if not has_cccd: ood_flags.append("foreigner_no_cccd")
    # CMND 9 số legacy đôi khi
    if has_cccd and ood and rng.random() < 0.2:
        cccd = rand_digits(rng, 9); ood_flags.append("cmnd_9digit")

    phone = build_phone(rng, core)
    if foreign_nat and rng.random() < 0.5:
        phone = core["intl_phone_codes"][rng.choice(list(core["intl_phone_codes"]))] + rand_digits(rng, 9); ood_flags.append("foreign_phone")

    gplx = build_gplx(rng, cccd_code, gender, y) if (age >= 18 and has_cccd and rng.random() < 0.6) else ""
    passport = ("C" + rand_digits(rng, 7)) if rng.random() < 0.35 else ""
    plate = build_plate(rng, core, province) if (age >= 18 and rng.random() < 0.45) else ""

    # email
    dom = wchoice(rng, {"personal": 0.8, "education": 0.1, "corporate": 0.07, "government": 0.03})
    base = slug(nm["full_name"]) or "nguoi.dung"
    email = base + (str(rng.randint(1, 999)) if rng.random() < 0.5 else "") + "@" + rng.choice(core["email_domains"][dom])

    # marital theo tuổi
    marital = wchoice(rng, core["hon_nhan_by_age"][age_bucket(age)])
    occupation = pick_occupation(rng, core, age)

    ctx = {"full_name": nm["full_name"], "cccd": cccd or phone, "year": str(y), "gender": gender}

    # SPI & free-text => LẤY TỪ SCHEMA (đa dạng, chống sập)
    def R(fname):
        m = PII.get(fname)
        return realize_field(rng, core, m, ctx) if m else None

    fields = {
        **nm, "dob": fmt_dob(d, m, y), "gender": gender, "nationality": nationality,
        "address": addr["text"], "address_parts": {k: addr[k] for k in ("house_number","street","ward","province","scheme")},
        "phone": phone, "cccd": cccd, "passport_number": passport, "driver_license": gplx,
        "vehicle_plate": plate, "email": email, "marital_status": marital, "occupation": occupation,
        "ethnicity": ethnicity, "religion": R("religion"), "political_view": R("political_view"),
        "criminal_record": R("criminal_record"), "health_status": R("health_status"),
        "family_relations": R("family_relations"), "digital_account": R("digital_account"),
        "name_alias": R("name_alias"), "private_life": R("private_life"),
        "location_data": R("location_data"), "behavioral_data": R("behavioral_data"),
        "bank_account": build_bank_account(rng, core), "biometric": R("biometric"),
        "sexual_orientation": R("sexual_orientation"),
        "tax_code": (rand_digits(rng,10) if rng.random() < 0.3 else ""),
        "social_insurance_no": (rand_digits(rng,10) if rng.random() < 0.25 else ""),
        "health_insurance_no": ((rng.choice(["DN","HS","GD","TE","HN","BT"]) + rand_digits(rng,13)) if rng.random() < 0.3 else ""),
    }
    consistency = {
        "cccd_province_in_old_codes": (cccd[:3] in core["tinh_2025"][province]["old_codes"]) if (cccd and len(cccd)==12) else None,
        "cccd_year_matches_dob": (cccd[4:6] == f"{y%100:02d}") if (cccd and len(cccd)==12) else None,
        "cccd_gender_digit": (cccd[3] if (cccd and len(cccd)==12) else None),
        "plate_province_ok": (plate[:2] in core["tinh_2025"][province]["plate"]) if plate else None,
    }
    # gen_mode + llm_generate_prob: mỗi record, field mềm có XÁC SUẤT -> [[LLM_GENERATE]] (trộn nguồn, đa dạng)
    MUST_LLM_GEN = {
        "political_view", "religion", "sexual_orientation", "health_status",
        "criminal_record", "private_life", "location_data", "behavioral_data", "biometric"
    }
    gen_plan = {"llm_rewrite": [], "llm_generate": []}
    for _fn, _m in PII.items():
        if _fn not in fields:
            continue
        _base = _m.get("llm_generate_prob", 0.0)
        prob = _base if _m.get("gen_mode") == "llm_full" else min(1.0, _base * llm_scale)
        to_gen = (not bake_llm) and ((prob > 0.0 and (prob >= 1.0 or rng.random() < prob)) or _fn in MUST_LLM_GEN)
        if to_gen:
            fields[_fn] = "[[LLM_GENERATE]]"
            gen_plan["llm_generate"].append(_fn)
        elif _m.get("gen_mode") == "bank_rewrite":
            gen_plan["llm_rewrite"].append(_fn)
    quasi_key = f"{occupation}|{addr.get('ward','')}|{y}|{gender}"
    return {
        "profile_id": f"pf_{idx:06d}",
        "fields": fields,
        "meta": {"region": core["tinh_2025"][province]["region"], "age": age, "ethnicity": ethnicity},
        "consistency": consistency,
        "quasi_key": quasi_key,
        "ood_flags": ood_flags,
        "gen_plan": gen_plan,
    }

# ----------------------------------------------------------------------------- validate against schema regex
def validate(prof, PII):
    res = {}
    def chk(field, val, key="validate_regex", loose=False):
        if not val: return None
        rx = (PII[field].get("format") or {}).get(key)
        if loose:
            rx = (PII[field].get("format") or {}).get("validate_regex_loose", rx)
        return bool(re.match(rx, val)) if rx else None
    f = prof["fields"]
    res["cccd"] = chk("cccd", f["cccd"], loose=True) if len(f["cccd"]) == 12 else (len(f["cccd"]) == 9 or f["cccd"] == "")
    res["phone"] = chk("phone", f["phone"])
    res["email"] = chk("email", f["email"])
    res["driver_license"] = chk("driver_license", f["driver_license"], "validate_regex_loose")
    res["passport_number"] = chk("passport_number", f["passport_number"])
    return res

# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30000)
    ap.add_argument("--core", default="profile_core.json")
    ap.add_argument("--schema", default="pii_schema.json")
    ap.add_argument("--out", default="profile_bank.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--bake-llm", dest="bake_llm", action="store_true",
                    help="Nướng giá trị mẫu cho field llm_full thay vì để sentinel")
    ap.add_argument("--llm-prob-scale", dest="llm_scale", type=float, default=1.0,
                    help="Nhân toàn bộ llm_generate_prob (0 = tắt sentinel xác suất, >1 = đa dạng hơn)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    core = load_json(args.core)
    schema = load_json(args.schema)
    PII = {f["field"]: f for f in schema["fields"]}

    profiles = []
    seen = set()
    attempts = 0
    while len(profiles) < args.n and attempts < args.n * 3:
        attempts += 1
        p = build_profile(rng, core, PII, len(profiles), bake_llm=args.bake_llm, llm_scale=args.llm_scale)
        key = (p["fields"]["cccd"] or "", p["fields"]["full_name"], p["fields"]["dob"])
        if p["fields"]["cccd"] and key in seen:  # dedup theo cccd thật
            continue
        seen.add(key)
        profiles.append(p)

    # k-anonymity: đếm theo quasi_key
    qcount = Counter(p["quasi_key"] for p in profiles)
    for p in profiles:
        p["k_estimate"] = qcount[p["quasi_key"]]
        p["low_k"] = p["k_estimate"] < 5

    # validate + thống kê
    fail = Counter()
    for p in profiles:
        v = validate(p, PII)
        p["validation"] = v
        for k, ok in v.items():
            if ok is False: fail[k] += 1

    with open(args.out, "w", encoding="utf-8") as f:
        for p in profiles:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # ===== STATS =====
    print(f"\n=== ĐÃ ĐÚC {len(profiles)} profile -> {args.out} ===")
    print("Validate fail:", dict(fail) or "0 (tất cả pass)")
    def dist(key, fn, top=6):
        c = Counter(fn(p) for p in profiles)
        tot = sum(c.values())
        return ", ".join(f"{k}:{v*100//tot}%" for k, v in c.most_common(top))
    print("Giới tính:", dist(lambda x: x["fields"]["gender"], None) if False else dist("g", lambda p: p["fields"]["gender"]))
    print("Vùng:", dist("r", lambda p: p["meta"]["region"]))
    print("Dân tộc top:", dist("e", lambda p: p["fields"]["ethnicity"]))
    print("Tỉnh top:", dist("t", lambda p: p["fields"]["address_parts"]["province"]))
    print("political_view unique:", len({p["fields"]["political_view"] for p in profiles}),
          "| criminal_record unique:", len({p["fields"]["criminal_record"] for p in profiles}),
          "| health_status unique:", len({p["fields"]["health_status"] for p in profiles}))
    pv = Counter(p["fields"]["political_view"] for p in profiles).most_common(1)[0]
    print("  political_view phổ biến nhất chiếm:", f"{pv[1]*100//len(profiles)}% ('{pv[0][:40]}')")
    print("OOD: có >=1 cờ:", sum(1 for p in profiles if p["ood_flags"]), "| k<5:", sum(1 for p in profiles if p["k_estimate"] < 5))
    cc = [p for p in profiles if len(p["fields"]["cccd"]) == 12]
    okprov = sum(1 for p in cc if p["consistency"]["cccd_province_in_old_codes"])
    okyear = sum(1 for p in cc if p["consistency"]["cccd_year_matches_dob"])
    print(f"CCCD consistency: tỉnh khớp {okprov}/{len(cc)}, năm khớp {okyear}/{len(cc)}")
    print("\n--- 2 PROFILE MẪU ---")
    for p in profiles[:2]:
        print(json.dumps(p, ensure_ascii=False)[:600])

if __name__ == "__main__":
    main()
