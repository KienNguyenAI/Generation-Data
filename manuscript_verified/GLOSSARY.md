# BẢNG THUẬT NGỮ THỐNG NHẤT BÀI BÁO KHOA HỌC (ViPII UNIFIED GLOSSARY)

Tài liệu này chuẩn hóa và khóa cứng toàn bộ hệ thống thuật ngữ, ký hiệu toán học và cách gọi xuyên suốt tất cả các phần của bài báo khoa học **ViPII**: *A Decree-13-Compliant Benchmark and Compact Models for Vietnamese PII Detection and Utility-Preserving De-identification*.

Tất cả các mục viết tiếp theo (Mục 1, 2, 3, 4, 5, 6, Abstract và Phụ lục) **bắt buộc phải tuân thủ nghiêm ngặt 100%** cách gọi cố định này.

---

## 1. BẢNG THUẬT NGỮ CỐT LÕI (CORE TERMINOLOGY MAPPING)

| Khái niệm nghiệp vụ | Cách gọi cố định (Authoritative Term) | Định nghĩa & Phạm vi sử dụng | Ký hiệu / Quy chuẩn |
|:---|:---|:---|:---:|
| **Dataset / Hệ thống** | **ViPII** | Tên chuẩn hóa chính thức của bộ benchmark, pipeline và hệ thống nghiên cứu. | `ViPII` |
| **Đơn vị nhãn** | **Character span** | Đơn vị gán nhãn thực thể dựa trên tọa độ Unicode code point 0-indexed $[s_i, e_i)$ trên chuỗi Unicode sau chuẩn hóa NFC. Tuyệt đối không dùng token BIO trong ground-truth. | `span = (s, e, f, l)` |
| **Nhãn pháp lý** | **PII / SPI** | Phân tầng pháp lý nhị phân theo Nghị định 13: `PII` (Dữ liệu cá nhân cơ bản - Điều 2.3 & 3) và `SPI` (Dữ liệu cá nhân nhạy cảm - Điều 2.4 & 4). | $l \in \{\text{PII}, \text{SPI}\}$ |
| **Tác vụ 1** | **Span-level detection and annotation** | Tác vụ mô hình dự đoán chính xác tọa độ ký tự cùng phân loại trường và nhãn pháp lý của thực thể trên văn bản thô. | $g: X_{\text{raw}} \to \hat{\mathcal{Y}}$ |
| **Tác vụ 2** | **Utility-preserving sanitization** | Tác vụ mô hình tạo sinh khử định danh trực tiếp văn bản thô, che phủ hoặc hoán đổi PII/SPI nhưng bảo toàn tối đa ngữ nghĩa và tính khả dụng của văn bản. | $\mathcal{M}: X_{\text{raw}} \to X_{\text{sanitized}}$ |
| **Dữ liệu đầu ra (Tác vụ 2)** | **Sanitized text** | Chuỗi văn bản an toàn thu được sau khi thực hiện khử định danh (qua Tag Masking hoặc Consistent Synthetic Replacement). | $X_{\text{sanitized}}$ |
| **PII chưa được loại bỏ** | **Residual privacy leakage** | Tỷ lệ thực thể PII/SPI ground-truth bị mô hình bỏ sót hoặc khử không triệt để dưới giao thức kiểm toán thực nghiệm. | $\mathcal{L}_{\text{privacy}} = 1 - \text{SanRec}$ |
| **Nội dung phi PII bị xóa** | **Over-redaction** | Hiện tượng mô hình bôi đen hoặc xóa nhầm các nội dung thông tin nghiệp vụ, thủ tục hoặc cú pháp hợp pháp phi PII. | $\mathcal{O}_{\text{redact}} = 1 - \text{RetRec}$ |

---

## 2. HỆ THỐNG TRẠNG THÁI VĂN BẢN VÀ KÝ HIỆU TOÁN HỌC (TEXT STATES & NOTATIONS)

| Ký hiệu | Định nghĩa trạng thái văn bản & Ý nghĩa toán học |
|:---:|:---|
| $X_{\text{tagged}}$ | Bản nháp do LLM sinh ra trong pipeline, còn chứa các thẻ đánh dấu ngữ nghĩa `⟦field⟧...⟦/field⟧`. |
| $X_{\text{clean}}$ | Văn bản tự nhiên sạch sau khi bộ giải thuật Stack Parser LIFO $\mathcal{O}(N)$ bóc tách thẻ và ghi nhận tọa độ ground-truth $\mathcal{Y}^*$. |
| $X_{\text{raw}}$ | Văn bản đầu vào đưa vào các mô hình downstream để phát hiện span hoặc khử định danh ($X_{\text{raw}} \equiv X_{\text{clean}}$ trong quá trình benchmark). |
| $X_{\text{sanitized}}$ | Chuỗi văn bản an toàn đầu ra do mô hình de-identification $\mathcal{M}(X_{\text{raw}})$ sinh ra. |
| $y_i^* = (s_i^*, e_i^*, f_i^*, l_i^*)$ | Bộ tứ thuộc tính span ground-truth (vị trí code point bắt đầu, kết thúc, trường, nhãn pháp lý). |
| $\mathcal{Y}^*$ | Tập hợp toàn bộ các span ground-truth phẳng, không chồng lấn trên một tài liệu ($e_i^* \le s_j^* \quad \forall i < j$). |
| $\hat{\mathcal{Y}}$ | Tập hợp các span do mô hình dự đoán ở Tác vụ 1. |
| $\mathcal{S}_{\text{cand}}$ | Tập hợp các span ứng viên do các cơ chế bóc tách phát hiện trước khi gỡ chồng lấn. |
| $\mathcal{P}(X_{\text{raw}})$ | Tập các đơn vị thông tin nhạy cảm PII/SPI ground-truth có trong văn bản. |
| $\mathcal{U}(X_{\text{raw}})$ | Tập các đơn vị thông tin nghiệp vụ phi PII cần bảo tồn khả dụng. |
| $\text{SanRec}$ | Sanitization Recall (Tỷ lệ thực thể PII/SPI được khử thành công). |
| $\text{SanAtt}$ | Sanitization Attribute Accuracy (Độ chính xác bóc tách theo từng thuộc tính PII/SPI). |
| $\text{RetRec}$ | Retention Recall (Tỷ lệ thông tin nghiệp vụ phi PII được bảo toàn trọn vẹn). |
| $\text{RetAtt}$ | Retention Attribute Accuracy (Độ chính xác giữ nguyên các trường phi PII). |
| $\text{FULL}$ | Tỷ lệ tài liệu hoàn hảo: đạt đồng thời 0% Residual Privacy Leakage và 0% Over-redaction trên toàn tài liệu. |

---

## 3. BỐN CƠ CHẾ GÁN NHÃN GROUND-TRUTH (OPERATIONAL CALIBRATION MECHANISMS)

> **Lưu ý phương pháp luận cốt lõi**: Bốn cơ chế dưới đây là **giải thuật xác định chạy offline trên máy chủ** dùng để kiến tạo ground-truth $\mathcal{Y}^*$ không lệch offset. Chúng **không phải là kiến trúc của mô hình neural** (Qwen SLMs, DeepSeek...) được đánh giá ở Mục 6.

1. **Verbatim Matching (`via: verbatim` - 12 fields)**: Khớp nguyên văn bằng Regex Lookaround trên Unicode code point (`full_name`, `address`, `cccd`, `phone`, `email`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code`, `bank_account`, `social_insurance_no`, `health_insurance_no`).
2. **Cue-Context Disambiguation (`via: cue_context` và `date` - 7 fields)**: Giải trừ đa nghĩa từ đồng âm bằng cửa sổ trượt từ khóa dẫn (lookback $\le 80$ ký tự, chặn ranh giới câu) và nhãn thời gian sinh (`dob`, `gender`, `marital_status`, `nationality`, `ethnicity`, `religion`, `political_view`).
3. **Name-Component Decomposition (`via: name_component` - 3 fields)**: Phân rã thành phần họ tên tiếng Việt (`family_name`, `middle_name`, `given_name`) theo chính sách phân rã rời rạc không chồng lấn.
4. **Semantic Anchor-Tag Parsing (`via: anchor_tag` - 10 fields)**: Bóc tách tọa độ mệnh đề tự sự nhạy cảm dạng mở bằng Stack Parser LIFO $\mathcal{O}(N)$ từ thẻ neo `⟦field⟧...⟦/field⟧` (`name_alias`, `family_relations`, `health_status`, `criminal_record`, `location_data`, `private_life`, `biometric`, `behavioral_data`, `sexual_orientation`, `eid_credentials`).

Hệ thống giải quyết xung đột bằng thuật toán **Anchor-First Greedy Longest-Span Match Resolution** (`resolve_overlaps` trong `core/annotation.py`), đảm bảo tính xác định tuyệt đối và hoàn toàn không chồng lấn.
