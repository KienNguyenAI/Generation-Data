#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecurePrep — BỘ SINH THEO BIỂU MẪU HÀNH CHÍNH (Form-Driven Natural Generation) bằng Gemini.
Bản cập nhật: Cho phép LLM tự động chọn lựa trường thông tin phù hợp ngữ cảnh (Option A).
"""
import json, re, os, sys, random
from pathlib import Path

# Add current folder to path to import base generator
sys.path.append(str(Path(__file__).resolve().parent))
import generate

# Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT = generate.OUT
MODEL = generate.MODEL
SENS = generate.SENS
FIELDS = generate.FIELDS
MECHANISM = generate.MECHANISM
CUE_WORDS = generate.CUE_WORDS
BIRTH_CUES = generate.BIRTH_CUES
CRITICAL = generate.CRITICAL

SUB_FORMATS = {
    "administrative": {
        "don_tu": "Đơn từ cá nhân (Đơn trình bày hoàn cảnh, Đơn xin nghỉ phép, Đơn khiếu nại, Đơn xin miễn giảm nghĩa vụ hành chính).",
        "to_khai": "Tờ khai tự thuật (Tờ khai lý lịch tư pháp, Bản tự thuật cá nhân, Tờ khai đăng ký biến động hộ tịch).",
        "bien_ban": "Biên bản báo cáo (Biên bản xác minh thực địa của cán bộ, Báo cáo giải trình y tế của bác sĩ, Biên bản hòa giải)."
    },
    "dialogue": {
        "consultation": "Cuộc trò chuyện tư vấn hành chính giữa công dân và cán bộ tiếp nhận tại Bộ phận một cửa UBND hoặc cơ quan thuế.",
        "medical_chat": "Hỏi đáp y tế chẩn đoán bệnh và khai thác tiền sử dị ứng, tiền sử bệnh án giữa bác sĩ và bệnh nhân.",
        "legal_chat": "Cuộc trao đổi tư vấn pháp lý giữa luật sư và khách hàng về tiền án tiền sự, tranh chấp đất đai hoặc hôn nhân."
    },
    "third_person": {
        "diary": "Nhật ký cá nhân (Đoạn văn xuôi tự sự kể về cuộc sống riêng tư, nợ nần, trăn trở tôn giáo hoặc quá trình chữa bệnh).",
        "personal_email": "Thư điện tử (Email gửi sếp xin nghỉ phép y tế hoặc email gửi người thân tâm sự hoàn cảnh khó khăn)."
    }
}

TONES = {
    "formal_objective": "Trang trọng, khách quan, sử dụng ngôn từ hành chính chuẩn mực, trung tính, tuân thủ pháp luật.",
    "urgent_anxious": "Khẩn khoản, lo âu, thể hiện tình thế gấp gáp của nhân vật (ốm nặng, nợ nần, tai nạn) và cầu thị sự giúp đỡ.",
    "frustrated_complaining": "Bức xúc, phản ánh, thể hiện thái độ khiếu nại, đòi công bằng hoặc phản ánh gay gắt về vấn đề quyền lợi.",
    "cooperative_polite": "Hợp tác, lịch sự, thể hiện thái độ nhã nhặn, tôn trọng giữa hai bên đối thoại.",
    "casual_confidential": "Thân mật, tâm sự, sử dụng từ ngữ đời thường, giàu cảm xúc tự sự của nhân vật."
}

DOMAIN_SPI_MAP = {
    "medical_healthcare": ["health_status", "health_insurance_no", "biometric", "sexual_orientation"],
    "insurance_welfare": ["health_insurance_no", "social_insurance_no", "private_life"],
    "justice_legal": ["criminal_record", "behavioral_data", "political_view", "location_data"],
    "civil_family": ["private_life", "religion", "ethnicity", "sexual_orientation", "eid_credentials"],
    "education_training": ["private_life", "ethnicity", "political_view"],
    "religion_ethnicity": ["religion", "ethnicity"],
    "economy_tech_other": ["bank_account", "eid_credentials", "location_data"]
}

def extract_core_alias_name(val):
    if not val: return ""
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
    fl = generate.pfields(profile)
    full_name_val = fl.get("full_name", "")
    dyn_family, dyn_middle, dyn_given = generate.split_vietnamese_name(full_name_val) if full_name_val else ("", "", "")
    
    # Extract core alias name if present
    alias_val = fl.get("name_alias", "")
    a_fam, a_mid, a_giv = ("", "", "")
    if alias_val:
        core_alias = extract_core_alias_name(alias_val)
        if core_alias:
            a_fam, a_mid, a_giv = generate.split_vietnamese_name(core_alias)

    used = set(tagged_fields)
    # If LLM used full_name or name_alias, we add individual name components
    # to allow generate.annotate to perform post-hoc name splitting correctly
    if "full_name" in used or "name_alias" in used:
        used.update(["family_name", "middle_name", "given_name"])
        
    manifest = []
    name_parts = {"family_name", "middle_name", "given_name"}
    
    for field in used:
        if field not in generate.MECHANISM: continue
        
        m = generate.MECHANISM.get(field, "verbatim")
        label = generate.SENS.get(field, "PII")
        name_vi = (generate.FIELDS.get(field) or {}).get("name_vi", field)
        
        if field in name_parts:
            surfaces = []
            if field == "family_name":
                if dyn_family: surfaces.append(dyn_family)
                if a_fam: surfaces.append(a_fam)
            elif field == "middle_name":
                if dyn_middle: surfaces.append(dyn_middle)
                if a_mid: surfaces.append(a_mid)
            elif field == "given_name":
                if dyn_given: surfaces.append(dyn_given)
                if a_giv: surfaces.append(a_giv)
            
            surfaces = list(dict.fromkeys([s for s in surfaces if s]))
            if not surfaces: continue
            manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces})
            continue
            
        val = fl.get(field)
        if val is None or str(val).strip() == "":
            continue
        val = str(val).strip()
        
        is_anchor = (m == "anchor_tag" or val == generate.SENTINEL)
        
        if is_anchor:
            manifest.append({
                "field": field,
                "label": label,
                "name_vi": name_vi,
                "mechanism": m,
                "anchor": True,
                "seed_value": None if val == generate.SENTINEL else val
            })
        else:
            if m == "verbatim":
                if field == "cccd": surfaces = generate.render_cccd(val)
                elif field == "phone": surfaces = generate.render_phone(val)
                elif field == "address": surfaces = generate.render_address(val)
                elif field == "full_name": surfaces = generate.render_full_name(val)
                else: surfaces = [val]
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces})
            elif m == "date":
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": generate.render_dob(val), "cue_words": generate.BIRTH_CUES})
            elif m == "cue_context":
                surfaces = [val]
                if field == "political_view":
                    surfaces = generate.render_political_view(val)
                elif field == "religion":
                    surfaces = generate.render_religion(val)
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": surfaces, "cue_words": CUE_WORDS.get(field, [])})
            else:
                manifest.append({"field": field, "label": label, "name_vi": name_vi, "mechanism": m, "surfaces": [val]})
                
    for e in manifest:
        e["derived"] = (e["field"] in name_parts and e["field"] not in ["full_name"])
        
    return manifest

def build_outline_prompt(form_meta, fields_desc_str, register, sub_format_desc, tone_desc, target_spi=None):
    persona = "Bạn là một chuyên gia soạn thảo văn bản hành chính và pháp lý tại Việt Nam."
    task_desc = f"lập dàn ý chi tiết cho một văn bản mô phỏng thủ tục hành chính (phong cách chung: {register}, định dạng chi tiết: {sub_format_desc})"
    
    if register == "dialogue":
        rule_outline = "Liệt kê cấu trúc các lượt nói/chủ đề trao đổi chính giữa các nhân vật (ví dụ: Chào hỏi, Khai thác thông tin lý do thực hiện thủ tục, Giải đáp hướng dẫn, Đề xuất và Kết luận)."
    elif register == "third_person":
        rule_outline = "Liệt kê cấu trúc 3 phần (Mở đầu ghi nhận sự việc, Thân bài tường thuật/xác minh chi tiết về đối tượng, Kết luận/Đề xuất). Tuyệt đối cấm sử dụng ngôi thứ nhất 'tôi', phải dùng ngôi thứ ba (ví dụ: 'ông Nguyễn Bảo Long', 'chủ thể')."
    else:
        rule_outline = "Liệt kê cấu trúc 3 phần (Mở bài, Thân bài, Kết bài). Trong đó phần Thân bài phải nêu rõ 2 - 3 ý chính sẽ dùng để trình bày chi diện hoàn cảnh và đề xuất nhằm thuyết phục người đọc."

    form_desc = f"""- Thủ tục hành chính: "{form_meta['record_type']}"
- Cơ quan tiếp nhận/xử lý: "{form_meta.get('agency', 'Cơ quan có thẩm quyền')}" """

    raw_text = form_meta.get("form_raw_text", "")
    if raw_text:
        form_desc += f"\n- Nội dung/cấu trúc khung xương biểu mẫu gốc tham khảo:\n«««\n{raw_text[:1000]}\n»»»"

    spi_constraint = ""
    if target_spi:
        spi_name_vi = (generate.FIELDS.get(target_spi) or {}).get("name_vi", target_spi)
        spi_constraint = f"""
YÊU CẦU BẮT BUỘC LỒNG GHÉP THÔNG TIN NHẠY CẢM (SPI):
- Bạn bắt buộc phải chọn trường thông tin "{spi_name_vi}" ({target_spi}) vào dàn ý.
- Hãy sáng tạo ra một kịch bản/hoàn cảnh cá nhân cực kỳ tự nhiên và hợp lý khiến thông tin nhạy cảm "{spi_name_vi}" này buộc phải xuất hiện hoặc được đề cập đến trong văn bản/cuộc thoại liên quan đến thủ tục "{form_meta['record_type']}" (ví dụ: lý do sức khỏe để xin hoãn/đẩy nhanh tiến độ, vướng mắc lý lịch tư pháp của người làm đơn, hoàn cảnh đời tư khó khăn cần trình bày hỗ trợ, yếu tố tôn giáo/dân tộc ảnh hưởng...).
"""

    return f"""{persona}
Nhiệm vụ của bạn là {task_desc} dựa trên bối cảnh biểu mẫu hành chính sau:
{form_desc}

Yêu cầu về giọng điệu/văn phong của văn bản: {tone_desc}

Dưới đây là Ngân hàng thông tin nhân thân có sẵn (bao gồm thông tin định danh và thông tin nhạy cảm của nhân vật):
{fields_desc_str}
{spi_constraint}
Yêu cầu lập dàn ý (Bước 1 & 2):
1. Xác định loại văn bản phù hợp nhất (ví dụ: Đơn trình bày hoàn cảnh, Tờ khai tự thuật, Thư từ trao đổi, Biên bản xác minh, hoặc Cuộc đối thoại tư vấn).
2. Lập dàn ý chi tiết: {rule_outline}

QUY TẮC BẮT BUỘC VỀ CHỌN LỌC THÔNG TIN:
- Bạn KHÔNG ĐƯỢC dùng tất cả các thông tin ở trên.
- Bạn chỉ được lựa chọn một số thông tin định danh tối thiểu (Họ tên, ngày sinh...) và bắt buộc phải chọn trường nhạy cảm được yêu cầu lồng ghép ở trên để đưa vào dàn ý.
- Những thông tin không liên quan (ví dụ: số tài khoản ngân hàng hay biển số xe trong tờ khai kết hôn; tình trạng sức khỏe hay án tích trong đăng ký tạm trú...) tuyệt đối không được đưa vào văn bản để đảm bảo tính tự nhiên và chân thực.

Hãy trả về kết quả dưới dạng Markdown phân cấp rõ ràng (chỉ trả về dàn ý, tuyệt đối chưa viết nội dung chi tiết của văn bản/cuộc trò chuyện).

BẮT BUỘC ở dòng cuối cùng của kết quả, bạn phải liệt kê danh sách các mã trường (field name) đã chọn dưới định dạng sau:
«SELECTED_FIELDS: ["field_name_1", "field_name_2", ...]»
Ví dụ:
«SELECTED_FIELDS: ["full_name", "dob", "cccd", "religion"]»"""

def build_draft_prompt(form_meta, fields_desc_str, banned_fields_desc_str, outline, register, sub_format_desc, tone_desc):
    if register == "dialogue":
        persona = "Bạn là người biên soạn hội thoại/cuộc trò chuyện tiếng Việt tự nhiên."
        rule_prose = f"1) VIẾT DẠNG CUỘC TRÒ CHUYỆN/HỘI THOẠI HÀNG NGÀY: Viết bản nháp dưới dạng lời thoại đối đáp qua lại tự nhiên giữa các nhân vật để tái lập định dạng: {sub_format_desc}. Sử dụng danh xưng/tiền tố lời thoại rõ ràng (ví dụ: 'Bác sĩ:', 'Bệnh nhân:'). TUYỆT ĐỐI KHÔNG dùng họ tên cụ thể của nhân vật để làm nhãn người nói/tiền tố lời thoại (ví dụ: KHÔNG dùng 'Trần Phương Anh:', hãy dùng danh từ chung như 'Công dân:', 'Khách hàng:', 'Bệnh nhân:'). Lồng ghép khéo léo và tự nhiên các thông tin cá nhân và nhạy cảm vào các lượt thoại đối đáp."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng ghi chú kết thúc cuộc hội thoại (ví dụ: [Kết thúc cuộc trò chuyện])."
    elif register == "third_person":
        persona = "Bạn là người ghi nhận/báo cáo thông tin từ góc nhìn thứ ba."
        rule_prose = f"1) VIẾT DẠNG NARRATIVE GÓC NHÌN THỨ BA: Viết bản nháp dưới dạng lời kể, báo cáo xác minh hoặc biên bản tường thuật để tái lập định dạng: {sub_format_desc}. TUYỆT ĐỐI CẤM sử dụng ngôi thứ nhất 'tôi', 'chúng tôi' để chỉ đối tượng xác minh. Phải dùng ngôi thứ ba (ví dụ: 'ông Nguyễn Bảo Long', 'bà Nguyễn Thị Lan', 'chủ thể'). Triển khai văn bản mạch lạc, không dùng dấu gạch đầu dòng danh sách."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng phần ký tên/chức danh của người lập biên bản hoặc người xác minh."
    else:
        persona = "Bạn là người soạn thảo văn bản hành chính/đời sống tiếng Việt."
        rule_prose = f"1) VIẾT DẠNG ĐOẠN VĂN XUÔI LIÊN TỤC: Triển khai chi tiết văn bản hành chính hoàn chỉnh, mạch lạc để tái lập định dạng: {sub_format_desc}. TUYỆT ĐỐI KHÔNG dùng các dấu gạch đầu dòng (- hoặc *), không viết kiểu danh sách liệt kê \"Nhãn: giá trị\". Bạn PHẢI lồng ghép toàn bộ thông tin cá nhân vào các câu văn xuôi hành chính tự nhiên và liên tục trong các đoạn văn."
        rule_sign = f"6) Dòng cuối cùng kết thúc bằng phần ký tên; chỉ ghi tên gọi."

    form_desc = f"""- Thủ tục hành chính: "{form_meta['record_type']}"
- Cơ quan tiếp nhận/xử lý: "{form_meta.get('agency', 'Cơ quan có thẩm quyền')}" """

    raw_text = form_meta.get("form_raw_text", "")
    if raw_text:
        form_desc += f"\n- Nội dung/cấu trúc khung xương biểu mẫu gốc tham khảo:\n«««\n{raw_text[:1000]}\n»»»"

    return f"""{persona} Hãy thực hiện viết bản nháp (Bước 3) cho văn bản/cuộc trò chuyện dưới định dạng: **{sub_format_desc}** với giọng điệu/văn phong: **{tone_desc}** dựa trên bối cảnh biểu mẫu và dàn ý dưới đây.

[BỐI CẢNH BIỂU MẪU HÀNH CHÍNH]
{form_desc}

[DÀN Ý ĐÃ LẬP]
{outline}

[NGÂN HÀNG THÔNG TIN NHÂN VẬT ĐỂ CHỌN]
{fields_desc_str}

[DANH SÁCH TRƯỜNG THÔNG TIN CẤM ĐỀ CẬP (KHÔNG ĐƯỢC CHỌN VÀO DÀN Ý)]
{banned_fields_desc_str}

QUY TẮC BẮT BUỘC KHI VIẾT NHÁP:
{rule_prose}
1b) VIẾT TỰ NHIÊN, TRÁNH LẶP TỪ KHÔ CỨNG: Tránh diễn đạt lặp từ hoặc ghép nhãn thô cứng, thiếu tự nhiên (ví dụ: tránh viết "tôn giáo là không tôn giáo" mà hãy viết "không theo tôn giáo nào"; tránh viết "án tích là không có án tích" mà hãy viết "chưa từng bị kết án"). Hãy viết câu văn mượt mà và tự nhiên, phù hợp với văn cảnh thực tế. Tránh viết những câu ghép lủng củng hoặc tối nghĩa khi ghép dữ liệu (ví dụ: không viết "dẫn đến việc cần hỗ trợ đi lại khi làm thủ tục hành chính gặp nhiều khó khăn", hãy viết mạch lạc thành "do đó việc đi lại thực hiện thủ tục hành chính gặp nhiều khó khăn và cần có người hỗ trợ").
2) ĐA DẠNG HÓA VÀ TỰ NHIÊN HÓA ĐỊNH DẠNG (PII DIVERSITY): Chỉ đưa các thông tin định danh và nhạy cảm thực sự cần thiết theo dàn ý. Khi viết các thông tin định danh, bạn được khuyến khích đa dạng hóa định dạng hiển thị của chúng sao cho tự nhiên nhất với văn cảnh (tuyệt đối không chép dấu « » vào văn bản), ví dụ:
   - Đối với Ngày sinh (dob): có thể viết dạng 'ngày 29 tháng 08 năm 1982', '29/08/1982', '29-08-1982', '29.08.1982' hoặc '1982-08-29'.
   - Đối với Số điện thoại (phone): có thể viết dạng '0987.911.340', '0987 911 340', '+84 987 911 340', '(0987) 911 340' hoặc viết liền '0987911340'.
   - Đối với CCCD: có thể viết dạng cách khoảng '0361 8203 3012', '036-182-033-012' hoặc viết liền '036182033012'.
   - Đối với Địa chỉ (address) và Họ tên (full_name): lồng ghép tự nhiên vào ngữ cảnh (ví dụ: 'Nguyễn Thanh Quỳnh Liên', 'NGUYỄN THANH QUỲNH LIÊN', hoặc đảo họ tên ở cuối đơn...).
   Các trường khác không có định dạng đa dạng thì dùng đúng giá trị được cho. Đối với tình trạng hôn nhân (marital_status), bạn được phép chuyển chữ cái đầu thành chữ thường (ví dụ: 'góa', 'độc thân') để đảm bảo ngữ pháp.
3) BỌC CÁC TRƯỜNG THÔNG TIN ĐÃ ĐIỀN BẰNG THẺ NEO BẮT BUỘC:
   Mọi thông tin cá nhân/nhạy cảm phải được bọc bằng thẻ `⟦field_name⟧giá trị⟦/field_name⟧`. Tuyệt đối không để xảy ra lỗi dán nhãn như viết dính tên thẻ vào văn bản.
3b) TUYỆT ĐỐI NGHIÊM CẤM LỒNG THẺ VÀO NHAU (No nested tags). Chỉ bọc thẻ cho đúng cụm từ mang thông tin giá trị thực tế của trường đó. KHÔNG bọc cả câu dài hay đoạn văn chứa các thực thể khác. Mọi thẻ phải nằm tách biệt, độc lập nhau.
    - SAI: ⟦private_life⟧áp lực từ việc tranh chấp quyền nuôi dưỡng con trai là ⟦family_relations⟧Trịnh Quang Công Tài⟦/family_relations⟧ và phân chia tài sản⟦/private_life⟧
    - ĐÚNG: áp lực từ việc ⟦private_life⟧tranh chấp quyền nuôi dưỡng con trai⟦/private_life⟧ là ⟦family_relations⟧con trai là Trịnh Quang Công Tài⟦/family_relations⟧ và ⟦private_life⟧phân chia tài sản⟦/private_life⟧
4) KHÔNG ĐƯỢC gán ghép thông tin cá nhân của nhân vật làm thông tin của tổ chức/cơ quan. Các thông tin trong ngân hàng thông tin (Địa chỉ, Số điện thoại, Email) là thông tin cá nhân của nhân vật. Khi viết, hãy ghi rõ đó là địa chỉ cá nhân, số điện thoại cá nhân của người đại diện/người làm đơn/người chịu trách nhiệm chuyên môn chứ không được gán thành địa chỉ/số điện thoại của cơ quan báo chí, doanh nghiệp hay tổ chức.
5) CHỈ ĐƯỢC ĐỀ CẬP THÔNG TIN CÓ TRONG DANH SÁCH CHỌN: Bạn chỉ được viết và đề cập đến thông tin nhạy cảm của nhân vật nếu trường đó có mặt trong [NGÂN HÀNG THÔNG TIN NHÂN VẬT ĐỂ CHỌN] ở trên. TUYỆT ĐỐI CẤM tự ý bịa đặt hoặc đưa vào văn bản các thông tin nhạy cảm khác nếu trường đó có trong [DANH SÁCH TRƯỜNG THÔNG TIN CẤM ĐỀ CẬP] (Ví dụ: nếu trong danh sách cấm có 'criminal_record', cấm đề cập đến án tích hoặc lý lịch tư pháp; nếu có 'health_status', cấm đề cập đến bệnh trạng).
   - Đối với án tích (criminal_record): CHỈ viết về án tích (bao gồm cả việc xác nhận chưa từng bị kết án kèm Phiếu lý lịch tư pháp số hiệu ngẫu nhiên) NẾU trường `criminal_record` có trong danh sách chọn ở trên. Khi viết, bắt buộc bọc thẻ `⟦criminal_record⟧` cho toàn bộ mệnh đề đó (ví dụ: "⟦criminal_record⟧chưa từng bị kết án theo Phiếu lý lịch tư pháp số 452/STP-LLTP⟦/criminal_record⟧"). Nếu trường `criminal_record` không có mặt trong danh sách chọn ở trên, TUYỆT ĐỐI CẤM đề cập đến án tích hoặc lý lịch tư pháp dưới bất kỳ hình thức nào.
   - Đối với sức khỏe (health_status) và đời tư (private_life): TUYỆT ĐỐI CẤM gán ghép các thông tin chi phí chữa bệnh, khó khăn kinh tế, nợ nần, suy kiệt tài chính vào nhãn `⟦health_status⟧`. Nhãn `⟦health_status⟧` chỉ chứa thông tin y tế, chẩn đoán, bệnh trạng (ví dụ: 'bị suy thận giai đoạn cuối'). Phần khó khăn tài chính hoặc chi phí phát sinh (ví dụ: 'cần chi phí chạy thận liên tục') phải được bọc riêng bằng nhãn `⟦private_life⟧` (nếu trường `private_life` có mặt trong danh sách chọn). Nếu trường `private_life` không có trong danh sách chọn, TUYỆT ĐỐI CẤM đề cập đến chi phí chữa bệnh hay khó khăn tài chính/nợ nần do bệnh tật.
6) TUYỆT ĐỐI CẤM TỰ Ý MÔ TẢ/BỊA ĐẶT THÊM THÔNG TIN Y TẾ HOẶC ĐỜI TƯ: Bạn chỉ được sử dụng đúng các giá trị nhạy cảm đã cho trong ngân hàng thông tin để đưa vào văn bản.
   - Khi sinh thông tin cho các trường nhạy cảm có giá trị '[[LLM_GENERATE]]' (như health_status, private_life, religion, v.v.), bạn phải sinh các giá trị cực kỳ đơn giản, ngắn gọn và trung tính. Ví dụ: đối với health_status, chỉ ghi tên bệnh lý cơ bản (như 'bị suy thận giai đoạn cuối', 'bị tiểu đường nặng', 'bị gãy chân'), TUYỆT ĐỐI KHÔNG tự ý thêm thắt các chi tiết lâm sàng hay hậu quả bi kịch như 'phải nhập viện điều trị tích cực', 'nguy kịch', 'gánh nặng lớn đè lên vai nhân sự', 'suy kiệt thể chất nặng' hay 'chi phí chữa bệnh' (trừ khi có trường private_life được chọn).
7) KHÔNG tự ý bổ sung thêm thông tin cá nhân (tên riêng, số điện thoại, địa chỉ) mới ngoài ngân hàng thông tin nhân vật ở trên.
8) CHỈ trả về nội dung bản nháp thô sau khi viết. KHÔNG có lời mở đầu hay lời kết của AI, KHÔNG định dạng markdown chứa ```."""

def build_revision_prompt(fields_desc_str, banned_fields_desc_str, draft, register):
    if register == "dialogue":
        rule_format = "1) ĐẢM BẢO ĐỐI ĐÁP TỰ NHIÊN VÀ PHÙ HỢP BỐI CẢNH: Sửa lỗi nếu cuộc hội thoại diễn đạt gượng ép hoặc rập khuôn. Chỉnh sửa lời thoại trôi chảy, tự nhiên và phù hợp với tính cách/vai trò của từng nhân vật. Đặc biệt, TUYỆT ĐỐI KHÔNG dùng tên riêng cụ thể của nhân vật để làm tiền tố lời thoại/nhãn người nói (ví dụ: KHÔNG dùng 'Trần Phương Anh:', phải sửa thành 'Công dân:', 'Bệnh nhân:', 'Khách hàng:')."
    elif register == "third_person":
        rule_format = "1) BẢO TOÀN GÓC NHÌN THỨ BA: Sửa các lỗi nếu văn bản dùng ngôi thứ nhất 'tôi' để chỉ đối tượng. Chuyển đổi toàn bộ thành ngôi thứ ba khách quan, trang trọng và mạch lạc."
    else:
        rule_format = "1) ĐẢM BẢO VĂN XUÔI LIÊN TỤC: Sửa lỗi nếu bản nháp sử dụng các dấu gạch đầu dòng (- hoặc *) hoặc viết kiểu danh sách liệt kê \"Nhãn: giá trị\". Bạn phải chuyển đổi và lồng ghép toàn bộ thông tin này thành các câu văn xuôi hành chính trôi chảy, liên tục trong các đoạn văn (tuyệt đối không để lại dạng danh sách liệt kê). Chỉnh sửa câu chữ mạch lạc, trang trọng và tự nhiên."

    return f"""Bạn là một Biên tập viên văn bản tiếng Việt chuyên nghiệp. Nhiệm vụ của bạn là rà soát và hiệu đính (Bước 4) bản nháp dưới đây nhằm tối ưu hóa chất lượng văn bản.

[BẢN NHÁP CỦA BẠN]
{draft}

QUY TẮC HIỆU ĐÍNH BẮT BUỘC:
{rule_format}
1b) SỬA LỖI DIỄN ĐẠT THÔ CỨNG VÀ PHẠM VI THÔNG TIN: 
    - CHỈ ĐƯỢC phép giữ lại và hiệu đính các thông tin nhạy cảm (án tích, bệnh tật, tôn giáo, hôn nhân, người thân...) nếu trường đó có trong danh sách ở mục 2. Nếu một trường nhạy cảm nằm trong [DANH SÁCH TRƯỜNG THÔNG TIN CẤM ĐỀ CẬP] ở dưới, bạn BẮT BUỘC PHẢI XÓA BỎ hoàn toàn bất kỳ câu chữ nào đề cập đến nó (Ví dụ: nếu có trường criminal_record trong danh sách cấm, hãy xóa bỏ ngay câu nói về việc chưa từng bị kết án hoặc Phiếu lý lịch tư pháp; nếu có health_status trong danh sách cấm, cấm đề cập đến bệnh tật).
    - Đối với trường tình trạng hôn nhân (marital_status) (ví dụ: 'Góa', 'Độc thân', 'Kết hôn'), bạn phải chuyển thành chữ thường (ví dụ: 'góa', 'độc thân', 'kết hôn') khi viết vào câu để đảm bảo đúng ngữ pháp tiếng Việt.
    - Sửa các lỗi diễn đạt rập khuôn hoặc ghép nhãn gượng ép (ví dụ: sửa "tôn giáo là không tôn giáo" thành "không theo tôn giáo nào"; sửa "án tích là không có án tích" thành "chưa từng bị kết án").
    - Đảm bảo Địa chỉ, Số điện thoại, Email của nhân vật được nêu rõ là thông tin cá nhân của họ chứ không bị gán ghép thành địa chỉ/số liên lạc của cơ quan hay tổ chức.
    - Đảm bảo thông tin về việc nhân vật không có án tích đi kèm tham chiếu đến Phiếu lý lịch tư pháp phải được bọc thẻ ⟦criminal_record⟧ đầy đủ (ví dụ: "⟦criminal_record⟧chưa từng bị kết án theo Phiếu lý lịch tư pháp số [số hiệu ngẫu nhiên]⟦/criminal_record⟧").
    - Tránh các câu ghép lủng củng, tối nghĩa hoặc lặp từ gượng ép khi lồng ghép thông tin từ ngân hàng dữ liệu.
2) BẢO TOÀN DỮ LIỆU & CHẤP NHẬN ĐA DẠNG ĐỊNH DẠNG: Bảo toàn các giá trị định danh từ ngân hàng thông tin nhân vật dưới đây. Chấp nhận và giữ nguyên các định dạng tự nhiên đa dạng mà bản nháp đã sử dụng (chẳng hạn như ngày sinh viết dạng chữ 'ngày... tháng... năm...', số điện thoại có dấu chấm/cách, cccd có khoảng trắng...). Đối với tình trạng hôn nhân (marital_status), bạn bắt buộc viết thường:
{fields_desc_str}

[DANH SÁCH TRƯỜNG THÔNG TIN CẤM ĐỀ CẬP (KHÔNG ĐƯỢC CÓ TRONG VĂN BẢN)]
{banned_fields_desc_str}

3) Chuẩn hóa thẻ đóng mở: Đảm bảo mọi thẻ nhạy cảm bắt đầu bằng ⟦field⟧ đều phải kết thúc bằng ⟦/field⟧ tương ứng. Sửa triệt để các lỗi dán nhãn sai cú pháp (như viết dính chữ không có ngoặc ví dụ: "family_relationscon trai..." hoặc "⟦family_relationscon... ⟧"). Bắt buộc phải đưa về dạng chuẩn mực: ⟦field_name⟧giá trị⟦/field_name⟧. Không lồng thẻ vào nhau.
- TUYỆT ĐỐI NGHIÊM CẤM LỒNG THẺ VÀO NHAU (No nested tags). Mỗi thực thể chỉ bọc thẻ độc lập, tách biệt nhau.
  + SAI: ⟦private_life⟧tranh chấp quyền nuôi con trai là ⟦family_relations⟧Trịnh Quang Công Tài⟦/family_relations⟧ và phân chia tài sản⟦/private_life⟧
  + ĐÚNG: ⟦private_life⟧tranh chấp quyền nuôi con trai⟦/private_life⟧ là ⟦family_relations⟧con trai là Trịnh Quang Công Tài⟦/family_relations⟧ và ⟦private_life⟧phân chia tài sản⟦/private_life⟧
- CHỈ bọc đúng cụm từ mang giá trị thông tin cụ thể (ví dụ: "đang trong quá trình ly thân", "nợ nần chồng chất"). TUYỆT ĐỐI CẤM bọc cả câu dài phức tạp chứa các từ dẫn, từ nối, từ chuyển tiếp không mang thông tin nhạy cảm định danh.
Rà soát kỹ và dán nhãn đầy đủ cho các trường tự do (health_status, private_life, criminal_record, political_view, religion, sexual_orientation). Đảm bảo tuân thủ NGUYÊN TẮC VÀNG VỀ TÍNH ĐỊNH DANH: chỉ bọc thẻ cho các thông tin có tính định danh cụ thể, TUYỆT ĐỐI CẤM dán nhãn cho các danh từ/đại từ chỉ nhóm/quan hệ chung chung (như "vợ chồng", "cả hai con chung", "con cái", "gia đình", "sức khỏe", "bệnh tật", "án tích", v.v.).
- Phân tách tuyệt đối ⟦health_status⟧ và ⟦private_life⟧: Trường ⟦health_status⟧ chỉ được bọc các mô tả trực tiếp về bệnh lý, chẩn đoán, triệu chứng lâm sàng. TUYỆT ĐỐI KHÔNG bọc phần mô tả chi phí chữa bệnh, khó khăn tài chính, nợ nần do chữa bệnh vào thẻ ⟦health_status⟧. Tất cả các nội dung về chi phí phát sinh, khó khăn tài chính, nợ nần đó phải được bọc riêng bằng nhãn ⟦private_life⟧ (nếu trường private_life có mặt trong danh sách ở mục 2); nếu trường private_life không có trong danh sách mục 2, bạn phải XÓA BỎ nội dung nói về chi phí/khó khăn tài chính này khỏi văn bản.
- Tránh bọc cả câu phức tạp hay đoạn dài. Phân rã ranh giới rõ ràng: Nếu một câu có cả phần bệnh trạng (health_status) và phần hậu quả ảnh hưởng đời tư (private_life), hãy bọc riêng biệt thành "⟦health_status⟧[bệnh trạng]⟦/health_status⟧ nên ⟦private_life⟧[hậu quả]⟦/private_life⟧".
- Đối với criminal_record, đảm bảo gán nhãn ⟦criminal_record⟧ cho cả các tuyên bố không có án tích có liên kết với chứng từ pháp lý như Phiếu lý lịch tư pháp.
- Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ. TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧.
4) KHÔNG tự ý bổ sung thêm thông tin cá nhân (tên riêng, số điện thoại, địa chỉ) mới nào khác vào văn bản (trừ khi chúng được dán nhãn thẻ đúng quy cách).
5) BẢO ĐẢM TÍNH KHÁCH QUAN, KHÔNG TỰ SOẠN THÊM BỆNH TẬT LÂM SÀNG/ĐỜI TƯ: Rà soát và loại bỏ các chi tiết bệnh lý lâm sàng cụ thể mới (như 'nguy kịch', 'suy kiệt thể chất nặng', 'tim mạch', 'nhập viện điều trị tích cực') hay các tình tiết hoàn cảnh bi kịch đời tư mới do bước nháp tự viết thêm mà không có trong hồ sơ gốc. Thay thế chúng bằng câu từ chung chung, trung tính (ví dụ: 'gặp vấn đề về sức khỏe', 'hoàn cảnh khó khăn') hoặc dùng đúng giá trị được cho.
6) CHỈ trả về nội dung văn bản đã được hiệu đính. KHÔNG giải thích, KHÔNG markdown chứa ```."""

def generate_one(profile, form_meta, register=None, outline=None, tagged_fields=None, target_spi=None):
    fl = generate.pfields(profile)
    
    # 1. Choose or reuse register
    if not register:
        register = random.choice(["administrative", "dialogue", "third_person"])
        
    # Choose sub-format and tone
    sub_format_key = random.choice(list(SUB_FORMATS[register].keys()))
    sub_format_desc = SUB_FORMATS[register][sub_format_key]
    
    if register == "dialogue":
        valid_tones = ["cooperative_polite", "urgent_anxious", "frustrated_complaining"]
    elif register == "third_person":
        valid_tones = ["casual_confidential", "urgent_anxious"]
    else:
        valid_tones = ["formal_objective", "urgent_anxious", "frustrated_complaining"]
        
    tone_key = random.choice(valid_tones)
    tone_desc = TONES[tone_key]
    
    # 2. Compile all fields available in profile for the prompt
    fields_desc = []
    for field in generate.MECHANISM:
        if field in ("family_name", "middle_name", "given_name"): continue
        val = fl.get(field)
        if val is None or str(val).strip() == "": continue
        
        name_vi = (generate.FIELDS.get(field) or {}).get("name_vi", field)
        fields_desc.append(f"   - {name_vi} ({field}): «{val}»")
    fields_desc_str = "\n".join(fields_desc)
    
    # 3. Choose or reuse outline
    selected_fields = []
    if not outline:
        outline_prompt = build_outline_prompt(form_meta, fields_desc_str, register, sub_format_desc, tone_desc, target_spi=target_spi)
        try:
            raw_outline = generate.call_gemini(outline_prompt, temperature=0.5)
            outline = generate.clean_output(raw_outline)
            
            # Extract selected fields
            match = re.search(r'«SELECTED_FIELDS:\s*(\[.*?\])»', raw_outline)
            if match:
                try:
                    selected_fields = json.loads(match.group(1))
                    selected_fields = [f.strip() for f in selected_fields if f.strip() in generate.MECHANISM]
                except Exception:
                    selected_fields = []
            
            if not selected_fields:
                # Fallback: scan outline text for field keys
                for field in generate.MECHANISM:
                    if field in raw_outline:
                        selected_fields.append(field)
                if not selected_fields:
                    selected_fields = ["full_name", "dob", "cccd", "address", "phone"]
            
            if target_spi and target_spi not in selected_fields:
                selected_fields.append(target_spi)
                
            # Clean SELECTED_FIELDS block from the outline to keep outline clean
            outline = re.sub(r'«SELECTED_FIELDS:\s*\[.*?\]»', '', outline).strip()
        except Exception as e:
            print(f"      (Lập dàn ý gặp lỗi: {e}. Sử dụng dàn ý mặc định...)")
            outline = """1. Phần mở đầu: Tiêu ngữ, thông tin người làm đơn/các nhân vật.
2. Phần nội dung: Trình bày chi tiết hoàn cảnh có lồng ghép thông tin nhạy cảm liên quan đến thủ tục.
3. Phần kết: Ký tên/ghi rõ họ tên."""
            selected_fields = ["full_name", "dob", "cccd", "address", "phone"]
            if target_spi and target_spi not in selected_fields:
                selected_fields.append(target_spi)
    else:
        # If outline is reused, use tagged_fields from rec
        selected_fields = tagged_fields if tagged_fields else ["full_name", "dob", "cccd", "address", "phone"]

    # Filter fields_desc_str based on selected_fields, and build banned fields list
    filtered_fields_desc = []
    banned_fields_desc = []
    for field in generate.MECHANISM:
        if field in ("family_name", "middle_name", "given_name"): continue
        val = fl.get(field)
        if val is None or str(val).strip() == "": continue
        
        name_vi = (generate.FIELDS.get(field) or {}).get("name_vi", field)
        if field in selected_fields:
            display_val = str(val).strip()
            if field == "cccd": display_val = random.choice(generate.render_cccd(display_val))
            elif field == "phone": display_val = random.choice(generate.render_phone(display_val))
            elif field == "dob": display_val = random.choice(generate.render_dob(display_val))
            elif field == "address": display_val = random.choice(generate.render_address(display_val))
            elif field == "full_name": display_val = random.choice(generate.render_full_name(display_val))
            filtered_fields_desc.append(f"   - {name_vi} ({field}): «{display_val}»")
        elif generate.SENS.get(field) in ("SPI", "PII") or field in ("marital_status", "religion", "political_view", "sexual_orientation", "health_status", "criminal_record", "private_life"):
            banned_fields_desc.append(f"   - {name_vi} ({field})")
            
    filtered_fields_desc_str = "\n".join(filtered_fields_desc)
    banned_fields_desc_str = "\n".join(banned_fields_desc) if banned_fields_desc else "   (Không có)"

    last = None
    for attempt in range(1, 4):
        temp_draft = 0.85 if attempt == 1 else 0.7
        draft_prompt = build_draft_prompt(form_meta, filtered_fields_desc_str, banned_fields_desc_str, outline, register, sub_format_desc, tone_desc)
        raw_draft = generate.call_gemini(draft_prompt, temperature=temp_draft)
        draft = generate.clean_output(raw_draft)
        
        revision_prompt = build_revision_prompt(filtered_fields_desc_str, banned_fields_desc_str, draft, register)
        raw_revised = generate.call_gemini(revision_prompt, temperature=0.2)
        tagged = generate.clean_output(raw_revised)
        
        # We dynamically discover or reuse which fields the LLM actually chose to tag
        if tagged_fields is None:
            attempt_tagged_fields = set(re.findall(r"⟦([a-zA-Z0-9_]+)⟧", tagged))
            attempt_tagged_fields = attempt_tagged_fields.intersection(set(selected_fields))
        else:
            attempt_tagged_fields = set(tagged_fields)
        
        # Build manifest containing ONLY these used fields
        manifest = build_manifest_for_used_fields(profile, attempt_tagged_fields)
        
        # Choose a random surface variant for matching validation
        for e in manifest:
            if e.get("surfaces"):
                e["prompt_surface"] = random.choice(e["surfaces"])
            else:
                e["prompt_surface"] = ""
                
        ext = generate.extract_anchor_tags(tagged, [e["field"] for e in manifest if e.get("anchor")])
        
        # Restrict spans to only selected_fields
        ext["spans"] = [s for s in ext["spans"] if s["field"] in selected_fields]
        
        clean = ext["clean_text"]
        
        # Coverage check (strictly on the dynamically constructed manifest)
        miss = generate.coverage(clean, manifest)
        important = [f for f in miss if f in generate.CRITICAL or generate.SENS.get(f) == "SPI"]
        last = (manifest, clean, ext, miss, attempt_tagged_fields)
        
        # If the tags are parsed successfully and no critical/SPI fields used by the LLM are missing
        if ext["ok"] and not important:
            break
        print(f"   [regen {attempt}] ok_tag={ext['ok']} important_miss={important}")
        
    manifest, clean, ext, miss, final_tagged_fields = last
    spans = generate.annotate(clean, manifest, ext["spans"])
    
    return {
        "profile_id": profile.get("profile_id"),
        "template_id": form_meta.get("template_id"),
        "source_url": form_meta.get("source_url"),
        "record_type": form_meta.get("record_type"),
        "agency": form_meta.get("agency"),
        "track": "B_form_driven",
        "model": generate.MODEL,
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
    generate.load_all_form_metadata()
    valid_forms = [item for item in generate.FORM_METADATA_CACHE.values() if item.get("form_raw_text") and item.get("record_type")]
    
    if not valid_forms:
        print("Không tìm thấy biểu mẫu hợp lệ nào trong form.json!")
        sys.exit(1)
        
    print(f"Tìm thấy {len(valid_forms)} biểu mẫu chứa văn bản mẫu trong form.json")
    
    pool = generate.load_profiles(3000)
    # Trộn ngẫu nhiên hồ sơ người lớn (18-85 tuổi)
    adult_pool = [p for p in pool if (generate._age(generate.pfields(p)) or 0) >= 18 and (generate._age(generate.pfields(p)) or 999) <= 85]
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
        fl = generate.pfields(profile)
        available_target_spis = [f for f in target_candidates if fl.get(f) and str(fl.get(f)).strip()]
        
        if not available_target_spis:
            all_spis = [f for f in generate.MECHANISM if generate.SENS.get(f) == "SPI"]
            available_target_spis = [f for f in all_spis if fl.get(f) and str(fl.get(f)).strip()]
            
        target_spi = random.choice(available_target_spis) if available_target_spis else None
        
        print(f"[{i+1}/{n}] {pid} (tuổi {generate._age(generate.pfields(profile))}) × Biểu mẫu: {form_meta['record_type']} ({form_meta.get('agency')}) [SPI: {target_spi}]")
        try:
            rec = generate_one(profile, form_meta, target_spi=target_spi)
            lines.append(json.dumps(rec, ensure_ascii=False))
            m = rec["meta"]
            summary.append((pid, form_meta["record_type"][:30], m["n_spans"], m["tag_ok"], m["missing_coverage"]))
            print(f"      -> {m['n_spans']} spans | tag_ok={m['tag_ok']} | format={m['sub_format']} | tone={m['tone']} | miss={m['missing_coverage']}")
        except Exception as e:
            print("      LỖI:", e)
            summary.append((pid, form_meta["record_type"][:30], "-", "ERR", str(e)[:50]))
            
    ds = OUT / "dataset.jsonl"
    ds.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"{'#':<3}{'profile':<11}{'form_type':<32}{'spans':<7}{'tag_ok':<8}missing")
    print("-" * 90)
    for i, (pid, ftype, ns, ok, ms) in enumerate(summary, 1):
        print(f"{i:<3}{pid:<11}{ftype:<32}{str(ns):<7}{str(ok):<8}{ms}")
    ok_cnt = sum(1 for s in summary if s[3] is True)
    print(f"\n{ok_cnt}/{n} tag_ok. Dataset Form-Driven -> {ds}")

def patch_profile_in_dataset(pid):
    OUT.mkdir(exist_ok=True)
    ds = OUT / "dataset.jsonl"
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
            
    if found_idx == -1:
        print(f"Không tìm thấy profile_id: {pid} trong {ds.name}!")
        sys.exit(1)
        
    print(f"Tìm thấy hồ sơ {pid} tại dòng {found_idx + 1} của {ds.name}. Tiến hành sinh lại...")
    
    generate.load_all_form_metadata()
    pool = generate.load_profiles(3000)
    profile = next((p for p in pool if p.get("profile_id") == pid), None)
    if not profile:
        print(f"Không tìm thấy hồ sơ {pid} trong ngân hàng hồ sơ!")
        sys.exit(1)
        
    rec = records[found_idx]
    form_meta = generate.FORM_METADATA_CACHE.get(rec["template_id"])
    if not form_meta:
        # Find by record_type
        for meta in generate.FORM_METADATA_CACHE.values():
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
    fl = generate.pfields(profile)
    available_target_spis = [f for f in target_candidates if fl.get(f) and str(fl.get(f)).strip()]
    if not available_target_spis:
        all_spis = [f for f in generate.MECHANISM if generate.SENS.get(f) == "SPI"]
        available_target_spis = [f for f in all_spis if fl.get(f) and str(fl.get(f)).strip()]
    target_spi = random.choice(available_target_spis) if available_target_spis else None
    
    # Generate one clean record
    new_rec = generate_one(profile, form_meta, register=register, outline=outline, tagged_fields=tagged_fields, target_spi=target_spi)
    records[found_idx] = new_rec
    
    # Save back to dataset.jsonl
    dest = OUT / "dataset.jsonl"
    dest.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    print(f"Đã cập nhật thành công và lưu vào {dest}!")
    print("\n--- NỘI DUNG MỚI ---")
    print(new_rec["content"])

if __name__ == "__main__":
    # Nhận tham số dòng lệnh:
    # - Nếu tham số bắt đầu bằng "pf_" hoặc "--patch", thực hiện patch lại đúng row có profile đó
    # - Nếu tham số là một số, sinh số lượng dòng tương ứng (mặc định là 2 dòng)
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--patch" and len(sys.argv) > 2:
            patch_profile_in_dataset(sys.argv[2])
        elif arg.startswith("pf_"):
            patch_profile_in_dataset(arg)
        elif arg.isdigit():
            run_batch(int(arg))
        else:
            print("Tham số không hợp lệ. Sử dụng: python generate_form_driven.py [số lượng dòng | profile_id]")
    else:
        run_batch(2)
