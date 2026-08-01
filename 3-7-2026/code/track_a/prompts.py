# -*- coding: utf-8 -*-
from core.config import FIELDS

SUB_FORMATS = {
    "administrative": {
        "don_tu": "Đơn từ cá nhân (Đơn trình bày hoàn cảnh, Đơn xin nghỉ phép, Đơn khiếu nại, Đơn xin miễn giảm nghĩa vụ hành chính).",
        "to_khai": "Tờ khai tự thuật (Tờ khai lý lịch tư pháp, Bản tự thuật cá nhân, Tờ khai đăng ký biến động hộ tịch).",
        "bien_ban": "Biên bản báo cáo (Biên bản xác minh thực địa của cán bộ, Báo cáo giải trình y tế của bác sĩ, Biên bản hòa giải)."
    },
    "dialogue": {
        "consultation": "Cuộc trò chuyện tư vấn hành chính giữa công dân và cán bộ tiếp nhận tại Bộ phận một cửa UBND hoặc cơ quan thuế.",
        "medical_chat": "Hỏi đáp y tế chẩn đoán bệnh và khai thác tiền sử dị ứng, tiền sử bệnh án giữa bác sĩ và bệnh nhân.",
        "legal_chat": "Cuộc trao đổi tư vấn pháp lý giữa luật sư và khách hàng về tiền án tiền sự, tranh chấp đất đai hoặc hôn nhân.",
        "social_chat": "Đoạn chat/tin nhắn trao đổi qua mạng xã hội (Zalo, Messenger) chia sẻ thông tin cá nhân và thủ tục hành chính."
    },
    "third_person": {
        "diary": "Nhật ký cá nhân (Đoạn văn xuôi tự sự kể về cuộc sống riêng tư, nợ nần, trăn trước tôn giáo hoặc quá trình chữa bệnh).",
        "personal_email": "Thư điện tử (Email gửi sếp xin nghỉ phép y tế hoặc email gửi người thân tâm sự hoàn cảnh khó khăn).",
        "social_post": "Bài đăng/Bình luận trên mạng xã hội (tâm sự hoàn cảnh cá nhân, nhờ tư vấn thủ tục hoặc phản ánh dịch vụ)."
    }
}

TONES = {
    "formal_objective": "Trang trọng, khách quan, sử dụng ngôn từ hành chính chuẩn mực, trung tính, tuân thủ pháp luật.",
    "urgent_anxious": "Khẩn khoản, lo âu, thể hiện tình thế gấp gáp của nhân vật (ốm nặng, nợ nần, tai nạn) và cầu thị sự giúp đỡ.",
    "frustrated_complaining": "Bức xúc, phản ánh, thể hiện thái độ khiếu nại, đòi công bằng hoặc phản ánh gay gắt về vấn đề quyền lợi.",
    "cooperative_polite": "Hợp tác, lịch sự, thể hiện thái độ nhã nhặn, tôn trọng giữa hai bên đối thoại.",
    "casual_confidential": "Thân mật, tâm sự, sử dụng từ ngữ đời thường, giàu cảm xúc tự sự của nhân vật.",
    "casual_informal": "Bình dị, tự nhiên, sử dụng từ ngữ đời thường, có thể viết tắt thông dụng (cccd, sđt, vs, ah, ...), không quá trang nghiêm."
}

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
        spi_name_vi = (FIELDS.get(target_spi) or {}).get("name_vi", target_spi)
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
1c) TRÁNH DỒN TẤT CẢ PII VÀO ĐẦU VĂN BẢN (PII Distribution): Tuyệt đối tránh việc dồn toàn bộ thông tin cá nhân (họ tên, ngày sinh, số CCCD, địa chỉ, số điện thoại, email) vào ngay câu đầu tiên hoặc đoạn đầu tiên một cách cơ học và khô cứng (ví dụ: tránh viết "Tôi là Nguyễn Văn A, sinh ngày..., CCCD..., địa chỉ...", hoặc "Văn bản này được lập bởi ông Nguyễn Văn A, sinh ngày..., mang số Căn cước công dân..."). Hãy phân bổ và lồng ghép chúng một cách rải rác, tự nhiên vào các ngữ cảnh thích hợp trong suốt văn bản. Bắt buộc phải tách họ tên, ngày sinh và số CCCD ra các câu riêng biệt, hoặc đặt chúng ở các vị trí khác nhau trong văn bản (ví dụ: họ tên xuất hiện ở phần giới thiệu đầu văn bản, ngày sinh/CCCD xuất hiện ở phần nội dung hành chính hoặc ở các đoạn sau).
1d) LIÊN KẾT BIỆT DANH VÀ BỐI CẢNH SỐ ĐỊNH DANH (Proper Connectors & Context):
    - Khi viết biệt danh (name_alias), phải sử dụng các từ nối tự nhiên để làm rõ mối quan hệ (ví dụ: "ông Nguyễn Dũng (thường gọi là Lộc)", "ông Nguyễn Dũng, nghệ danh là Lộc"). Tuyệt đối không dùng dấu phẩy ghép thô cứng như "Nguyễn Dũng, Lộc".
    - Khi đưa các số định danh vào văn bản (CCCD, driver_license, passport_number...), bạn bắt buộc phải ghi rõ chính xác loại số định danh đó là gì ngay trước số (ví dụ: "số Căn cước công dân 0620 8480 0817", "số thẻ CCCD 0620 8480 0817", "số hộ chiếu B1234567"). Tuyệt đối không viết mơ hồ kiểu "mang số...", "có số..." mà không chỉ rõ loại số định danh, và TUYỆT ĐỐI KHÔNG được gán ghép số định danh cá nhân này thành số của loại giấy tờ khác (như không dùng số CCCD để làm số quyết định, số thẻ Thừa phát lại, số thẻ hành nghề, v.v.).
2) ĐA DẠNG HÓA VÀ TỰ NHIÊN HÓA ĐỊNH DẠNG (PII DIVERSITY): Chỉ đưa các thông tin định danh và nhạy cảm thực sự cần thiết theo dàn ý. Khi viết các thông tin định danh, bạn được khuyến khích đa dạng hóa định dạng hiển thị của chúng sao cho tự nhiên nhất với văn cảnh (tuyệt đối không chép dấu « » vào văn bản), ví dụ:
   - Đối với Ngày sinh (dob): có thể viết dạng 'ngày 29 tháng 08 năm 1982', '29/08/1982', '29-08-1982', '29.08.1982' hoặc '1982-08-29'.
   - Đối với Số điện thoại (phone): có thể viết dạng '0987.911.340', '0987 911 340', '+84 987 911 340', '(0987) 911 340' hoặc viết liền '0987911340'.
   - Đối với CCCD: có thể viết dạng cách khoảng '0361 8203 3012', '036-182-033-012' hoặc viết liền '036182033012'.
   - Đối với Địa chỉ (address) và Họ tên (full_name): lồng ghép tự nhiên vào ngữ cảnh (ví dụ: 'Nguyễn Thanh Quỳnh Liên', 'NGUYỄN THANH QUỲNH LIÊN', hoặc đảo họ tên ở cuối đơn...).
   Các trường khác không có định dạng đa dạng thì dùng đúng giá trị được cho. Đối với tình trạng hôn nhân (marital_status), bạn được phép chuyển chữ cái đầu thành chữ thường (ví dụ: 'góa', 'độc thân') để đảm bảo ngữ pháp.
3) BỌC CÁC TRƯỜNG THÔNG TIN ĐÃ ĐIỀN BẰNG THẺ NEO BẮT BUỘC:
   Mọi thông tin cá nhân/nhạy cảm (bao gồm cả các thông tin định danh cơ bản như full_name, dob, cccd, address, phone, email, bank_account, v.v. và các thông tin nhạy cảm) phải được bọc bằng thẻ `⟦field_name⟧giá trị⟦/field_name⟧`. Tuyệt đối không để xảy ra lỗi dán nhãn như viết dính tên thẻ vào văn bản.
   Ví dụ dán nhãn đúng: "Tôi tên là ⟦full_name⟧Nguyễn Tuấn Vĩnh⟦/full_name⟧, hiện đang làm thủ tục hành chính. Tôi sinh ngày ⟦dob⟧1972-03-08⟦/dob⟧ và đang tạm trú tại ⟦address⟧số 115/36 đường Kim Mã, phường Hải Châu, tỉnh Tây Ninh⟦/address⟧. Để phục vụ xác minh, tôi cung cấp số Căn cước công dân ⟦cccd⟧080-072-623-756⟦/cccd⟧. Mẹ tôi là ⟦family_relations⟧Nguyễn Kim Tú⟦/family_relations⟧ hiện thường trú tại ⟦address⟧phường Tự An, tỉnh Bắc Ninh⟦/address⟧."
3b) TUYỆT ĐỐI NGHIÊM CẤM LỒNG THẺ VÀO NHAU (No nested tags). Chỉ bọc thẻ cho đúng cụm từ mang thông tin giá trị thực tế của trường đó. KHÔNG bọc cả câu dài hay đoạn văn chứa các thực thể khác. Mọi thẻ phải nằm tách biệt, độc lập nhau.
    - SAI: ⟦private_life⟧áp lực từ việc tranh chấp quyền nuôi dưỡng con trai là ⟦family_relations⟧Trịnh Quang Công Tài⟦/family_relations⟧ và phân chia tài sản⟦/private_life⟧
    - ĐÚNG: áp lực từ việc ⟦private_life⟧tranh chấp quyền nuôi dưỡng con trai⟦/private_life⟧ là ⟦family_relations⟧con trai là Trịnh Quang Công Tài⟦/family_relations⟧ và ⟦private_life⟧phân chia tài sản⟦/private_life⟧
    - NGUYÊN TẮC VÀNG VỀ LOẠI BỎ TỪ DẪN NHẬP (Exclude Lead-in Prefixes): Khi dán nhãn cho bất kỳ trường thông tin nào (đặc biệt là name_alias, sexual_orientation, health_status, religion, political_view, v.v.), bạn TUYỆT ĐỐI KHÔNG được bọc các từ dẫn nhập, đại từ quan hệ, liên từ hoặc từ ngữ giới thiệu vào trong thẻ. Chỉ bọc đúng cụm từ mang nội dung giá trị cốt lõi.
      + Đối với biệt danh/bí danh (name_alias): Chỉ bọc tên biệt danh cụ thể (ví dụ: "thường gọi là ⟦name_alias⟧Linh⟦/name_alias⟧", "nghệ danh là ⟦name_alias⟧Đạt⟦/name_alias⟧"). TUYỆT ĐỐI KHÔNG bọc "thường gọi là", "nghệ danh là", "bí danh", "biệt danh".
      + Đối với xu hướng tình dục (sexual_orientation): Chỉ bọc xu hướng cụ thể (ví dụ: "⟦sexual_orientation⟧LGBTQ+⟦/sexual_orientation⟧", "⟦sexual_orientation⟧đồng tính nam⟦/sexual_orientation⟧"). TUYỆT ĐỐI KHÔNG bọc "xu hướng tình dục là", "người thuộc cộng đồng".
      + Đối với sức khỏe (health_status): Chỉ bọc tên bệnh hoặc tình trạng bệnh (ví dụ: "bị ⟦health_status⟧suy thận giai đoạn cuối⟦/health_status⟧", "mắc ⟦health_status⟧viêm khớp dạng thấp⟦/health_status⟧"). TUYỆT ĐỐI KHÔNG bọc "bị bệnh", "mắc chứng", "gặp vấn đề về sức khỏe là".
      + Đối với tôn giáo (religion) và quan điểm chính trị (political_view): Chỉ bọc giá trị tôn giáo/chính trị cốt lõi (ví dụ: "theo ⟦religion⟧đạo Phật⟦/religion⟧", "là ⟦political_view⟧quần chúng⟦/political_view⟧"). TUYỆT ĐỐI KHÔNG bọc "theo đạo", "tôn giáo là", "quan điểm chính trị là".
      + Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ. TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧. Thay vào đó, hãy bọc riêng biệt các thông tin chi tiết này bằng các thẻ tương ứng của chúng (ví dụ: địa chỉ của mẹ bọc bằng thẻ ⟦address⟧, số điện thoại bọc bằng thẻ ⟦phone⟧, ngày sinh bọc bằng thẻ ⟦dob⟧, CCCD bọc bằng thẻ ⟦cccd⟧).
4) KHÔNG ĐƯỢC gán ghép thông tin cá nhân của nhân vật làm thông tin của tổ chức/cơ quan. Các thông tin trong ngân hàng thông tin (Địa chỉ, Số điện thoại, Email) là thông tin cá nhân của nhân vật. Khi viết, hãy ghi rõ đó là địa chỉ cá nhân, số điện thoại cá nhân của người đại diện/người làm đơn/người chịu trách nhiệm chuyên môn chứ không được gán thành địa chỉ/số điện thoại của cơ quan báo chí, doanh nghiệp hay tổ chức.
5) CHỈ ĐƯỢC ĐỀ CẬP THÔNG TIN CÓ TRONG DANH SÁCH CHỌN: Bạn chỉ được viết và đề cập đến thông tin nhạy cảm của nhân vật nếu trường đó có mặt trong [NGÂN HÀNG THÔNG TIN NHÂN VẬT ĐỂ CHỌN] ở trên. TUYỆT ĐỐI CẤM tự ý bịa đặt hoặc đưa vào văn bản các thông tin nhạy cảm khác nếu trường đó có trong [DANH SÁCH TRƯỜNG THÔNG TIN CẤM ĐỀ CẬP] (Ví dụ: nếu trong danh sách cấm có 'criminal_record', cấm đề cập đến án tích hoặc lý lịch tư pháp; nếu có 'health_status', cấm đề cập đến bệnh trạng).
   - Đối với án tích (criminal_record): CHỈ viết về án tích (bao gồm cả việc xác nhận chưa từng bị kết án kèm Phiếu lý lịch tư pháp số hiệu ngẫu nhiên) NẾU trường `criminal_record` có trong danh sách chọn ở trên. Khi viết, bắt buộc bọc thẻ `⟦criminal_record⟧` cho toàn bộ mệnh đề đó (ví dụ: "⟦criminal_record⟧chưa từng bị kết án theo Phiếu lý lịch tư pháp số 452/STP-LLTP⟦/criminal_record⟧"). Nếu trường `criminal_record` không có mặt trong danh sách chọn ở trên, TUYỆT ĐỐI CẤM đề cập đến án tích hoặc lý lịch tư pháp dưới bất kỳ hình thức nào.
   - Đối với sức khỏe (health_status) và đời tư (private_life): TUYỆT ĐỐI CẤM gán ghép các thông tin chi phí chữa bệnh, khó khăn kinh tế, nợ nần, suy kiệt tài chính vào nhãn `⟦health_status⟧`. Nhãn `⟦health_status⟧` chỉ chứa thông tin y tế, chẩn đoán, bệnh trạng (ví dụ: 'bị suy thận giai đoạn cuối'). Phần khó khăn tài chính hoặc chi phí phát sinh (ví dụ: 'cần chi phí chạy thận liên tục') phải được bọc riêng bằng nhãn `⟦private_life⟧` (nếu trường `private_life` có mặt trong danh sách chọn). Nếu trường `private_life` không có trong danh sách chọn, TUYỆT ĐỐI CẤM đề cập đến chi phí chữa bệnh hay khó khăn tài chính/nợ nần do bệnh tật.
6) TUYỆT ĐỐI CẤM TỰ Ý MÔ TẢ/BỊA ĐẶT THÊM THÔNG TIN Y TẾ HOẶC ĐỜI TƯ: Bạn chỉ được sử dụng đúng các giá trị nhạy cảm đã cho trong ngân hàng thông tin để đưa vào văn bản.
   - Khi sinh thông tin cho các trường nhạy cảm có giá trị '[[LLM_GENERATE]]' (như health_status, private_life, religion, political_view, v.v.), bạn phải sinh các giá trị cực kỳ đơn giản, ngắn gọn và trung tính theo đúng định nghĩa chuẩn:
     + Đối với quan điểm chính trị (political_view): Bạn phải sinh một nhận thức, niềm tin hoặc lập trường chính trị/xã hội thực sự (ví dụ: 'ủng hộ chính sách phát triển công nghệ', 'ủng hộ bình đẳng xã hội', 'mất niềm tin vào các giá trị cũ'). TUYỆT ĐỐI CẤM sinh hoặc nhầm lẫn với các chức danh, đảng tịch, đoàn tịch hay tình trạng thành viên (như 'đảng viên', 'đoàn viên', 'đang viên dự bị', 'quần chúng').
     + Đối với tôn giáo (religion): Chỉ được sinh các tôn giáo phổ biến (như 'đạo Phật', 'Công giáo', 'Không tôn giáo').
     + Đối với sức khỏe (health_status): Chỉ ghi tên bệnh lý cơ bản (như 'bị suy thận giai đoạn cuối', 'bị tiểu đường nặng', 'bị gãy chân'), TUYỆT ĐỐI KHÔNG tự ý thêm thắt các chi tiết lâm sàng hay hậu quả bi kịch như 'phải nhập viện điều trị tích cực', 'nguy kịch', 'gánh nặng lớn đè lên vai nhân sự', 'suy kiệt thể chất nặng' hay 'chi phí chữa bệnh' (trừ khi có trường private_life được chọn).
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
    - NGUYÊN TẮC VÀNG VỀ LOẠI BỎ TỪ DẪN NHẬP (Exclude Lead-in Prefixes): Khi dán nhãn cho bất kỳ trường thông tin nào (đặc biệt là name_alias, sexual_orientation, health_status, religion, political_view, v.v.), bạn TUYỆT ĐỐI KHÔNG được bọc các từ dẫn nhập, đại từ quan hệ, liên từ hoặc từ ngữ giới thiệu vào trong thẻ. Chỉ bọc đúng cụm từ mang nội dung giá trị cốt lõi.
      + Đối với biệt danh/bí danh (name_alias): Chỉ bọc tên biệt danh cụ thể (ví dụ: "thường gọi là ⟦name_alias⟧Linh⟦/name_alias⟧", "nghệ danh là ⟦name_alias⟧Đạt⟦/name_alias⟧"). TUYỆT ĐỐI KHÔNG bọc "thường gọi là", "nghệ danh là", "bí danh", "biệt danh".
      + Đối với xu hướng tình dục (sexual_orientation): Chỉ bọc xu hướng cụ thể (ví dụ: "⟦sexual_orientation⟧LGBTQ+⟦/sexual_orientation⟧", "⟦sexual_orientation⟧đồng tính nam⟦/sexual_orientation⟧"). TUYỆT ĐỐI KHÔNG bọc "xu hướng tình dục là", "người thuộc cộng đồng".
      + Đối với sức khỏe (health_status): Chỉ bọc tên bệnh hoặc tình trạng bệnh (ví dụ: "bị ⟦health_status⟧suy thận giai đoạn cuối⟦/health_status⟧", "mắc ⟦health_status⟧viêm khớp dạng thấp⟦/health_status⟧"). TUYỆT ĐỐI KHÔNG bọc "bị bệnh", "mắc chứng", "gặp vấn đề về sức khỏe là".
      + Đối với tôn giáo (religion) và quan điểm chính trị (political_view): Chỉ bọc giá trị tôn giáo/chính trị cốt lõi (ví dụ: "theo ⟦religion⟧đạo Phật⟦/religion⟧", "là ⟦political_view⟧quần chúng⟦/political_view⟧"). TUYỆT ĐỐI KHÔNG bọc "theo đạo", "tôn giáo là", "quan điểm chính trị là".
      + Đối với quan hệ gia đình (family_relations) và thông tin người thân: Chỉ bọc thẻ ⟦family_relations⟧ cho cụm từ chỉ mối quan hệ và tên của họ. TUYỆT ĐỐI KHÔNG bọc các thông tin chi tiết của người thân (như ngày sinh, CCCD, địa chỉ, số điện thoại của họ) vào trong thẻ ⟦family_relations⟧. Thay vào đó, hãy bọc riêng biệt các thông tin chi tiết này bằng các thẻ tương ứng của chúng (ví dụ: địa chỉ của mẹ bọc bằng thẻ ⟦address⟧, số điện thoại bọc bằng thẻ ⟦phone⟧, ngày sinh bọc bằng thẻ ⟦dob⟧, CCCD bọc bằng thẻ ⟦cccd⟧).
    - Rà soát kỹ và dán nhãn đầy đủ cho tất cả các thông tin cá nhân cơ bản (full_name, dob, cccd, address, phone, email, bank_account, v.v.) cũng như các trường tự do (health_status, private_life, criminal_record, political_view, religion, sexual_orientation). Đảm bảo mọi giá trị thuộc các trường được chọn đều được bọc thẻ đúng quy cách. Đảm bảo tuân thủ NGUYÊN TẮC VÀNG VỀ TÍNH ĐỊNH DANH: chỉ bọc thẻ cho các thông tin có tính định danh cụ thể, TUYỆT ĐỐI CẤM dán nhãn cho các danh từ/đại từ chỉ nhóm/quan hệ chung chung (như "vợ chồng", "cả hai con chung", "con cái", "gia đình", "sức khỏe", "bệnh tật", "án tích", v.v.).
    - Đối với trường tình trạng hôn nhân (marital_status) (ví dụ: 'Góa', 'Độc thân', 'Kết hôn'), bạn phải chuyển thành chữ thường (ví dụ: 'góa', 'độc thân', 'kết hôn') khi viết vào câu để đảm bảo đúng ngữ pháp tiếng Việt.
    - Đối với quan điểm chính trị (political_view): Bạn BẮT BUỘC phải rà soát và chuyển đổi các chức danh, đảng tịch, đoàn tịch (như 'đảng viên', 'đoàn viên', 'đảng viên dự bị', 'quần chúng') thành các nhận thức, thái độ hoặc lập trường chính trị/xã hội thực sự (ví dụ: sửa "với tư cách là một ⟦political_view⟧đảng viên/đảng viên dự bị⟦/political_view⟧" thành "với ⟦political_view⟧lập trường luôn chấp hành các chủ trương chính sách của Nhà nước⟦/political_view⟧" hoặc "với tư cách là một người ⟦political_view⟧ủng hộ đường lối phát triển chung⟦/political_view⟧").
    - Sửa các lỗi diễn đạt rập khuôn hoặc ghép nhãn gượng ép (ví dụ: sửa "tôn giáo là không tôn giáo" thành "không theo tôn giáo nào"; sửa "án tích là không có án tích" thành "chưa từng bị kết án").
    - Đảm bảo Địa chỉ, Số điện thoại, Email của nhân vật được nêu rõ là thông tin cá nhân của họ chứ không bị gán ghép thành địa chỉ/số liên lạc của cơ quan hay tổ chức.
    - Đảm bảo thông tin về việc nhân vật không có án tích đi kèm tham chiếu đến Phiếu lý lịch tư pháp phải được bọc thẻ ⟦criminal_record⟧ đầy đủ (ví dụ: "⟦criminal_record⟧chưa từng bị kết án theo Phiếu lý lịch tư pháp số [số hiệu ngẫu nhiên]⟦/criminal_record⟧").
    - Tránh các câu ghép lủng củng, tối nghĩa hoặc lặp từ gượng ép khi lồng ghép thông tin từ ngân hàng dữ liệu.
1c) RÀ SOÁT VÀ PHÂN BỔ LẠI PII (PII Distribution): Rà soát và phân bổ lại các thông tin định danh (họ tên, ngày sinh, CCCD, địa chỉ, điện thoại...) nếu chúng đang bị dồn tất cả vào ngay câu đầu tiên/đoạn đầu tiên một cách cơ học và khô cứng (ví dụ: sửa ngay các câu mở đầu kiểu "Văn bản này được lập bởi ông Nguyễn Văn A, sinh ngày..., mang số Căn cước công dân..."). Sửa đổi bằng cách tách chúng ra thành các câu riêng biệt hoặc lồng ghép chúng một cách tự nhiên và rải rác ở các vị trí khác nhau trong văn bản (ví dụ: họ tên ở đầu đơn, ngày sinh và số CCCD chuyển sang câu tiếp theo hoặc đoạn sau, số điện thoại và email chuyển xuống cuối phần liên hệ).
1d) LIÊN KẾT BIỆT DANH VÀ BỐI CẢNH SỐ ĐỊNH DANH:
    - Đảm bảo biệt danh (name_alias) được nối bằng từ ngữ tự nhiên làm rõ mối quan hệ (ví dụ: "ông Nguyễn Dũng (thường gọi là Lộc)" hoặc "ông Nguyễn Dũng, biệt danh là Lộc"), sửa ngay nếu đang viết kiểu ghép thô cứng bằng dấu phẩy như "Nguyễn Dũng, Lộc".
    - Đảm bảo các số định danh (CCCD, hộ chiếu, GPLX...) có danh xưng/loại số định danh cụ thể đi kèm chính xác rõ ràng ngay trước số (ví dụ: "số Căn cước công dân...", "số thẻ CCCD..."), sửa đổi toàn bộ các câu ghi mơ hồ dạng "mang số...", "có số..." mà không chỉ rõ loại số định danh, hoặc gán ghép sai loại số định danh (như gán số CCCD thành số quyết định, số thẻ Thừa phát lại, số thẻ hành nghề, v.v.).
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
