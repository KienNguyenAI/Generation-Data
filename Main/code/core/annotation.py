# -*- coding: utf-8 -*-
import re
import unicodedata
from core.config import SENS, MECHANISM, BIRTH_CUES

NFC = lambda s: unicodedata.normalize("NFC", s)

BL, BR = r"(?<!\w)", r"(?!\w)"

NAME_CUES = [
    "họ và tên", "họ tên", "người làm đơn", "người khai", "người ký", "ký tên", "tên:",
    "tên gọi", "thường gọi", "được gọi", "gọi là", "tôi là", "tôi tên", "trân trọng", "kính đơn", "ký:", "người viết đơn",
    "mang họ", "họ là", "họ của", "họ:", "chữ đệm", "tên đệm", "chữ lót"
]

_OPEN, _CLOSE = "⟦", "⟧"

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

def extract_anchor_tags(tagged, anchor_fields=None):
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

def coverage(clean, manifest):
    miss = []
    for e in manifest:
        if e["mechanism"] == "anchor_tag" or e.get("anchor"): continue
        if e.get("derived"): continue
        found = (len(match_cue_context(clean, e["surfaces"], e.get("cue_words") or BIRTH_CUES)) > 0
                 if e["mechanism"] in ("cue_context", "date") else any(s in clean for s in e["surfaces"]))
        if not found: miss.append(e["field"])
    return miss
