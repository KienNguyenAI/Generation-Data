# SecurePrep — Pipeline hiện tại (thuần Python, `generate.py`)

> Sơ đồ khớp đúng code trong `Generation-Data/generate.py` (cập nhật 2026-07-02).
> Mở file này bằng VS Code (Preview) để xem Mermaid render.

## 1. Toàn cảnh: từ nguồn → dataset

```mermaid
flowchart TD
  subgraph SRC["Nguồn dữ liệu (Data/ + .env)"]
    P["profile_bank.jsonl<br/>~30k hồ sơ PII/SPI"]
    S["pii_schema.json<br/>34 field + gen_mode"]
    C["scenario_catalog.json<br/>21 kịch bản + supplemental_attributes"]
    E[".env → GEMINI_API"]
  end

  subgraph BATCH["run_batch(N)  —  lớp lô"]
    SEL["Chọn N hồ sơ NGƯỜI LỚN (tuổi ≥18)<br/>× N kịch bản PHÂN BIỆT"]
  end

  subgraph ROW["generate_one()  —  mỗi row 1 lần chạy"]
    B1["① PREPARE · build_manifest<br/>SUBSET field theo kịch bản + REALIZE surface (dob/cccd/phone biến thể) + gán mechanism"]
    B1b["①b ATTRIBUTES · realize_supplemental<br/>org → O · doc_code → distractor O (12 số) · thân nhân → PII mượn hồ sơ khác"]
    B2["② PROMPT · build_prompt<br/>verbatim + supplements + hướng dẫn bọc ⟦thẻ⟧ + quy tắc"]
    B3["③ GENERATE (≤3 lần) · call_gemini → clean_output<br/>(auto-retry 503/500; bỏ ```/«»)"]
    B4["④ EXTRACT anchor-tag<br/>⟦field⟧…⟦/field⟧ → text SẠCH + span field mềm"]
    B5{"VALIDATE<br/>coverage đủ? thẻ cân bằng?"}
    B6["⑤ ANNOTATE 3 lớp (xác định)<br/>→ spans"]
    B7["⑥ EXPORT record {content, spans, meta}"]
  end

  subgraph OUT["Đầu ra (output/)"]
    O1["real_&lt;profile&gt;_&lt;scenario&gt;.json"]
    O2["dataset.jsonl (gộp N row)"]
    V["viewer.html — xem span"]
  end

  P --> SEL
  C --> SEL
  SEL --> B1 --> B1b --> B2 --> B3 --> B4 --> B5
  S -. mechanism/surface .-> B1
  C -. supplemental .-> B1b
  E --> B3
  B5 -- "thiếu value / thẻ hỏng" --> B3
  B5 -- "đạt" --> B6 --> B7 --> O1
  B7 --> O2 --> V
```

## 2. Chi tiết ⑤ ANNOTATE — 3 lớp, xác định, KHÔNG dùng LLM

```mermaid
flowchart LR
  IN["text sạch + manifest + anchor spans"] --> M{"mechanism theo field"}
  M -->|"verbatim<br/>cccd, phone, email, bank, giấy tờ số, full_name, address"| L2["Lớp 1+2: khớp verbatim<br/>NFC + phân biệt hoa/thường + biên từ + nhiều biến thể"]
  M -->|"date · dob"| D["Cần cue 'sinh ngày/ngày sinh'<br/>→ loại ngày ký/ngày làm đơn"]
  M -->|"cue_context<br/>gender, ethnicity, religion, political_view…"| CU["Chỉ gán khi có nhãn dẫn trong CÙNG mệnh đề<br/>(chống 'Không/Kinh' từ phổ biến)"]
  M -->|"name_component<br/>họ, chữ đệm, tên"| NC["Có nhãn dẫn (mang họ/chữ đệm/tên…là) HOẶC chữ ký trần<br/>case-sensitive (tránh 'kiệt quệ')"]
  M -->|"anchor_tag<br/>health, criminal, private, sexual, biometric…"| AN["Span đã lấy từ ⟦…⟧ ở bước ④"]
  L2 --> R
  D --> R
  CU --> R
  NC --> R
  AN --> R
  R["resolve_overlaps<br/>longest-match-first · không chồng lấn"] --> SP["spans cuối (start, end, field, label, via)"]
```

## 3. Ánh xạ code (file: `Generation-Data/generate.py`)

| Bước | Hàm |
|---|---|
| Chọn lô | `run_batch(n)` — lọc `_age`≥18, `DEFAULT_SCENARIOS` |
| ① PREPARE | `build_manifest(profile, scenario)` (+ `render_dob/cccd/phone`) |
| ①b ATTRIBUTES | `realize_supplemental(profile, scenario, pool, seed)` |
| ② PROMPT | `build_prompt(scenario, manifest, supplements)` |
| ③ GENERATE | `call_gemini(prompt)` + `clean_output(t)` |
| ④ EXTRACT | `extract_anchor_tags(tagged, anchor_fields)` |
| VALIDATE | `coverage(clean, manifest)` (+ regen trong `generate_one`) |
| ⑤ ANNOTATE | `annotate(clean, manifest, anchor_spans)` → `match_verbatim` / `match_cue_context` / `match_name_component` / `resolve_overlaps` |
| ⑥ EXPORT | `generate_one(...)` trả record → ghi `real_*.json` + `dataset.jsonl` |

## 4. Nguyên tắc chốt
- **Constraint-First**: code kiểm soát mọi giá trị (verbatim / seed / mượn) → LLM chỉ viết văn xuôi bao quanh. Không để LLM tự bịa PII.
- **Annotate là bước cuối, xác định**: dò chuỗi trong manifest, không hỏi LLM → offset chính xác 100%.
- **1 PASS**: `generate.py` sinh + annotate chuẩn trong một lần. `reannotate.py` chỉ là công cụ bảo trì (re-annotate data cũ khi đổi logic, khỏi tốn API) — KHÔNG phải bước bắt buộc.

## 5. Chạy
```bash
python Generation-Data/generate.py 10     # sinh 10 row → output/dataset.jsonl
python Generation-Data/generate.py 100    # sinh 100 row
```
