# HƯỚNG DẪN CHI TIẾT HỆ THỐNG PIPELINE SECUREPREP
 
Dự án **SecurePrep** phát triển và vận hành hai hệ thống pipeline bổ trợ lẫn nhau nhằm mục tiêu tạo lập tập dữ liệu PII/SPI (Thông tin nhận dạng cá nhân và Thông tin cá nhân nhạy cảm) chất lượng cao cho tiếng Việt, tuân thủ Nghị định 356/2025/NĐ-CP.

Tài liệu này mô tả chi tiết từng bước vận hành trong cả hai pipeline.

---

## PHẦN 1: PIPELINE SINH DỮ LIỆU PII/SPI (16 BƯỚC)

Quy trình hoạt động theo nguyên tắc **Constraint-First (LLM-as-writer)**. Toàn bộ logic kiểm soát và sinh dữ liệu định danh được thực hiện bằng mã nguồn Python tĩnh để tránh hiện tượng LLM tự tạo thông tin ảo (hallucination) gây lệch nhãn.

### Bước 1: Sinh và Lựa chọn Loại Bản Ghi (`record_type`)
* **Mục tiêu**: Xác định loại văn bản hành chính/tự sự cần sinh (ví dụ: Đơn xin học bổng, Tờ khai đăng ký kết hôn, Email gửi bổ sung hồ sơ...).
* **Cách thức hoạt động**: 
  - Ở chế độ mặc định: Hệ thống bốc ngẫu nhiên một mẫu từ bộ dữ liệu thô đã làm sạch (`raw_data_cleaned`).
  - Ở chế độ Form-based: Dùng một `form_info` cố định làm đầu vào để sinh hàng loạt bản ghi cho cùng một cấu trúc biểu mẫu nhưng với các hồ sơ công dân khác nhau.
* **Đầu ra**: Loại bản ghi (`record_type_info`) kèm mẫu biểu mẫu trống.

### Bước 2: Sinh Hồ Sơ Giả Lập (`profile_fake`)
* **Mục tiêu**: Xây dựng một thực thể hồ sơ công dân giả lập hoàn chỉnh, giàu thông tin PII/SPI làm dữ liệu nguồn.
* **Cách thức hoạt động**: 
  - Lấy dữ liệu nền từ `profile_core`.
  - Thực hiện các hàm sinh nâng cao:
    - `gen_cccd()`: Sinh số CCCD 12 chữ số hợp lệ, trong đó chữ số mã giới tính/thế kỷ sinh và mã năm sinh phải khớp với thông tin hồ sơ.
    - `pick_ho()` và `pick_ten()`: Lựa chọn họ tên ngẫu nhiên nhưng phải khớp với trường tộc người (`dan_toc`) bằng cách tra cứu danh mục `ETHNIC_NAMES` (ví dụ: dân tộc Mông, Thái, Tày sẽ có họ tên đặc thù).
    - Phân bổ vùng miền Bắc/Trung/Nam theo tỷ lệ chuẩn 40/20/40.
* **Đầu ra**: File JSON chứa hồ sơ giả lập (`profile_fake`).

### Bước 3: Kiểm duyệt Hồ Sơ (Sanity Check Profile)
* **Mục tiêu**: Loại bỏ các hồ sơ giả lập không hợp lệ hoặc chứa các thông tin mâu thuẫn trước khi gửi cho LLM.
* **Cách thức hoạt động**: Chạy hàm `sanity_check_profile()`. Kiểm tra độ dài CCCD (12 số), định dạng ngày sinh, định dạng số điện thoại, sự thống nhất giữa giới tính và mã CCCD.
* **Chốt kiểm soát (Gate)**: Nếu kiểm duyệt thất bại, hệ thống quay lại **Bước 2** để tái tạo hồ sơ mới (thử lại tối đa 5 lần).

### Bước 4: Trích xuất Biểu Mẫu Trống (`form_blank`)
* **Mục tiêu**: Xác định các trường thông tin cần điền và cấu trúc của biểu mẫu trống.
* **Cách thức hoạt động**: Phân tích cú pháp của mẫu văn bản gốc từ Bước 1, xác định các trường giữ chỗ (placeholders) dạng `[Họ và tên]`, `[Số điện thoại]`, `[Địa chỉ]`...
* **Đầu ra**: Cấu trúc biểu mẫu trống (`form_blank`).

### Bước 5: Sinh Danh Sách Sự Kiện và Ngữ Cảnh Nền (`event_list` & `background_context`)
* **Mục tiêu**: Tạo ra lý do logic để văn bản hành chính/tự sự này tồn tại (ví dụ: lý do nộp đơn, hoàn cảnh của công dân).
* **Cách thức hoạt động**: 
  - LLM (mô hình sinh) nhận thông tin từ `profile_fake` và `record_type_info`.
  - Sinh ra danh sách các sự kiện (`event_list`) dạng cấu trúc JSON cùng đoạn mô tả hoàn cảnh nền (`background_context`).
  - Hệ thống sinh 2 ứng viên (candidates), sau đó tính điểm ưu tiên dựa trên độ tự nhiên và mức độ liên quan để chọn ra kết quả tốt nhất.
* **Đầu ra**: JSON chứa `event_list`, `background_context` và nhãn loại văn bản (`record_tags`).

### Bước 6: Điền Biểu Mẫu Thô (`form_filled`) & Sinh Văn Bản Gốc (`form_filled_original`)
* **Mục tiêu**: Tạo ra một văn bản tham chiếu đã điền đầy đủ thông tin sạch để phục vụ đối chiếu và đo lường.
* **Cách thức hoạt động**: 
  - Bản ghi `form_filled` được điền tự động bằng cách map trực tiếp các trường trong `profile_fake` vào `form_blank`.
  - Hàm `build_form_filled_text()` kết xuất văn bản thô đầy đủ giá trị thực của hồ sơ.

### Bước 7: Kiểm Tra Hợp Lệ Điều Khiển (Legal/Control Validate)
* **Mục tiêu**: Đảm bảo các quy định pháp luật và logic thực tế được tuân thủ (ví dụ: tuổi kết hôn phải >= 18, tuổi đi học đúng quy định...).
* **Cách thức hoạt động**: Chạy hàm `legal_validate()`. 
* **Chốt kiểm soát (Gate)**: 
  - Nếu thất bại thông thường: Trả luồng về **Bước 5** để sinh lại sự kiện nền.
  - Nếu thất bại nghiêm trọng (Fatal): Trở lại hẳn **Bước 2** để sinh lại hồ sơ công dân mới.

### Bước 8: Lập Danh Sách Tiêm PII/SPI (`injection_list`)
* **Mục tiêu**: Chỉ định chính xác các giá trị PII/SPI nào bắt buộc phải xuất hiện trong văn bản cuối cùng và giá trị nào cần ẩn đi.
* **Cách thức hoạt động**:
  - Hàm `build_injection_list()` lọc ra các trường trực tiếp (`direct_identifiers`) hoặc nhạy cảm (`sensitivity=SPI`).
  - Gắn nhãn `annotate=true` cho các trường bắt buộc và đưa giá trị chuỗi của chúng vào danh sách khóa chặt (`locked_values`).
  - Các PII còn lại trong profile được liệt vào danh sách cấm (`forbidden_values`) để ngăn chặn việc LLM tự viết bừa gây nhiễu dữ liệu.

### Bước 9: Thiết Lập Kế Hoạch Định Dạng (`format_plan`)
* **Mục tiêu**: Định hướng phong cách viết văn bản cho LLM.
* **Cách thức hoạt động**: Lấy mẫu ngẫu nhiên từ registry quản lý kiểu định dạng để quyết định: `style` (giọng điệu chính thức/email/chat), `tone` (trang trọng/thân mật), và cấp độ độ khó NER (`easy`, `medium`, `hard`).

### Bước 9b: Đa Dạng Hóa Định Dạng
* **Mục tiêu**: Cân bằng phân phối các loại văn bản trong toàn bộ tập dữ liệu (tránh lệch tỷ lệ).
* **Cách thức hoạt động**: Đối chiếu phân bổ thực tế của pool dữ liệu để điều chỉnh phân phối lấy mẫu cho các tags/styles tiếp theo.
* **Kiểm soát đặc biệt**: Nếu `fmt_id = 1` (Biểu mẫu hành chính truyền thống có sẵn), hệ thống sẽ **bỏ qua bước gọi LLM ở Bước 10** và dùng luôn văn bản `form_filled_original` từ Bước 6 nhằm tối ưu hóa chi phí.

### Bước 10: Sinh Văn Bản Nháp Đầu Tiên (`initial_draft`)
* **Mục tiêu**: Yêu cầu LLM viết một đoạn văn hành chính tự sự tự nhiên.
* **Cách thức hoạt động**:
  - LLM nhận `prompt_b10` chứa thông tin từ `background`, `injection_list` và các ràng buộc cấm tự ý sinh thêm số, tên riêng bên ngoài danh sách khóa.
  - LLM sinh ra văn bản dưới dạng đoạn văn văn xuôi (prose) tự nhiên.

### Bước 10b: Lựa Chọn Bản Sửa Đổi (Revision Selection)
* **Mục tiêu**: Chọn ra bản thảo văn bản tốt nhất.
* **Cách thức hoạt động**: Nếu LLM sinh ra cả bản nháp gốc (`initial_draft`) và bản chỉnh sửa (`revised_draft`), hệ thống sẽ chạy thuật toán so sánh chất lượng để giữ lại bản tối ưu hơn, đảm bảo độ bao phủ thông tin cao hơn.

### Bước 11: Kiểm Duyệt Nội Dung & Tự Sửa Lỗi (Validation & Auto-fix)
* **Mục tiêu**: Đảm bảo 100% các giá trị trong `locked_values` xuất hiện đầy đủ và không bị LLM tự ý sinh thêm các PII/SPI lạ (hallucination).
* **Cách thức hoạt động**: Chạy hàm `validate_content()`. 
* **Chốt kiểm soát (Gate)**:
  - Nếu gặp lỗi nhẹ (`SOFT_FAIL` - thiếu 1 vài giá trị khóa): Trực tiếp gửi văn bản kèm lỗi cho LLM chạy prompt tự động sửa lỗi chính tả/bổ sung (`build_prompt_autofix`). Cho phép tự sửa tối đa **01 lần**.
  - Nếu gặp lỗi nặng (`HARD_FAIL` - tự chế thông tin định danh mới hoặc tỉ lệ bao phủ quá thấp): Hủy bản nháp và quay lại **Bước 5**.

### Bước 11b: Tạo Nhiễu Ngẫu Nhiên (Optional Noise Injection)
* **Mục tiêu**: Giả lập lỗi quét văn bản OCR, lỗi gõ phím của con người để tăng tính thực tế của dữ liệu.
* **Cách thức hoạt động**:
  - Tiêm ngẫu nhiên các ký tự nhiễu, lỗi chính tả nhẹ ngoài vùng các từ khóa thuộc `locked_values` thông qua hàm `apply_noise_safely()`.
  - **Quy tắc an toàn**: Quá trình tạo nhiễu nếu vô tình vi phạm hoặc làm hỏng cấu trúc của `locked_values` thì hệ thống sẽ tự động khôi phục (rollback) về bản văn bản sạch ở Bước 11 thay vì hủy bỏ cả bản ghi.

### Bước 12: Đánh Giá Độ Đa Dạng (Diversity Check)
* **Mục tiêu**: Tránh trùng lặp cấu trúc câu và từ vựng quá mức giữa các bản ghi trong tập dữ liệu.
* **Cách thức hoạt động**: Tính điểm tương đồng Cosine giữa văn bản vừa sinh với tập các văn bản đã sinh trước đó trong `diversity_pool`.
* **Chốt kiểm soát (Gate)**: Nếu độ tương đồng vượt ngưỡng (> 0.45), hệ thống sẽ tăng nhiệt độ (`temperature`) của LLM lên và thử sinh lại (hoặc chuyển về **Bước 5**).

### Bước 13: Đánh Dấu Spans Nhãn L1/L2
* **Mục tiêu**: Định vị chính xác tọa độ (start/end offsets) của các PII/SPI trong văn bản.
* **Cách thức hoạt động**: 
  - Chạy hàm `annotate_spans()`.
  - So khớp chính xác chuỗi ký tự của các trường thuộc `locked_values` trong văn bản cuối cùng để ghi nhận vị trí index. Gán nhãn cấp 1 (L1) và cấp 2 (L2) theo quy định trong schema.

### Bước 14: Lưu Trữ Metadata
* **Mục tiêu**: Ghi nhận toàn bộ thông tin nền để phục vụ công tác kiểm duyệt, phân tách dữ liệu và tái lập (reproducibility).
* **Cách thức hoạt động**: Tổng hợp thông tin về model sinh, cấu trúc form gốc, các tham số cấu hình, và các điểm số đo lường.

### Bước 15: Kết Xuất Bản Ghi NER (`annotated_record`)
* **Mục tiêu**: Lưu bản ghi hoàn chỉnh ra ổ cứng.
* **Cách thức hoạt động**: Ghi đối tượng bản ghi hoàn chỉnh gồm: `content` (văn bản), `spans` (danh sách nhãn và tọa độ), `metadata` vào tệp JSON đầu ra.

### Bước 16: Đánh Giá Chất Lượng Tập Dữ Liệu
* **Mục tiêu**: Đánh giá tổng quát toàn bộ lô dữ liệu (batch/pool) được tạo ra.
* **Cách thức hoạt động**: Chạy các chỉ số thống kê về độ đa dạng từ vựng (MATTR >= 0.80), chỉ số phân phối (Vendi score >= 40), điểm tổng hợp chất lượng tập dữ liệu (Dataset S >= 0.70). Nếu đạt yêu cầu, lô dữ liệu sẽ chính thức được duyệt.

---

## PHẦN 2: PIPELINE SỬA LỖI NHÃN ↔ GIÁ TRỊ (PHỄU 5 TẦNG)

Đây là quy trình hậu xử lý tự động chạy độc lập để quét sạch các lỗi gán sai nhãn văn xuôi (lệch khớp giữa từ mô tả câu và dữ liệu span thực tế).

### Tầng A: Nạp Kho Tri Thức (Knowledge Base)
* **Vai trò**: Cung cấp bộ quy tắc định dạng cứng và từ vựng đóng để đưa ra quyết định mà không cần hỏi LLM.
* **Hoạt động**: 
  - Nạp các regex định dạng chuẩn cho CCCD, Số điện thoại, Biển số xe, Hộ chiếu, GPLX, Mã số thuế.
  - Nạp danh mục từ điển đóng tiếng Việt như: 54 dân tộc, Danh sách tôn giáo, Các cụm từ chỉ giới tính, Tình trạng hôn nhân.

### Tầng B: Bộ Phát Hiện Xác Định (Deterministic Detector)
* **Vai trò**: Quét văn bản hành chính theo hai chiều để tìm ra lỗi.
* **Hoạt động**:
  1. **Quét theo nhãn**: Tìm kiếm các từ khóa chỉ nhãn (ví dụ: "số điện thoại là", "số căn cước là") rồi kiểm tra giá trị ngay phía sau có khớp định dạng tương ứng không.
  2. **Quét theo giá trị (Neo vào span)**: Duyệt qua tất cả các nhãn spans đã được gán tọa độ chính xác. Tìm từ gợi ý đứng trước nó trong văn xuôi. Nếu từ gợi ý sai (ví dụ đứng trước một số CCCD lại là chữ *"số điện thoại"*), hệ thống sẽ lập tức đánh dấu lỗi.

### Tầng C: Bộ Phân Loại & Tự Sửa Lỗi (Triage & Local Fix)
* **Vai trò**: Đưa ra hướng xử lý tối ưu nhất cho từng ca lỗi phát hiện được.
* **Hoạt động**: Chia lỗi thành 3 hướng xử lý chính:
  1. **Quy tắc RELABEL (Ưu tiên cao nhất)**: Khi nhãn span đã gán đúng loại thực thể nhưng câu văn xuôi viết sai chữ gợi ý. Hệ thống tiến hành thay thế chữ gợi ý trong câu văn xuôi bằng chữ đúng (Ví dụ: Đổi *"số điện thoại"* thành *"số CCCD"*). Cách này an toàn tuyệt đối, không làm thay đổi giá trị thực tế hay phá vỡ tọa độ span.
  2. **Quy tắc VALUE-FIX**: Áp dụng khi phát hiện một giá trị thô bị sai nằm ngoài vùng nhãn spans. Hệ thống tự động thay thế bằng giá trị gốc tương ứng từ `profile_fake`.
  3. **Quy tắc ESCALATE**: Đối với các trường hợp phức tạp (sửa bên trong cụm từ dài, bất đồng 3 chiều không rõ nguyên nhân), hệ thống sẽ gom lại để chuyển lên Tầng D.

### Tầng D: Đưa Lên Mô Hình (Gemini Escalation)
* **Vai trò**: Giải quyết các ca lỗi phức tạp nhất bằng LLM.
* **Hoạt động**:
  - Không gửi toàn bộ văn bản 9.000 tokens gây lãng phí.
  - Hệ thống chỉ cắt riêng **cửa sổ văn bản** hẹp xung quanh vị trí lỗi (khoảng 100-200 từ), gửi kèm giả thuyết của bộ phát hiện và các giá trị gốc liên quan.
  - Sử dụng mô hình `ts/gemini-3.1-flash-lite` qua cổng API tối ưu chi phí, kết hợp gom lô (batching) và bộ nhớ đệm ngữ cảnh (context caching).

### Tầng E: Áp Dụng Chỉnh Sửa & Tính Lại Offset (Apply & Re-validate)
* **Vai trò**: Thực thi các thay đổi vào văn bản và đảm bảo tính toàn vẹn của dữ liệu spans.
* **Hoạt động**:
  - Áp dụng các thay đổi từ Tầng C và Tầng D vào văn bản chính thức.
  - Chạy hàm `remap_spans()`: Tự động tính toán lại vị trí bắt đầu và kết thúc (start/end index offsets) của toàn bộ các spans trong văn bản do độ dài câu chữ đã bị thay đổi sau khi sửa lỗi gợi ý.
  - Quét lại toàn bộ văn bản bằng Tầng B một lần nữa để xác nhận lỗi đã giảm về **0**. Ghi file đã sửa và file audit chi tiết ra thư mục đầu ra.

---

## PHẦN 3: BẢN ĐỒ TẬP TIN CODE TRONG HỆ THỐNG

Bạn có thể tra cứu mã nguồn thực thi trực tiếp của các bước trên tại các file:

### Sinh dữ liệu (16 bước):
* **[gen-data-v2.ipynb](file:///d:/Đại Học/SecurePrep/Project/code/gen-data-v2.ipynb)**: Notebook trung tâm chạy toàn bộ 16 bước sinh và lọc dữ liệu.
* **[build_profile_core.py](file:///d:/Đại Học/SecurePrep/Project/data/profile_core/build_profile_core.py)**: Module sinh profile cá nhân giả lập cho Bước 2.

### Sửa lỗi nhãn-giá trị (Hậu xử lý):
* **[pii_fixer_pipeline.py](file:///d:/Đại Học/SecurePrep/Project/code/dacn1/pii_fixer_pipeline.py)**: Notebook điều phối toàn bộ phễu 5 tầng sửa lỗi.
* **[pii_fixer_core.py](file:///d:/Đại Học/SecurePrep/Project/code/dacn1/pii_fixer_core.py)**: Mã nguồn lõi xử lý các thuật toán Tầng A, B, C và remap offsets.
* **[final_real.py](file:///d:/Đại Học/SecurePrep/Project/code/dacn1/final_real.py)**: Phiên bản script Python tối ưu hóa để chạy đa luồng trên server cho toàn bộ shards dữ liệu.

---

## PHẦN 4: HƯỚNG DẪN KHỞI CHẠY PIPELINE SỬA LỖI

Để tiến hành rà soát lỗi và làm sạch dữ liệu tự động, hãy thực hiện các bước sau:

1. Thiết lập API Key của cổng vilao.ai (hoặc OpenAI) bằng cách điền vào cấu hình biến `GEMINI_API_KEY` trong file `final_real.py` hoặc thiết lập biến môi trường.
2. Đặt các tệp dữ liệu cần rà soát (.json) vào thư mục `data/in/`.
3. Chạy câu lệnh thực thi:
   ```powershell
   python code/dacn1/final_real.py
   ```
4. Kết quả sau khi được làm sạch hoàn chỉnh và tính lại chính xác tọa độ spans sẽ được xuất ra tại thư mục `data/out/`.
