# GHI CHÚ QUY TẮC: RANH GIỚI NHÃN MƠ HỒ (IMPRECISE SPAN BOUNDARY)

> **Mục tiêu:** Thống nhất ranh giới gán nhãn giữa hai thực thể nhạy cảm (SPI) là `health_status` (Tình trạng sức khỏe) và `private_life` (Đời sống riêng tư).

---

## 1. Vấn đề phát sinh (Case study)
Trong bản ghi số 1 (`pf_002796`) của kịch bản `sc_health_occup`, văn bản do LLM sinh ra có chứa câu:
> *"...nhưng vẫn còn chịu ảnh hưởng nghiêm trọng của bệnh lý hen phế quản, dùng thuốc cắt cơn khi cần. Tình trạng này khiến tôi thường xuyên khó thở và suy giảm đáng kể khả năng làm việc lâu dài, **gây ảnh hưởng trực tiếp đến sinh hoạt cũng như công việc hàng ngày của tôi**."*

* **Tình trạng gán nhãn ban đầu:** Cả cụm câu văn dài trên bị bọc chung trong thẻ neo của nhãn `health_status`.
* **Vấn đề:** Vế sau (*"gây ảnh hưởng trực tiếp đến sinh hoạt cũng như công việc hàng ngày..."*) phản ánh các tác động tiêu cực lên cuộc sống cá nhân/đời tư, nên mang tính chất của nhãn `private_life` hơn là mô tả y khoa thuần túy của `health_status`.

---

## 2. Quy tắc phân định ranh giới (Span Boundary Rules)

Để tránh hiện tượng loãng nhãn (imprecise span boundary) khi gán nhãn thủ công hoặc khi LLM neo nhãn:

### A. Đối với `health_status` (Tình trạng sức khỏe)
* **Phạm vi bao phủ:** Chỉ bao phủ các thông tin mô tả trực tiếp tình trạng bệnh lý, triệu chứng lâm sàng, chẩn đoán, tiền sử bệnh án, hoặc tên cơ sở/phác đồ đang điều trị thực tế.
  * *Ví dụ đúng:* `"viêm phổi cấp tính"`, `"suy giảm trí nhớ kéo dài"`, `"điều trị ngoại trú tại Bệnh viện Đa khoa tỉnh Bình Dương"`.
* **Ranh giới:** Cắt nhãn ngay khi kết thúc phần triệu chứng/bệnh lý. **Không** kéo dài sang phần mô tả hệ quả đối với sinh hoạt hay công việc.

### B. Đối với `private_life` (Đời sống riêng tư)
* **Phạm vi bao phủ:** Gán nhãn cho các thông tin mô tả hoàn cảnh sống, khó khăn kinh tế, quan hệ hôn nhân/gia đình, các vấn đề đời tư nhạy cảm, **và các tác động/hậu quả tiêu cực do bệnh tật gây ra đối với sinh hoạt và công việc hàng ngày**.
  * *Ví dụ đúng:* `"gây ảnh hưởng trực tiếp đến sinh hoạt cũng như công việc hàng ngày của tôi"`, `"không còn khả năng lao động kiếm sống ổn định để trang trải chi phí sinh hoạt"`.

---

## 3. Thử thách về Thực thể lồng nhau (Overlapping/Nested Entities) và Nhãn phẳng (Flat NER)

### A. Bản chất hiện tượng lồng nhau trong dữ liệu PII/SPI
Trong ngôn ngữ tự nhiên, đặc biệt là văn bản hành chính và đời sống, các thông tin định danh (PII) và nhạy cảm (SPI) thường có xu hướng lồng ghép thứ bậc vào nhau:
- **Quan hệ gia đình (`family_relations`) lồng Họ tên (`full_name`):** Ví dụ: `"cha đẻ là ông Nguyễn Văn Nam"`.
- **Địa chỉ (`address`) lồng Tên địa danh (`location_name`):** Ví dụ: `"phường Xuân Khánh, TP HCM"`.
- **Tài khoản số (`digital_account`) lồng Mã định danh chuyên biệt:** Ví dụ: `"tài khoản VssID 0761838425"` (chứa mã số BHXH).

### B. Giới hạn kỹ thuật của bài toán Nhãn phẳng (Flat NER)
Hầu hết các kiến trúc học máy nhận diện thực thể hiện đại (như BERT-CRF, SpaCy) và các định dạng thẻ gán chuẩn (IOB/BIO tagging) đều hoạt động trên giả định **Nhãn phẳng**: mỗi token chỉ có thể thuộc về duy nhất một thực thể tại một thời điểm. Việc gán hai nhãn chồng lấn (overlap) lên cùng một ký tự sẽ làm phát sinh các lỗi kỹ thuật:
- **Mâu thuẫn toán học ở đầu ra (Label collision):** Tín hiệu xác suất của mô hình phân loại chuỗi chỉ có một chiều chọn nhãn cho mỗi token.
- **Phá vỡ cấu trúc đánh giá:** Làm mất tính chính xác khi tính các độ đo $F_1$, $Precision$, $Recall$ do ranh giới nhập nhằng.

### C. Giải pháp và Ứng dụng thực tế trong ẩn danh dữ liệu (De-identification)
Đối với bài toán thực tế về ẩn danh hóa dữ liệu (De-identification/Redaction):
- **Nguyên lý che phủ gián tiếp (Implicit Redaction):** Nếu cả cụm thông tin cha (ví dụ: `"cha đẻ là ông Nguyễn Văn Nam"`) được che phủ:
  > *"Họ tên của [RED-FAMILY_RELATIONS]"*
  Thì các thông tin định danh con bên trong (`"Nguyễn Văn Nam"`) đã mặc nhiên được bảo vệ. Việc gán nhãn trùng lặp là không cần thiết.
- **Quy tắc phân cấp và xử lý ưu tiên (Boundary Prioritization):**
  Để giải quyết tranh chấp ranh giới phẳng, SecurePrep áp dụng quy tắc phân cấp ưu tiên:
  1. *Nếu ưu tiên bảo vệ ID cứng:* Cắt nhỏ ranh giới của nhãn bao quanh để nhường ký tự cho ID cứng (CCCD, Số điện thoại).
  2. *Nếu ưu tiên cấu trúc thực thể nguyên tử (Ví dụ: Họ tên thân nhân):* Co ranh giới của nhãn quan hệ (`family_relations`) về cụm từ chỉ mối quan hệ (`"cha đẻ là ông"`), và giải phóng phần tên riêng (`"Nguyễn Văn Nam"`) để gán nhãn thành phần độc lập (`family_name`, `middle_name`, `given_name`).
