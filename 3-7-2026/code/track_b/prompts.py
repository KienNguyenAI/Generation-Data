# -*- coding: utf-8 -*-
import re

def build_outline_prompt(scenario, manifest, supplements=None, form_meta=None):
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

    form_desc = ""
    if form_meta and form_meta.get("record_type"):
        form_desc = f"\n- Biểu mẫu hành chính tham chiếu: \"{form_meta['record_type']}\" (do {form_meta.get('agency', 'Cơ quan có thẩm quyền')} ban hành)"
        raw_text = form_meta.get("form_raw_text", "")
        if raw_text:
            form_desc += f"\n- Nội dung/cấu trúc khung xương biểu mẫu gốc để mô phỏng:\n«««\n{raw_text[:800]}\n»»»"

    return f"""{persona}
Nhiệm vụ của bạn là {task_desc} dựa trên thông tin sau:
- Chủ đề kịch bản: "{scenario['title']}"
- Lý do/Bối cảnh xuất hiện văn bản: {scenario.get('disclosure_reason', '')}{form_desc}
- Phong cách ngôn ngữ: {register}

Các thông tin nhân thân và nghiệp vụ bắt buộc phải tích hợp sau này:
{fields_desc_str}
Thông tin bổ sung bắt buộc:
{supp_desc_str}

Yêu cầu thực hiện:
1. Xác định mục đích và giới hạn (Bước 1): Xác định loại văn bản/cuộc trò chuyện cụ thể phù hợp nhất. Xác định văn phong tự nhiên, phù hợp bối cảnh.
2. Lập dàn ý nhanh (Bước 2): {rule_outline}

Hãy trả về kết quả dưới dạng Markdown phân cấp rõ ràng (chỉ trả về dàn ý, tuyệt đối chưa viết nội dung chi tiết của văn bản/cuộc trò chuyện)."""

def build_draft_prompt(scenario, manifest, supplements, outline, form_meta=None):
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

    form_desc = ""
    if form_meta and form_meta.get("record_type"):
        form_desc = f"\n- Biểu mẫu hành chính tham chiếu: \"{form_meta['record_type']}\" (do {form_meta.get('agency', 'Cơ quan có thẩm quyền')} ban hành)"
        raw_text = form_meta.get("form_raw_text", "")
        if raw_text:
            form_desc += f"\n- Nội dung/cấu trúc khung xương biểu mẫu gốc để mô phỏng:\n«««\n{raw_text[:800]}\n»»»"

    return f"""{persona} Hãy thực hiện viết bản nháp (Bước 3) cho văn bản/cuộc trò chuyện dựa trên kịch bản, biểu mẫu tham chiếu và dàn ý dưới đây.
{form_desc}

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
3) Chuẩn hóa thẻ đóng mở: Đảm bảo mọi thẻ nhạy cảm bắt đầu bằng ⟦field] đều phải kết thúc bằng ⟦/field] tương ứng (ví dụ: sửa lỗi đóng thiếu dạng ⟧ trần hoặc thiếu dấu gạch chéo `/`). Không lồng thẻ vào nhau.
Rà soát kỹ và dán nhãn đầy đủ cho các trường tự do (health_status, private_life, criminal_record, political_view, religion, sexual_orientation). Đảm bảo tuân thủ NGUYÊN TẮC VÀNG VỀ TÍNH ĐỊNH DANH: chỉ bọc thẻ cho các thông tin có tính định danh cụ thể, TUYỆT ĐỐI CẤM dán nhãn cho các danh từ/đại từ chỉ nhóm/quan hệ chung chung (như "vợ chồng", "cả hai con chung", "con cái", "gia đình", "sức khỏe", "bệnh tật", "án tích", v.v.).
- Với ⟦health_status⟧, bạn chỉ được bọc các mô tả trực tiếp về bệnh lý, chẩn đoán, triệu chứng lâm sàng. TUYỆT ĐỐI KHÔNG bọc phần mô tả hệ quả đối với đời sống, sinh hoạt hay công việc vào thẻ ⟦health_status⟧ (các phần này nếu kịch bản yêu cầu sẽ bọc vào thẻ ⟦private_life⟧, nếu không thì để trống không bọc thẻ).
- Tránh bọc cả câu phức tạp hay đoạn dài. Phân rã ranh giới rõ ràng: Nếu một câu có cả phần bệnh trạng (health_status) và phần hậu quả ảnh hưởng đời tư (private_life), hãy bọc riêng biệt thành "⟦health_status⟧[bệnh trạng]⟦/health_status⟧ nên ⟦private_life⟧[hậu quả]⟦/private_life⟧". Chỉ gộp chung mệnh đề nhân quả vào một nhãn duy nhất nếu cả hai vế cùng thuộc về một trường thông tin.
- Đặc biệt với án tích (criminal_record), chỉ dán nhãn các câu/mệnh đề nêu cụ thể tội danh, hành vi phạm tội hoặc hình phạt cụ thể; TUYỆT ĐỐI KHÔNG dán nhãn các câu mô tả nỗ lực cải tạo, hoàn lương, sống gương mẫu hoặc tái hòa nhập cộng đồng nhằm tránh làm nhiễu ranh giới nhãn.
- Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ (ví dụ: "⟦family_relations⟧con gái là Phạm Như Giang⟦/family_relations⟧" hoặc "⟦family_relations⟧mẹ ruột là Nguyễn Thu Thùy Hiền⟦/family_relations⟧"). TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧.
4) KHÔNG tự ý bổ sung thêm thông tin cá nhân (tên riêng, số điện thoại, địa chỉ) mới nào khác vào văn bản (trừ khi chúng được dán nhãn thẻ đúng quy cách).
5) CHỈ trả về nội dung văn bản đã được hiệu đính. KHÔNG giải thích, KHÔNG markdown chứa ```."""
