# BÁO CÁO QUY TRÌNH HỢP NHẤT VÀ CÁC VẤN ĐỀ GÁN NHÃN (SECUREPREP)

Tài liệu này tổng hợp toàn bộ cấu trúc quy trình sinh dữ liệu (Pipeline), mô tả chi tiết từng bước hoạt động và các vấn đề kỹ thuật liên quan đến ranh giới gán nhãn thực thể nhạy cảm (PII/SPI).

---

## PHẦN 1: QUY TRÌNH PIPELINE HIỆN TẠI (STAGES OF GENERATION & ANNOTATION)

Quy trình hoạt động theo nguyên tắc **Constraint-First** (Code kiểm soát giá trị định danh trước, LLM chỉ đảm nhận việc sinh văn bản tự nhiên bao quanh) và **Deterministic Annotation** (Gán nhãn xác định bằng thuật toán ở bước cuối, không phụ thuộc LLM).

Luồng xử lý gồm 10 bước chính như sau:

### Bước 1: Trích xuất hồ sơ gốc (Profile)
- Hệ thống tải dữ liệu tĩnh từ ngân hàng hồ sơ `profile_bank.jsonl` (khoảng 30,000 hồ sơ công dân nhân tạo).
- Mỗi hồ sơ chứa đầy đủ thông tin tĩnh như Họ tên, ngày sinh, CCCD, số điện thoại, tôn giáo, án tích, tình trạng sức khỏe.

### Bước 2: Lựa chọn kịch bản (Scenario)
- Chọn ngẫu nhiên kịch bản từ `scenario_catalog.json` tương ứng với văn phong cần sinh (như `administrative` - hành chính, `dialogue` - đối thoại tư vấn, `prose` - văn xuôi tự sự).
- Mỗi kịch bản quy định rõ danh sách các nhãn nhạy cảm mục tiêu (`spi_targets`) cần khai thác.

### Bước 3: Ánh xạ Biểu mẫu (Form Reference)
- Dựa trên từ khóa của kịch bản, hệ thống tìm kiếm trong cơ sở dữ liệu `form.json` để chọn ra biểu mẫu dịch vụ công phù hợp (ví dụ: Tờ khai lý lịch tư pháp, Đơn xin nghỉ phép...).
- Biểu mẫu này được lấy làm siêu dữ liệu (Metadata) đính kèm vào bản ghi đầu ra phục vụ đối chiếu và lưu trữ, không gửi trực tiếp sang LLM.

### Bước 4: Tạo Manifest ràng buộc (build_manifest)
- Hệ thống tính toán tập hợp các trường PII/SPI bắt buộc phải xuất hiện.
- **Quy tắc lọc đặc biệt (Đã sửa đổi):**
  - Trạng thái án tích sạch (không có án tích) được loại khỏi Manifest nhạy cảm để đẩy sang tệp bổ trợ (Supplements) dưới dạng văn bản thường.
  - Tôn giáo mặc định (Không tôn giáo) hoặc chính trị mặc định (Quần chúng) sẽ được tự động bỏ qua nếu kịch bản có văn phong phi hành chính (như hội thoại, văn xuôi).

### Bước 5: Sinh thông tin bổ trợ (realize_supplemental)
- Sinh các thông tin bổ trợ nằm ngoài Manifest nhãn nhạy cảm, bao gồm:
  - Cơ quan tiếp nhận hồ sơ.
  - Số quyết định giấy tờ (đóng vai trò làm nhiễu - Distractors).
  - Họ tên, thông tin PII của người thân (được mượn ngẫu nhiên từ các hồ sơ khác để tạo ngữ cảnh đa chủ thể).

### Bước 6: Xây dựng Prompt dàn ý và nháp (Prompt Builder)
- Trộn Manifest và Supplements để tạo Prompt chi tiết. 
- Prompt yêu cầu LLM lập dàn ý (Outline) trước để cố định bối cảnh, sau đó yêu cầu sinh bản nháp (Draft) lồng ghép các từ khóa. Chỉ thị LLM bọc thẻ `⟦field⟧giá trị⟦/field⟧` quanh các giá trị nhạy cảm.

### Bước 7: Sinh bản nháp & Hiệu đính (Gemini LLM)
- Gọi API Gemini Flash.
- Quá trình chạy qua 2 giai đoạn: sinh bản nháp ở nhiệt độ cao (temp=0.85) để tăng độ đa dạng ngôn ngữ, sau đó chạy qua mô hình hiệu đính (Revision) ở nhiệt độ thấp (temp=0.20) để sửa lỗi đóng/mở thẻ <code>⟦/field⟧</code> và chuẩn hóa câu chữ.

### Bước 8: Kiểm duyệt chất lượng (Validation / Retry Loop)
- Trích xuất thẻ mở đóng và làm sạch văn bản thô.
- Gọi hàm `coverage()` để kiểm tra xem văn bản sạch có chứa đầy đủ thông tin từ manifest hay không.
- **Nới lỏng quy tắc (Đã sửa đổi):** Chấp nhận độ phủ của `full_name` nếu văn bản chứa Họ tên đầy đủ HOẶC chỉ chứa tên riêng (`given_name`), tránh lỗi phát sinh do LLM đối thoại tự nhiên chỉ gọi tên riêng.
- Nếu không đạt độ phủ hoặc thẻ bị hỏng, hệ thống sẽ tự động chạy lại (regen) tối đa 3 lần.

### Bước 9: Bộ gán nhãn Heuristic 3 lớp (Annotator)
- Chạy thuật toán gán nhãn xác định trên văn bản sạch bằng code Python (không gọi LLM):
  - **Lớp 1 (Khớp chính xác):** Dò tìm các chuỗi số CCCD, điện thoại, email, địa chỉ.
  - **Lớp 2 (Từ khóa ngữ cảnh):** Gán nhãn dân tộc, tôn giáo, giới tính khi đi kèm từ khóa dẫn đường (cues) để tránh gán nhãn nhầm các từ phổ thông.
  - **Lớp 3 (Thực thể nhạy cảm tự do):** Trích xuất tọa độ từ thẻ đóng mở `⟦field⟧` của LLM.
- **Gỡ chồng lấn (Đã sửa đổi):** Áp dụng bảng trọng số ưu tiên `PRIORITIES`. Nhãn định danh thành phần (như `given_name`) được ưu tiên cao hơn nhãn ngữ cảnh diện rộng (như `private_life`), tránh bị nuốt mất nhãn con.

### Bước 10: Xuất tệp gộp (Output JSONL)
- Ghi nhận hồ sơ dữ liệu hoàn chỉnh ở định dạng JSON Lines chứa văn bản sạch (`content`), danh sách spans nhãn phẳng (`spans`) và các thông tin kỹ thuật bổ trợ.

---

## PHẦN 2: PHÂN TÍCH CÁC VẤN ĐỀ GÁN NHÃN (TỪ PROBLEM.MD)

### 1. Ranh giới nhãn mơ hồ (Imprecise Span Boundary)
* **Vấn đề:** Tranh chấp ranh giới giữa `health_status` (Trạng thái sức khỏe) và `private_life` (Đời sống riêng tư).
  * Ví dụ: Câu văn phức diễn đạt nguyên nhân - hệ quả: *"Tôi bị bệnh hen phế quản khiến tôi không thể đi làm kiếm sống"* thường bị LLM bọc chung toàn bộ vào nhãn `health_status`.
* **Quy tắc phân định:**
  * `health_status`: Chỉ bao phủ các thông tin mô tả trực tiếp tình trạng bệnh lý, triệu chứng lâm sàng, chẩn đoán y khoa hoặc phác đồ điều trị. (Ví dụ: `"viêm phổi cấp tính"`).
  * `private_life`: Bao phủ các mô tả về hoàn cảnh sống khó khăn, quan hệ gia đình và các tác động tiêu cực gián tiếp của bệnh tật lên đời sống sinh hoạt, công việc. (Ví dụ: `"không thể đi làm kiếm sống"`).
  * **Giải pháp sửa đổi:** Cấu hình kịch bản đồng hiện cả 2 trường và cung cấp ví dụ Few-shot tương phản trong prompt để LLM phân rã ranh giới rõ ràng: `⟦health_status⟧bị hen phế quản⟦/health_status⟧ khiến tôi ⟦private_life⟧không thể đi làm kiếm sống⟦/private_life⟧`.

### 2. Thử thách về Thực thể lồng nhau (Nested Entities) & Nhãn phẳng (Flat NER)
* **Vấn đề:** Trong ngôn ngữ tự nhiên, thông tin định danh thường lồng nhau (Ví dụ: nhãn quan hệ gia đình `"con gái là Nguyễn Thị Lan"` bao chứa nhãn họ tên con `"Nguyễn Thị Lan"`). Tuy nhiên, các kiến trúc học máy nhận diện thực thể (NER) phổ biến lại hoạt động trên cơ chế nhãn phẳng (mỗi từ chỉ thuộc một nhãn).
* **Mâu thuẫn:** Gán nhãn lồng nhau (nested overlap) sẽ gây lỗi phân loại nhãn ở đầu ra và làm sai lệch chỉ số đánh giá F1/Precision/Recall của mô hình.
* **Giải pháp ẩn danh hóa và xử lý ưu tiên:**
  * Áp dụng nguyên lý che phủ gián tiếp: Nếu nhãn cha (`family_relations`) đã được che phủ, thực thể con bên trong đương nhiên được bảo vệ, việc gán nhãn trùng lặp là không cần thiết.
  * Thiết lập bảng phân cấp ưu tiên `PRIORITIES` khi gỡ chồng lấn spans trong code:
    1. Ưu tiên bảo vệ ID cứng (CCCD, SĐT, Email - Trọng số 100).
    2. Ưu tiên dữ liệu nhạy cảm đặc thù (Bệnh lý, án tích, tôn giáo - Trọng số 80).
    3. Ưu tiên PII Họ tên & Địa chỉ (Trọng số 60).
    4. Ưu tiên tên riêng thành phần đứng độc lập (Given Name - Trọng số 50).
    5. Ưu tiên nhãn ngữ cảnh đời tư diện rộng (Private Life - Trọng số 40).
