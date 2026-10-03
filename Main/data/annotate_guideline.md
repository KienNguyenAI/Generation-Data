# GUIDELINE ĐÁNH SPAN — Pass Re-annotate (SecurePrep)

> **Nguồn luật:** NĐ 356/2025/NĐ-CP — Điều 3 = **PII** (dữ liệu cá nhân cơ bản), Điều 4 = **SPI** (dữ liệu cá nhân nhạy cảm).
> **Suy ra từ:** `Data/pii_schema.json` v2.10 (`hard_cases`, `confusable_catalog`, `annotation_invariants`, `matrix_summary`).
> **Vai trò kép:** (a) văn bản NẠP VÀO PROMPT của LLM re-annotate; (b) quy tắc CODE dùng để đối soát + gỡ chồng lấn.
> **Trạng thái:** BẢN THẢO v0.1 — chờ user duyệt (xem mục **F. Điểm cần chốt**).

---

## A. 7 nguyên tắc chung (áp cho toàn bộ pass)

1. **Chủ thể dữ liệu.** Chỉ đánh PII/SPI của **chủ thể hồ sơ**. PII của **thân nhân** vẫn đánh nhưng gắn `subject=other`. **KHÔNG đánh**: tên cán bộ/người tiếp nhận, tên/địa chỉ **cơ quan**, tổng đài/đường dây nóng, mã biên nhận → nhãn `O`.
2. **Hai nhãn.** Mỗi span có `label ∈ {PII, SPI}` + `field` (tên trường). Giữ đúng format hiện tại của `dataset.jsonl`.
3. **Phẳng, 1 nhãn/ký tự, KHÔNG chồng.** Khi 2 span tranh chấp cùng đoạn → giải theo **bảng ưu tiên mục B**.
4. **Biên = trọn mệnh đề bộc lộ, tự đủ nghĩa.** Không cắt cụt (❌ `"không công khai"` → ✅ `"không công khai xu hướng tính dục của bản thân"`). Không nuốt câu thủ tục/xã giao (*"kính mong quý cơ quan xem xét…"* = `O`).
5. **LLM trả TRÍCH DẪN, CODE sở hữu offset.** LLM trả `{quote, field, label, subject}` với `quote` = chuỗi **verbatim** trong văn bản; code định vị offset (NFC + longest-match-first + no-overlap). **LLM không bao giờ tự tính offset.**
6. **PII định danh cứng do MANIFEST quyết định.** Với ID cứng (cccd, phone, email, dob, giấy tờ số, tên, địa chỉ): sự tồn tại + ranh giới lấy từ manifest deterministic. LLM **không được thêm/bịa** PII không có trong manifest + supplemental-attributes → code loại, ghi `meta.rejected`.
7. **Cùng-bề-mặt-khác-vai-trò = `O`.** Xem **bảng distractor mục D** (mã hồ sơ 12 số, GPLX vs CCCD, "Kinh" trong "kinh tế"…).

---

## B. Bảng ưu tiên khi chồng nhau (flat, 1 nhãn/ký tự)

Xếp theo `matrix_summary`. Khi 2 span chồng, **nhóm cao chiếm ký tự tranh chấp; nhóm thấp chỉ giữ phần DƯ nếu phần đó vẫn tự đủ nghĩa, không thì bỏ.**

| Hạng | Nhóm | Field | Tính chất |
|------|------|-------|-----------|
| **1 (cao nhất)** | **ID cứng** (nguyên tử, đâm xuyên) | cccd, phone, email, passport_number, driver_license, vehicle_plate, tax_code, dob, bank_account(số), social_insurance_no, health_insurance_no, eid_credentials(login), toạ độ GPS, số văn bản (bản án/LLTP/QĐ) | Chuỗi ngắn, chiếm đúng ký tự của nó |
| **2** | **SPI đặc thù** | health_status, criminal_record, biometric, ethnicity, religion, political_view, sexual_orientation | Nhạy cảm bản chất/trực-tiếp-gắn-ngữ-cảnh |
| **3** | **PII tên & địa chỉ** | full_name (+ family/middle/given/alias), address, family_relations, digital_account, marital_status, gender, nationality | Định danh, biên theo manifest |
| **4 (thấp nhất)** | **SPI suy luận ngữ cảnh** | private_life, location_data, behavioral_data | Nhận **phần dư** sau khi nhóm 2–3 chiếm chỗ |

**Ví dụ áp dụng (pf_000007):** đoạn *"…mâu thuẫn nội tâm liên quan đến bản dạng cá nhân, khi mà môi trường làm việc và gia đình vẫn chưa hoàn toàn thấu hiểu về khía cạnh này."*
- Hạng 2 `sexual_orientation` chiếm: **"mâu thuẫn nội tâm liên quan đến bản dạng cá nhân"**
- Hạng 4 `private_life` nhận phần dư: **"môi trường làm việc và gia đình vẫn chưa hoàn toàn thấu hiểu về khía cạnh này"**
→ 2 span liền kề, KHÔNG chồng.

---

## C. Định nghĩa từng field — GẮN / KHÔNG GẮN / BIÊN

### C1. SPI (Điều 4) — TRỌNG TÂM của pass

**`health_status`** — Điều 4·1d · *(user chốt: chỉ tình trạng/bệnh lý THỰC)*
- **GẮN:** triệu chứng (*suy nhược cơ thể, đau thắt ngực, mất ngủ*), chẩn đoán/bệnh (*tăng huyết áp độ 2, tiểu đường type 2, rối loạn lo âu, suy thận mạn*), tiền sử bệnh/phẫu thuật (*tiền sử phẫu thuật tim mạch năm 2010*), tình trạng đặc biệt (*đang mang thai tuần 12, khuyết tật vận động*), **đang điều trị bệnh gì / ở đâu** (*đang điều trị ngoại trú tại BV Đa khoa tỉnh Bình Dương*), khuyết tật/di chứng (*di chứng tai biến mạch máu não*).
- **KHÔNG GẮN:** quy trình hành chính-y tế **không lộ bệnh** (*phác đồ điều trị nội khoa tích cực, tái khám đúng lịch hẹn, đơn thuốc, chế độ theo dõi, quá trình hậu phẫu, nhập/ra viện*); trạng thái tốt chung chung (*sức khỏe ổn định, chỉ số trong ngưỡng an toàn*).
- **BIÊN:** trọn cụm bệnh lý **+ bổ ngữ định danh bệnh** (bệnh viện điều trị, năm, giai đoạn). *"rối loạn lo âu, đang điều trị ngoại trú tại Bệnh viện Đa khoa tỉnh Bình Dương"* = **1 span trọn**. Cụm "sức khỏe không ổn định **do** di chứng tai biến…" → gắn từ "do…".

**`private_life`** — Điều 4·1c · *(user chốt: sàn = hoàn cảnh sống/kinh tế/quan hệ THỰC)*
- **GẮN:** hoàn cảnh gia đình/kinh tế khó khăn, sống một mình/không người thân hỗ trợ, đang ly thân/ly hôn, thu nhập-chi tiêu cá nhân, tranh chấp tài sản/thừa kế, nuôi con một mình, con bệnh hiểm nghèo, thân nhân định cư nước ngoài, **mâu thuẫn nội tâm/gia đình chưa thấu hiểu** (phần không thuộc sexual_orientation).
- **KHÔNG GẮN:** câu thủ tục/xã giao, mô tả chung không về đời tư chủ thể.
- **BIÊN:** trọn mệnh đề bộc lộ, **gồm cả hệ quả**. *"tôi hiện đang sống một mình và không có người thân hỗ trợ kinh tế, dẫn đến hoàn cảnh gia đình vô cùng chật vật"* = **1 span** (không cắt trước "dẫn đến…").

**`sexual_orientation`** — Điều 4·1e
- **GẮN:** xu hướng/đời sống tình dục (*dị tính, đồng tính, song tính*), *"không công khai xu hướng tính dục"*, *"đã xác định lại giới tính"*, mâu thuẫn/trăn trở về **bản dạng cá nhân / bản dạng giới**.
- **BIÊN:** trọn cụm — ✅ *"không công khai xu hướng tính dục của bản thân"* (❌ không cắt còn *"không công khai"*). Thắng `private_life` ở vùng chồng (hạng 2 > 4).

**`criminal_record`** — Điều 4·1g
- **GẮN:** án tích/tiền án/tiền sự, *"không có án tích"*, *"đã xóa án tích theo QĐ số…"*, án treo, đang bị điều tra, tội danh + số bản án. **Số bản án/LLTP/QĐ nằm TRONG cụm criminal** (không tách thành PII riêng).
- **BIÊN:** trọn cụm gồm số hiệu văn bản. *"đã hoàn toàn không có án tích"* = gắn (khai báo tình trạng tư pháp).

**`location_data`** — Điều 4·1h
- **GẮN:** toạ độ GPS, check-in địa điểm + toạ độ, lịch sử di chuyển, vị trí định vị theo thời gian.
- **KHÔNG GẮN / phân biệt:** **KHÁC `address`** (nơi cư trú tĩnh = PII address); địa điểm/địa chỉ cơ quan chung = `O`.
- **BIÊN:** trọn cụm gồm toạ độ. *"check-in xã Nghĩa Hưng, tỉnh Phú Thọ (10.80548, 103.7594)"* = 1 span.

**`behavioral_data`** — Điều 4·1l
- **GẮN:** log truy cập, lịch sử duyệt web/tìm kiếm, hoạt động MXH, IP, thiết bị/hệ điều hành đăng nhập, tần suất dùng app.
- **BIÊN:** trọn cụm hành vi (gồm IP/thời gian nếu có).

**`biometric`** — Điều 4·1đ
- **GẮN:** vân tay, mống mắt, ADN, đặc điểm nhận dạng (*sẹo, nốt ruồi*). **KHÔNG** có "mã sinh trắc số" giả.
- **BIÊN:** trọn cụm liệt kê. *"lấy mẫu vân tay, chụp ảnh chân dung và quét mống mắt"* = 1 span.

**`ethnicity`** — Điều 4·1a · **`religion`** — 1b · **`political_view`** — 1b *(cue-context, ngắn)*
- **GẮN** giá trị **chỉ khi có nhãn/ngữ cảnh dẫn**: dân tộc `Kinh/Tày/Khmer…`; tôn giáo `Công giáo/Phật giáo/Không tôn giáo…`; đảng tịch `Đảng viên/Đoàn viên/Quần chúng…`.
- **KHÔNG GẮN** (→ `O`): *"Kinh"* trong *kinh tế/kinh doanh/Bắc Kinh*; *"đạo"* trong *đạo đức/đào tạo*.
- **BIÊN:** đúng cụm giá trị (không nuốt nhãn "Dân tộc:"). Là SPI đặc thù (hạng 2).

**SPI dạng ID cứng** — biên deterministic, **hạng 1**:
`bank_account` (1k, số TK/thẻ), `social_insurance_no` (1k, BHXH 10 số), `health_insurance_no` (1d, BHYT 10/15), `eid_credentials` (1i, VNeID login; **mật khẩu luôn placeholder `********`**). Phân biệt bộ ba 10 số (MST/BHXH/BHYT) bằng keyword. Lịch sử giao dịch/tín dụng trong `bank_account` là **văn xuôi** → biên trọn cụm.

### C2. PII (Điều 3) — biên do MANIFEST, LLM chỉ xác nhận

- **`full_name` + `family_name` / `middle_name` / `given_name` / `name_alias`** (kh1): tên chủ thể. **Given_name khi LỒNG trong full_name → KHÔNG đánh riêng** (chỉ đánh khi đứng độc lập, vd ô "Tên" / chữ ký). Tên trong "đường Lê Lợi / phường Nguyễn Du" = `address_part`, không phải tên người.
- **`dob`** (kh2): ngày sinh. Phân biệt ngày tiếp nhận/hẹn trả/cấp/ký = `O`; ngày sinh thân nhân = `dob subject=other`.
- **`gender`** (kh3) · **`nationality`** (kh5) · **`marital_status`** (kh8): cue-context.
- **`address`** (kh4): nơi cư trú. Địa chỉ **cơ quan** = `O`. Khác `location_data`.
- **`phone`** (kh7) · **`cccd`** (kh7) · **`passport_number`** · **`driver_license`** · **`vehicle_plate`** · **`email`** (kh10) · **`tax_code`** (kh11): ID cứng, hạng 1. GPLX & CCCD **cùng 12 số** → nhãn theo keyword ("GPLX/bằng lái" vs "CCCD/số định danh").
- **`family_relations`** (kh9): cụm quan hệ (*"con là Phạm Bá Phúc, sinh năm 1978"*). **Tên/SĐT/dob thân nhân bên trong = PII riêng của người khác** → xem **Điểm cần chốt F1**.
- **`digital_account`** (kh10): username/handle MXH-app (KHÁC bank_account).
- **`photo`** (kh6): pipeline văn bản chỉ tham chiếu, hiếm khi có span.

---

## D. Bảng distractor → nhãn `O` (từ `confusable_catalog`)

| Bề mặt giống | Ví dụ | Dấu hiệu là `O` |
|---|---|---|
| cccd | mã hồ sơ/biên nhận 12 số (`725083050310`) | đi cùng "mã hồ sơ/biên nhận"; KHÔNG có "CCCD/số định danh" |
| phone | tổng đài `1900 1080`, SĐT cơ quan | "tổng đài/đường dây nóng/điện thoại cơ quan" |
| dob | ngày tiếp nhận/hẹn trả/cấp/ký | "ngày tiếp nhận/hẹn trả/cấp/ký/văn bản" |
| ethnicity | kinh tế, kinh doanh, Bắc Kinh, Thái Lan | KHÔNG có "dân tộc/đồng bào" |
| religion | đạo đức, đào tạo | KHÔNG có "tôn giáo/theo đạo" |
| marital_status | "phòng cho người độc thân" | không mô tả hôn nhân của chủ thể |
| bank_account | số hợp đồng/hoá đơn/công tơ | chỉ là bank khi có "tài khoản/ngân hàng" |
| full_name | cán bộ tiếp nhận, tên trong tên đường | vai trò "cán bộ/chuyên viên"; sau "đường/phường" |
| address | trụ sở UBND, bộ phận một cửa | "trụ sở/cơ quan" |

*(GPLX 12 số ↔ CCCD 12 số: KHÔNG phải `O` mà là **khác loại PII** — nhãn theo keyword.)*

---

## E. Ví dụ biên đã mổ (dùng làm self-test chống hồi quy)

| Doc | Hiện tại (sai/thiếu) | Sau pass (đúng) |
|---|---|---|
| pf_000006 | 1 span health (*tiền sử phẫu thuật…2010*) | + *suy nhược cơ thể… đau thắt ngực cục bộ*; giữ *tiền sử…2010*; **bỏ** phác đồ/tái khám/theo dõi |
| pf_000000 | private_life cụt tại *"…hỗ trợ kinh tế"* | nới tới *"…dẫn đến hoàn cảnh gia đình vô cùng chật vật"* |
| pf_000007 | sexual_orientation = *"không công khai"* (cụt) | *"không công khai xu hướng tính dục của bản thân"* + tách private_life *"…gia đình chưa thấu hiểu…"* |

---

## F. Điểm cần bạn CHỐT (residual — chưa quyết trong bảng)

- **F1. Tên/SĐT/dob thân nhân nằm trong `family_relations`.** Dữ liệu hiện KHÔNG nhất quán (pf_000004: tên con *nằm trong* span family_relations; tên mẹ lại *tách riêng* full_name). Chọn 1:
  - **(a)** Tách: tên/SĐT thân nhân = span PII riêng (`subject=other`); "con là"/"mẹ là" = cue (không span). *(khuyến nghị — sạch cho NER, khớp `note_pii` của schema)*
  - **(b)** Gộp: cả cụm là 1 span `family_relations`, tên bên trong không tách.
- **F2. Tên bệnh viện/tổ chức trong `health_status`** (vd *"Bệnh viện Đa khoa tỉnh Bình Dương"*): **(a)** nằm TRONG span health_status *(mặc định hiện tại)* hay **(b)** tách thành `O`/org riêng?
- **F3. Định dạng nhãn:** giữ `{field, label}` như `dataset.jsonl` hiện tại, hay xuất **3 trục** (`sensitivity/identifier_type/context_dependency`) như `step_13` của schema? *(khuyến nghị: giữ 2 trục cho đồng bộ, thêm 3 trục sau nếu cần)*
