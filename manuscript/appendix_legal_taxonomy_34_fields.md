# Appendix A: Exhaustive Statutory Taxonomy of the 34 Fields under Decree No. 13/2023/NĐ-CP

This appendix provides the exhaustive statutory grounding, legal scope, and canonical examples for all **34 field classes** defined in **ViPII**, based on the Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP) of the Socialist Republic of Vietnam.

---

### Table A.1: Comprehensive Statutory Taxonomy of the 34 Field Classes

| STT | Field Identifier ($f$) | Statutory Tier | Decree 13 Basis | Legal Scope & Definition | Primary Operational Mechanism | Canonical Example |
|:---:|:---|:---:|:---|:---|:---:|:---|
| 1 | `cccd` | **Basic PII** | Art. 2.3(e), Art. 3 | 12-digit Citizen Identity Card number issued under MPS algorithm (provincial code, century/gender bit, birth year, random sequence). | Verbatim Matching | `001095012345` |
| 2 | `cmnd` | **Basic PII** | Art. 2.3(e), Art. 3 | Legacy 9-digit National Identity Card number. | Verbatim Matching | `162849201` |
| 3 | `phone` | **Basic PII** | Art. 2.3(g), Art. 3 | Telecommunications subscriber number conforming to Vietnamese carrier prefixes (`03x`, `05x`, `07x`, `08x`, `09x`, `+84`). | Verbatim Matching | `0983123456` |
| 4 | `email` | **Basic PII** | Art. 2.3(g), Art. 3 | Personal RFC 5322 electronic mail address. | Verbatim Matching | `an.nguyen95@gmail.com` |
| 5 | `passport_number` | **Basic PII** | Art. 2.3(e), Art. 3 | Vietnamese passport serial number (1 capital letter followed by 7 digits). | Verbatim Matching | `C9812456` |
| 6 | `driver_license` | **Basic PII** | Art. 2.3(e), Art. 3 | 12-digit national PET driving license number. | Verbatim Matching | `790185002341` |
| 7 | `vehicle_plate` | **Basic PII** | Art. 2.3(h), Art. 3 | Motor vehicle registration plate following provincial administrative series. | Verbatim Matching | `29A-123.45` |
| 8 | `tax_code` | **Basic PII** | Art. 2.3(e), Art. 3 | 10-digit personal tax identification number or 13-digit dependent branch code. | Verbatim Matching | `8012345678` |
| 9 | `address` | **Basic PII** | Art. 2.3(d), Art. 3 | Full 4-tiered administrative residential or domicile address. | Verbatim Matching | `Số 15 ngõ 105 Doãn Kế Thiện, Mai Dịch, Cầu Giấy, Hà Nội` |
| 10 | `full_name` | **Basic PII** | Art. 2.3(a), Art. 3 | Full civil name of a natural person including surname, middle name, and given name. | Verbatim Matching | `Nguyễn Văn Bình` |
| 11 | `digital_account` | **Basic PII** | Art. 2.3(g), Art. 3 | Personal social network handle, OTT user ID, or profile URL (Zalo, Facebook). | Anchor-Tag Parsing (Verbatim for URL) | `zalo.me/0983123456` |
| 12 | `dob` | **Basic PII** | Art. 2.3(b), Art. 3 | Natural person's date of birth or birth year accompanied by temporal birth cues. | Cue-Context Disambiguation | `sinh ngày 12/04/1991` |
| 13 | `gender` | **Basic PII** | Art. 2.3(c), Art. 3 | Binary or declared civil sex/gender (*Nam*, *Nữ*). | Cue-Context Disambiguation | `giới tính: Nam` |
| 14 | `marital_status` | **Basic PII** | Art. 2.3(c), Art. 3 | Civil marital status (*Độc thân*, *Đã kết hôn*, *Ly hôn*). | Cue-Context Disambiguation | `tình trạng: Độc thân` |
| 15 | `nationality` | **Basic PII** | Art. 2.3(c), Art. 3 | Sovereign citizenship status. | Cue-Context Disambiguation | `quốc tịch: Việt Nam` |
| 16 | `family_name` | **Basic PII** | Art. 2.3(a), Art. 3 | Isolated paternal or maternal surname (single or compound: *Nguyễn*, *Trần Đình*). | Name-Component Decomposition | `Nguyễn` |
| 17 | `middle_name` | **Basic PII** | Art. 2.3(a), Art. 3 | Isolated middle name (*Văn*, *Thị*, *Ngọc*). | Name-Component Decomposition | `Văn` |
| 18 | `given_name` | **Basic PII** | Art. 2.3(a), Art. 3 | Primary given name when appearing in standalone form or signature line. | Name-Component Decomposition | `Bình` |
| 19 | `bank_account` | **Sensitive SPI** | Art. 2.4(d), Art. 4 | Domestic bank account number, IBAN, or payment card number. | Verbatim Matching | `0011001234567` |
| 20 | `social_insurance_no`| **Sensitive SPI** | Art. 2.4(d), Art. 4 | 10-digit National Social Insurance book number (VssID). | Verbatim Matching | `7912345678` |
| 21 | `health_insurance_no`| **Sensitive SPI** | Art. 2.4(a), Art. 4 | 10- or 15-character National Health Insurance card identifier. | Verbatim Matching | `GD4797912345678` |
| 22 | `ethnicity` | **Sensitive SPI** | Art. 2.4(c), Art. 4 | Ethnic affiliation spanning the 54 officially recognized ethnic groups of Vietnam. | Cue-Context Disambiguation | `dân tộc: Kinh` |
| 23 | `religion` | **Sensitive SPI** | Art. 2.4(c), Art. 4 | Religious belief, denomination, ordained affiliation (*Phật giáo*, *Công giáo*). | Cue-Context Disambiguation | `tôn giáo: Phật giáo` |
| 24 | `political_view` | **Sensitive SPI** | Art. 2.4(c), Art. 4 | Political views, party membership (*Đảng viên Đảng CSVN*), political history. | Cue-Context Disambiguation | `Đảng viên Đảng CSVN` |
| 25 | `location_data` | **Sensitive SPI** | Art. 2.4(e), Art. 4 | Precise geolocation coordinates, GPS tracking logs, specific real-time check-ins. | Cue-Context Disambiguation | `tọa độ 21.0285° N, 105.8542° E` |
| 26 | `behavioral_data` | **Sensitive SPI** | Art. 2.4(f), Art. 4 | Digital telemetry, IP access logs, browsing logs identifying specific activities. | Cue-Context Disambiguation | `địa chỉ IP 118.70.12.34` |
| 27 | `place_components`| **Sensitive SPI** | Art. 2.4(h), Art. 4 | Granular native place, ancestral origin, or birth provenance when linked to origin. | Cue-Context Disambiguation | `quê quán: Kim Sơn, Ninh Bình` |
| 28 | `health_status` | **Sensitive SPI** | Art. 2.4(a), Art. 4 | Medical history, clinical diagnoses, symptoms, treatments, medications. | Anchor-Tag Parsing | `mắc suy thận mạn giai đoạn 3, đang lọc máu` |
| 29 | `criminal_record` | **Sensitive SPI** | Art. 2.4(g), Art. 4 | Judicial record, prior convictions, administrative sanctions, parole terms. | Anchor-Tag Parsing | `đang chấp hành án treo 24 tháng` |
| 30 | `private_life` | **Sensitive SPI** | Art. 2.4(h), Art. 4 | Narrative disclosures of sensitive domestic hardship, economic distress, or divorce. | Anchor-Tag Parsing | `hiện mẹ đơn thân nuôi 2 con nhỏ, không có việc làm` |
| 31 | `family_relations` | **Sensitive SPI** | Art. 2.4(h), Art. 4 | Declarations of sensitive kinship ties, dependency, and vulnerable relatives. | Anchor-Tag Parsing | `mẹ già 82 tuổi tàn tật cần chăm sóc đặc biệt` |
| 32 | `sexual_orientation`| **Sensitive SPI** | Art. 2.4(a), Art. 4 | Gender identity, sexual orientation, gender reassignment disclosures. | Anchor-Tag Parsing | `chưa công khai xu hướng đồng tính với gia đình` |
| 33 | `biometric` | **Sensitive SPI** | Art. 2.4(b), Art. 4 | Descriptive morphological identifying characteristics, scars, physical markers. | Anchor-Tag Parsing | `sẹo chấm cách 1cm dưới sau đuôi lông mày trái` |
| 34 | `eid_credentials` | **Sensitive SPI** | Art. 2.4(d), Art. 4 | Electronic identification credential status, VNeID Level 2 account details. | Anchor-Tag Parsing | `Tài khoản VNeID Mức 2` |
