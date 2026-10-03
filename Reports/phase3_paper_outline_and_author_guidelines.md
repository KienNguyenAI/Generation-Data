# ĐỀ CƯƠNG CHI TIẾT BÀI BÁO KHOA HỌC (ViPII PAPER PROPOSAL & MASTER OUTLINE)

**Đề tài chính thức (Working Title):**  
**ViPII: A Decree-13-Compliant Benchmark and Compact Models for Vietnamese PII Detection and Utility-Preserving De-identification**

**Mục tiêu xuất bản đề xuất:** Top-tier NLP / Privacy Venue (ACL, EMNLP, NAACL) hoặc Tạp chí quốc tế uy tín (Nature Scientific Reports, IEEE TDSC, PLOS ONE).

---

## TỔNG THỂ KIẾN TRÚC BÀI BÁO (STRUCTURAL OVERVIEW)

```
├── ABSTRACT (Tóm tắt cô đọng: Bối cảnh, Gap, Đóng góp, Kết quả cốt lõi)
├── 1. INTRODUCTION (Bối cảnh thực tiễn, 4 Research Gaps, 4 Đóng góp chuẩn mực)
├── 2. RELATED WORK (4 Nhánh nghiên cứu: PII Systems, Synthetic Privacy, Programmatic/Weak Supervision, Utility Sanitization)
├── 3. TASK DEFINITION, LEGAL TAXONOMY AND OPERATIONAL FRAMEWORK (Định nghĩa bài toán, 34 fields NĐ 13, 4 Cơ chế kỹ thuật)
├── 4. CONSTRAINT-FIRST DATA SYNTHESIS AND ANNOTATION PIPELINE (Kiến trúc v1.1, 2-Stage Prompting, Gán nhãn xác định)
├── 5. DATASET STATISTICS AND QUALITY ANALYSIS (Thống kê quy mô, 2 Bảng + 2 Hình, MATTR, Vendi, Phân bố 34 trường)
├── 6. EXPERIMENTAL SETUP (8 Cấu hình mô hình, Thiết kế Split chống Leakage, Công thức hệ thống Thước đo kép)
├── 7. MAIN RESULTS (Bảng Chân lý thực nghiệm, Đánh giá FT vs Base, SLMs vs Frontier LLMs, Đánh đổi 0.6B vs 1.7B)
├── 8. ABLATION, ROBUSTNESS, ERROR ANALYSIS AND PRACTICAL IMPLICATIONS (Kế hoạch Ablation 6 thành phần, Nhiễu đối kháng, Triển khai on-premise)
├── 9. ETHICS, LIMITATIONS AND REPRODUCIBILITY (Đạo đức dữ liệu nhân tạo, Giới hạn phương ngữ, Cam kết mở mã nguồn & benchmark)
└── 10. CONCLUSION AND FUTURE WORK (Tổng kết đóng góp, Hướng phát triển đa phương thức OCR/Voice)
```

---

## NỘI DUNG CHI TIẾT TỪNG MỤC & HƯỚNG DẪN TÁC GIẢ (DETAILED SECTIONS)

### ABSTRACT (TÓM TẮT BÀI BÁO)
* **Bối cảnh:** Sự gia tăng ứng dụng AI trong xử lý hồ sơ hành chính, tư pháp, y tế tại Việt Nam đặt ra yêu cầu tuân thủ nghiêm ngặt khung pháp lý bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP).
* **Khoảng trống (Gap):** Các công cụ quốc tế (như Presidio, spaCy) và các LLMs toàn cầu gặp nhiều khó khăn trước các định danh có cấu trúc đặc thù và đặc tính ngôn ngữ tiếng Việt; đồng thời thiếu một benchmark chuẩn hóa căn chỉnh theo luật Việt Nam.
* **Đóng góp:** Giới thiệu **ViPII** — bộ benchmark PII/SPI tiếng Việt quy mô lớn được căn chỉnh theo danh mục pháp lý Nghị định 13, xây dựng qua quy trình sinh dữ liệu constraint-first kết hợp thuật toán gán nhãn span ký tự xác định phía máy chủ.
* **Kết quả:** Đánh giá thực nghiệm cho thấy mô hình nhỏ gọn tinh chỉnh `qwen3-0.6b (FT)` (590M tham số) đạt điểm tổng hợp `FULL` **70.10%** và độ thu hồi khử định danh `SanRec` **72.46%**, thể hiện hiệu quả vượt trội so với các baseline mở quy mô lớn (DeepSeek-V4-Flash) và mô hình thương mại (Gemini-3.6-Flash-High) trong khi duy trì tính khả dụng nghiệp vụ trên 98% (`RetAtt` 98.26%).
* **Ý nghĩa:** Cung cấp giải pháp khả thi cho bài toán khử định danh tại chỗ (on-premise) với chi phí phần cứng thấp, hỗ trợ tuân thủ quy định bảo vệ dữ liệu nội địa.

---

### MỤC 1: INTRODUCTION (ĐẶT VẤN ĐỀ & ĐÓNG GÓP CỐT LÕI)

* **1.1. Motivation & Practical Urgency (Bối cảnh thực tiễn):**
  * Sự bùng nổ ứng dụng AI trong văn bản hành chính, tư pháp, y tế, ngân hàng tại Việt Nam.
  * Nghị định 13/2023/NĐ-CP (PDPD) và Dự thảo Nghị định 356/2025 quy định trách nhiệm pháp lý và chế tài xử phạt nghiêm ngặt đối với hành vi để lộ dữ liệu cá nhân.
* **1.2. The Four Critical Research Gaps (Bốn khoảng trống nghiên cứu):**
  * *Gap 1 (Regulatory Mismatch):* Sự không tương thích giữa các công cụ quốc tế (theo chuẩn GDPR/HIPAA) với hệ thống phân loại pháp lý của Việt Nam (phân tầng rõ PII cơ bản Điều 2.3 và SPI nhạy cảm Điều 2.4).
  * *Gap 2 (Vietnamese Administrative & Linguistic Specifics):* Các định danh có quy tắc logic cấp số (CCCD 12 số mã hóa tỉnh/thế kỷ/năm sinh, CMND 9 số, BHXH, MST), địa chỉ phân rã 4 cấp hành chính, cấu trúc Họ-Đệm-Tên đa thành phần và hiện tượng từ đồng âm gây dương tính giả (*Kinh, Nam*).
  * *Gap 3 (Empirical Limitation of Frontier LLMs on Local PII):* Bằng chứng thực nghiệm từ benchmark cho thấy các LLMs mã nguồn mở và thương mại đa năng bỏ sót tỷ lệ lớn thực thể PII/SPI tiếng Việt (DeepSeek-V4-Flash bỏ sót gần 60% PII; các base model zero-shot đạt điểm FULL < 1%).
  * *Gap 4 (On-Premise Compliance Dilemma):* Nguy cơ pháp lý khi gửi dữ liệu thô sang API đám mây nước ngoài (Điều 25 NĐ 13 về chuyển dữ liệu ra nước ngoài), tạo ra nhu cầu cấp thiết về các mô hình nhỏ gọn (Compact SLMs) có thể chạy on-premise an toàn với chi phí tối thiểu.
* **1.3. The ViPII Framework & Core Contributions (Văn phong học thuật chuẩn mực, thận trọng):**
  1. *Đóng góp 1:* Một benchmark PII/SPI tiếng Việt quy mô lớn được căn chỉnh chặt chẽ với taxonomy pháp lý của Nghị định 13/2023/NĐ-CP (bao gồm 34 trường dữ liệu).
  2. *Đóng góp 2:* Một pipeline sinh dữ liệu constraint-first kết hợp giải thuật gán nhãn character-span xác định phía máy chủ, triệt tiêu sai lệch tọa độ ký tự.
  3. *Đóng góp 3:* Một framework đánh giá toàn diện đo lường đồng thời hai chiều đối xứng: Hiệu quả khử định danh (Privacy Sanitization) và Mức độ bảo toàn tính khả dụng (Utility Retention).
  4. *Đóng góp 4:* Nghiên cứu thực nghiệm chứng minh tính khả thi và hiệu năng vượt trội của các mô hình ngôn ngữ nhỏ gọn (Compact SLMs: 0.6B và 1.7B tham số) trong kịch bản triển khai on-premise.

---

### MỤC 2: RELATED WORK (TỔNG QUAN NGHIÊN CỨU & KHUNG SO SÁNH)

* **2.1. Automated PII Detection & De-identification Systems:**
  * Các hệ thống PII công nghiệp tiêu biểu: Microsoft Presidio, Philter, Google Cloud DLP, Amnesia.
  * *Hạn chế:* Thiết kế theo HIPAA (Mỹ) hoặc GDPR (EU); thiếu vắng taxonomy và cơ chế phân giải cho các thực thể hành chính/pháp lý Việt Nam.
* **2.2. Synthetic Data for Privacy Research & The PRIVASIS Paradigm:**
  * Các nghiên cứu sinh dữ liệu tổng hợp quy mô lớn: PRIVASIS (Li et al., 2026), TABNER nhằm giải quyết "cơn hạn hán dữ liệu" (Data Drought) mà không làm lộ dữ liệu người thật.
  * *Điểm mới của ViPII:* Kế thừa phương pháp sinh tổng hợp có kiểm soát (profile-guided synthesis) nhưng lần đầu tiên đưa vào các ràng buộc định danh hành chính địa phương và khung pháp lý quốc gia.
* **2.3. Programmatic Labeling, Weak Supervision & Synthetic NER Construction:**
  * Điểm qua các hướng tiếp cận gán nhãn tự động: Snorkel, weak supervision, synthetic entity extraction và các tài nguyên NER tiếng Việt trước đây (VLSP, PhoBERT-NER).
  * *So sánh phân định:* Chỉ ra sự khác biệt cốt lõi: NER truyền thống chỉ gán nhãn thực thể tên riêng tĩnh trên tin tức báo chí, trong khi ViPII giải quyết bài toán PII/SPI phức tạp với các mã số định danh có thuật toán kiểm tra và các mệnh đề nhạy cảm tự sự dạng dài.
* **2.4. Utility-Preserving Text Sanitization & Compact On-Premise Models:**
  * Xu hướng chuyển dịch từ "bôi đen thô bạo" (hard redaction) sang khử định danh bảo toàn khả dụng cho downstream tasks.
  * Phân tích rủi ro rò rỉ của LLM đám mây (Shao et al., 2024; Zhou et al., 2025) và tính tất yếu của Compact SLMs (0.6B / 1.7B) chạy on-premise phục vụ data minimization.

---

### MỤC 3: TASK DEFINITION, LEGAL TAXONOMY AND OPERATIONAL FRAMEWORK

* **3.1. Formal Task Formulation (Định nghĩa bài toán chuẩn mực):**
  * *Đầu vào:* Văn bản tiếng Việt tự nhiên $X_{\text{raw}} = (c_1, c_2, \dots, c_N)$ chứa các thông tin cá nhân thuộc tập thực thể $\mathcal{E}$.
  * *Hai chế độ nhiệm vụ (Two Task Modes):*
    1. *Span-Level Detection & Annotation:* Dự đoán tập hợp các nhãn thực thể phẳng $\mathcal{S} = \{(s_i, e_i, f_i, l_i)\}_{i=1}^M$, trong đó $s_i, e_i$ là vị trí ký tự bắt đầu/kết thúc, $f_i \in \mathcal{F}$ (trong 34 trường), $l_i \in \{\text{PII}, \text{SPI}\}$.
    2. *End-to-End Utility-Preserving Sanitization:* Sinh văn bản an toàn $X_{\text{sanitized}} = \mathcal{M}(X_{\text{raw}})$ trong đó các span PII/SPI được thay thế bằng thẻ định danh (Tag Masking: `[HỌ_TÊN]`, `[CCCD]`) hoặc hoán đổi giá trị nhân tạo nhất quán (Synthetic Replacement).
  * *Tiêu chuẩn Đánh giá Kép:*
    - *Khử đúng (Sanitization Correctness):* Triệt tiêu toàn bộ thông tin nhạy cảm ($100\% - \text{Leakage}$).
    - *Bảo toàn Khả dụng (Utility Preservation):* Giữ nguyên trọn vẹn cú pháp, ngữ nghĩa và các trường thông tin nghiệp vụ phi PII.
* **3.2. Legal Taxonomy (Căn cứ Nghị định 13/2023/NĐ-CP — 34 Fields):**
  * *Dữ liệu cá nhân cơ bản (PII - Điều 2.3 & Điều 3 - 18 trường):* `full_name`, `family_name`, `middle_name`, `given_name`, `name_alias`, `dob`, `gender`, `address`, `nationality`, `phone`, `cccd`, `cmnd`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code`, `marital_status`, `digital_account`.
  * *Dữ liệu cá nhân nhạy cảm (SPI - Điều 2.4 & Điều 4 - 16 trường):* `health_status`, `criminal_record`, `private_life`, `sexual_orientation`, `biometric`, `political_view`, `religion`, `ethnicity`, `bank_account`, `social_insurance_no`, `health_insurance_no`, `eid_credentials`, `location_data`, `behavioral_data`, `family_relations`, `place_components`.
* **3.3. Technical Operational Mechanisms (4 Cơ chế Vận hành Kỹ thuật):**
  * *1. Verbatim Matching (`via: verbatim`):* Khớp mẫu chính xác biên từ (Regex Lookaround) cho các định danh chuẩn hóa có cấu trúc hoặc thuật toán sinh.
  * *2. Cue-Context Disambiguation (`via: cue_context`):* Quét cửa sổ trượt (Sliding window 80 ký tự) để triệt tiêu dương tính giả cho các từ đồng âm/từ ngữ thông thường (*"Kinh"*, *"Nam"*).
  * *3. Name-Component Decomposition (`via: name_component`):* Bóc tách Họ, Đệm, Tên riêng tiếng Việt bằng giải thuật phân rã tên.
  * *4. Semantic Anchor-Tag Parsing (`via: anchor_tag`):* Thuật toán LIFO Stack Parser $\mathcal{O}(N)$ giải mã thẻ neo cho các mệnh đề tự sự dài/mở.

---

### MỤC 4: CONSTRAINT-FIRST DATA SYNTHESIS AND ANNOTATION PIPELINE

* **4.1. Nguyên lý Sinh có Ràng buộc (Constraint-First Principle):**
  * Các giá trị định danh được ấn định trước trong Manifest bằng mã nguồn. LLM chỉ đóng vai trò người kể chuyện tự nhiên bao quanh các giá trị đã định sẵn, ngăn chặn hoàn toàn hiện tượng bịa thực thể định danh mới.
* **4.2. Khung Dữ liệu Nền tảng (Foundational Data Assets):**
  * *Synthetic Profile Bank:* Khởi tạo thực thể nhân tạo không chứa dữ liệu công dân thật, tuân thủ thuật toán định danh (CCCD 12 số, GPLX) và kiểm định $k$-anonymity.  
    *(Lưu ý: Quá trình sinh chi tiết từng trường nhân khẩu học chỉ tóm lược trong 1 đoạn ngắn ở bài báo chính; toàn bộ phân phối xác suất và code được đưa vào Phụ lục/Appendix).*
  * *Situational Contexts & Registers:* Định hướng văn bản theo các bối cảnh tình huống thực tế (hành chính, tư vấn dịch vụ, đối thoại y tế, tường trình hoàn cảnh) nhằm kích hoạt động cơ bộc lộ thông tin nhạy cảm tự nhiên.
  * *Form Reference Metadata:* Tích hợp thông tin thủ tục dịch vụ công thực tế dưới dạng **Metadata đối soát** đính kèm bản ghi, không nhồi thô vào prompt LLM.
* **4.3. Ràng buộc trường & Nhiễu Đối kháng (Manifest & Adversarial Distractors):**
  * Sinh mã văn bản/mã hồ sơ 12 số (`doc_code` kiểu `num12` nhãn O) làm bẫy phân biệt ngữ cảnh với CCCD 12 số.
  * Nhúng PII thân nhân đa chủ thể (`subject: other`).
  * Cơ chế loại trừ án tích sạch và thông tin tôn giáo/chính trị mặc định trong văn phong đời thường.
* **4.4. Two-Stage Contextual Prompting:**
  * Stage 1: Dàn ý cấu trúc (Outline Prompting).
  * Stage 2: Bản nháp văn xuôi phong cách PRIVASIS (Draft Prompting).
  * Stage 2b: Hiệu đính cú pháp thẻ neo ở nhiệt độ thấp ($T=0.20$).
* **4.5. Deterministic Ground-Truth Annotation & Overlap Resolution:**
  * Tọa độ ký tự được tính toán 100% bằng giải thuật máy chủ (Regex Lookaround + Cue Windowing + Stack Parser LIFO $\mathcal{O}(N)$), không để LLM đoán offset.
  * Bộ gỡ chồng lấn `resolve_overlaps` theo Bảng ưu tiên PRIORITIES 5 bậc: ID Cứng (100) > SPI Đặc thù (80) > PII Tên & Địa chỉ (60) > Tên riêng (50) > SPI Diện rộng (40).
  * Quy tắc nới lỏng độ phủ họ tên (`Relaxed Full Name Coverage`).

---

### MỤC 5: DATASET STATISTICS AND QUALITY ANALYSIS

* **5.1. Thống kê Quy mô Tổng thể & Chất lượng Toàn diện (Table 1):**
  * Tổng số tài liệu (**47.881** văn bản) và tổng số thực thể (**474.874** spans).
  * Phân bổ giữa PII cơ bản (~63%) và SPI nhạy cảm (~37%).
  * Độ dài văn bản trung bình (~280 từ) và dung lượng từ vựng (Vocabulary size).
  * Chỉ số đa dạng từ vựng **`MATTR`** (~0.81–0.83) và đa dạng ngữ nghĩa **`Vendi Score`**.
  * Chỉ số toàn vẹn kỹ thuật: Tỷ lệ nhúng Manifest (`Coverage > 98.5%`), Tỷ lệ thẻ hợp lệ (`Tag OK > 99.2%`), Tỷ lệ giải quyết chồng lấn (`Overlap Resolution = 100%`).
* **5.2. Phân bố Chi tiết 34 Trường Dữ liệu (Table 2 & Figure 1):**
  * Bảng thống kê 34 trường: Căn cứ pháp lý, Cơ chế kỹ thuật, Số lượng span, Tỷ lệ %, và Độ dài ký tự trung bình.
  * Phân tích sự tương phản độ dài: PII cứng (10–16 ký tự) so với SPI tự sự (`health_status`: ~58 ký tự, `private_life`: ~72 ký tự).
  * Biểu đồ Figure 1 (Horizontal Bar Chart): Mã màu trực quan phân biệt 18 trường PII (xanh dương) và 16 trường SPI (đỏ/cam).
* **5.3. Đa dạng hóa Văn phong & Phân phối Độ dài (Figure 2):**
  * Figure 2(a) (Donut chart): Tỷ lệ các thể loại văn phong (Hành chính 45%, Tường trình tự sự 30%, Đối thoại 15%, Biên bản 10%).
  * Figure 2(b) (Histogram): Phân phối chuẩn độ dài tài liệu (100–600 từ), chứng minh tính hoàn chỉnh của ngữ cảnh.

---

### MỤC 6: EXPERIMENTAL SETUP (THIẾT LẬP THỰC NGHIỆM)

* **6.1. Thiết kế Phân chia Dữ liệu Chống Leakage (Data Split Design):**
  * Phân chia tập Train / Validation / Test đảm bảo các nguyên tắc cô lập nghiêm ngặt:
    - *Profile Disjoint:* Tuyệt đối không trùng lặp nhân vật giữa tập huấn luyện và kiểm thử.
    - *Form/Template Disjoint:* Các mẫu thủ tục hành chính ở tập Test hoàn toàn chưa từng xuất hiện trong Train.
    - *Scenario Disjoint:* Cô lập bối cảnh tình huống thử nghiệm.
    - *Generator Isolation:* Tách biệt mô hình sinh dữ liệu huấn luyện và mô hình kiểm thử để triệt tiêu hiện tượng rò rỉ phong cách (*Generator-Style Leakage*).
* **6.2. Hệ thống 8 Cấu hình Mô hình Đánh giá:**
  * *Proposed SLMs:* `qwen3-0.6b (FT)`, `qwen3-1.7b (FT)`.
  * *Zero-Shot Base SLMs:* `qwen3-0.6b (base)`, `qwen3-1.7b (base)`.
  * *Frontier / Industry Baselines:* `DeepSeek-V4-Flash`, `Gemini-3.6-Flash-High`, `GLM-5.1-Flash (Teacher Pipeline)`.
  * *Control Floor:* `Không xử lý (Untouched raw text)`.
* **6.3. Định nghĩa Toán học Hệ thống Thước đo Kép (Dual Metric Suite):**
  * Cung cấp công thức toán học tường minh, đơn vị tính (span-level, attribute-level, record-level), macro/micro averaging và cách xử lý partial match:
    - $\text{SanAtt}$: Tỷ lệ chính xác thuộc tính PII bị khử.
    - $\text{SanA/R}$: Tỷ lệ thuộc tính PII bị bóc tách trung bình trên mỗi bản ghi.
    - $\text{SanRec}$ (Chỉ số sinh tử): Tỷ lệ PII thực tế được loại bỏ hoàn toàn ($100\% - \text{SanRec} = \text{Tỷ lệ rò rỉ}$).
    - $\text{RetAtt}$, $\text{RetA/R}$, $\text{RetRec}$: Các chỉ số bảo toàn thông tin phi PII, đo lường nguy cơ bôi đen nhầm (*Over-redaction*).
    - $\text{FULL}$: Tỷ lệ tài liệu hoàn hảo song hành cả hai chiều Sanitization và Retention.
* **6.4. Chi tiết Huấn luyện (Training Protocol & Hyperparameters):**
  * Môi trường phần cứng, hyperparameters (learning rate, batch size, optimizer, epochs, scheduler), phương pháp tinh chỉnh (LoRA/Full-FT).

---

### MỤC 7: MAIN RESULTS (KẾT QUẢ THỰC NGHIỆM CHÂN LÝ)

* **7.1. Bảng Chân lý Số liệu Thực nghiệm (Main Benchmark Table):**

| STT | Mô hình (Model) | Phân loại | SanAtt (%) | SanA/R (%) | SanRec (%) | RetAtt (%) | RetA/R (%) | RetRec (%) | FULL (%) |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **GLM-5.1-Flash (Pipeline)** | *Teacher Pipeline* | 96.15 | 96.04 | 85.03 | 98.63 | 98.80 | 97.02 | **82.64** |
| 2 | **qwen3-0.6b (FT)** | **Proposed SLM** | **92.17** | **92.10** | **72.46** | **98.26** | **98.38** | **96.20** | **70.10** |
| 3 | **qwen3-1.7b (FT)** | **Proposed SLM** | **90.61** | **90.84** | **68.88** | **99.23** | **99.34** | **98.31** | **67.90** |
| 4 | **Gemini-3.6-Flash-High** | *Commercial Frontier* | 89.30 | 90.10 | 68.78 | 97.49 | 97.83 | 94.62 | **64.82** |
| 5 | **DeepSeek-V4-Flash** | *Open-Weight Baseline* | 73.72 | 74.37 | 40.97 | 95.84 | 95.96 | 91.90 | **37.72** |
| 6 | **qwen3-0.6b (base)** | *Zero-shot Base* | 19.44 | 19.80 | 4.49 | 80.17 | 81.79 | 70.59 | **0.82** |
| 7 | **qwen3-1.7b (base)** | *Zero-shot Base* | 4.21 | 4.33 | 0.00 | 99.86 | 99.84 | 99.72 | **0.00** |
| 8 | **Không xử lý** | *Control Floor* | 1.16 | 1.22 | 0.00 | 99.19 | 99.28 | 98.26 | **0.00** |

* **7.2. Phân tích Bước nhảy vọt nhờ Tinh chỉnh (FT vs. Base):**
  * `qwen3-0.6b (base)` bất lực trước dữ liệu tiếng Việt (`SanRec` 4.49%, `FULL` 0.82%).
  * `qwen3-0.6b (FT)` tạo bước chuyển biến lớn: `SanAtt` đạt **92.17%**, `SanRec` đạt **72.46%**, `FULL` đạt **70.10%**.
* **7.3. Hiệu năng Compact SLMs so với Frontier LLMs:**
  * `qwen3-0.6b (FT)` vượt `DeepSeek-V4-Flash` (+32.38 pp điểm FULL).
  * `qwen3-0.6b (FT)` vượt cả `Gemini-3.6-Flash-High` (+5.28 pp điểm FULL).
* **7.4. Đánh đổi quy mô 0.6B vs 1.7B:**
  * 0.6B nhạy hơn trong phát hiện PII (`SanRec` 72.46% vs 68.88%).
  * 1.7B thể hiện khả năng duy trì ngữ nghĩa phi PII tốt hơn (`RetAtt` 99.23% và `RetRec` 98.31%).

---

### MỤC 8: ABLATION, ROBUSTNESS, ERROR ANALYSIS AND PRACTICAL IMPLICATIONS

* **8.1. Kế hoạch Thử nghiệm Triệt tiêu (Ablation Study Plan):**
  * Đánh giá vai trò độc lập của từng thành phần kỹ thuật trong pipeline:
    1. *Bỏ Cue-Context Disambiguation:* Đo lường mức độ gia tăng của lỗi dương tính giả trên các từ đồng âm (*"Kinh"*, *"Nam"*).
    2. *Bỏ Adversarial Distractors:* Đo độ sụt giảm độ chính xác khi gặp số văn bản 12 số trong thực tế.
    3. *Bỏ Anchor-Tag Revision:* Đánh giá tỷ lệ lỗi cú pháp thẻ và lệch offset khi không có bước hiệu đính ở $T=0.20$.
    4. *Bỏ Name Decomposition:* So sánh hiệu năng khi coi Họ tên là một khối đơn nhất so với khi phân rã Họ - Đệm - Tên.
    5. *Bỏ Overlap Priority Lattice:* Đo lường tỷ lệ va chạm nhãn khi chỉ dùng heuristic chọn span dài nhất (longest-match).
    6. *One-stage vs. Two-stage Prompting:* Đánh giá độ phủ manifest và tính tự nhiên của văn bản giữa sinh trực tiếp và sinh qua dàn ý.
* **8.2. Khả năng chống chịu Nhiễu Đối kháng (Robustness against Distractors):**
  * Đánh giá năng lực phân biệt giữa CCCD 12 số và mã hồ sơ/văn bản 12 số (`doc_code` kiểu `num12` nhãn O).
* **8.3. Phân tích Lỗi & Các ca Thất bại (Error Analysis & Failure Modes):**
  * Phân loại các trường hợp rò rỉ còn lại: Các mệnh đề tự sự hoàn cảnh gia đình phức tạp hoặc địa chỉ viết tắt nhiều cấp.
* **8.4. Hiệu quả Tính toán & Triển khai On-Premise (Efficiency & Local Deployment):**
  * Đo lường thời gian suy luận (Latency - ms/văn bản), thông lượng (Tokens/sec), và dung lượng bộ nhớ (VRAM < 2GB / RAM).
  * Khẳng định tính khả thi khi chạy trực tiếp trên CPU/GPU văn phòng thông thường.
* **8.5. Ý nghĩa Thực tiễn & Khuyến nghị Chính sách (Practical Implications):**
  * Khuyến nghị kỹ thuật cho việc xây dựng cổng làm sạch dữ liệu (Sanitization Gateway) nội bộ cho các cơ quan hành chính công và bệnh viện.

---

### MỤC 9: ETHICAL CONSIDERATIONS, LIMITATIONS AND REPRODUCIBILITY

* **9.1. Đạo đức Nghiên cứu & Quản trị Rủi ro (Ethical Considerations):**
  * Khẳng định 100% dữ liệu là nhân tạo, không sử dụng hồ sơ thật của bất kỳ công dân nào; tuân thủ Điều 8 Nghị định 13.
  * Phân tích rủi ro lưỡng dụng (Dual-use risk) và các giải pháp kiểm soát an toàn.
* **9.2. Giới hạn Nghiên cứu (Limitations):**
  * Dữ liệu tập trung vào văn bản hành chính, tư pháp, y tế, đời sống; chưa bao quát sâu tiếng lóng và teencode mạng xã hội phức tạp.
* **9.3. Cam kết Tái lập & Khoa học Mở (Reproducibility & Artifact Release):**
  * Công bố mã nguồn Pipeline sinh dữ liệu và giải thuật gán nhãn xác định.
  * Phát hành tập Test Benchmark và checkpoint mô hình `qwen3-0.6b (FT)` trên Hugging Face / GitHub phục vụ cộng đồng nghiên cứu.

---

### MỤC 10: CONCLUSION AND FUTURE WORK

* **10.1. Kết luận:** Tổng kết các đóng góp: Benchmark chuẩn Nghị định 13 đầu tiên, Pipeline sinh có kiểm soát, và minh chứng rằng mô hình nhỏ tinh chỉnh chuyên biệt vượt trội mô hình biên giới lớn trong bài toán PII bản địa.
* **10.2. Hướng phát triển:** Mở rộng bài toán sang dữ liệu đa phương thức (OCR nhận dạng giấy tờ tùy thân quét, giọng nói đối thoại một cửa).

---

*Tài liệu này là bản đề cương chính thức, đầy đủ và chuẩn xác nhất để bắt đầu viết chi tiết bản thảo bài báo khoa học ViPII.*
