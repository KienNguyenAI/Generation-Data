# Section 7: In-Depth Analysis and Ablation Studies

This section provides an in-depth empirical analysis of the ViPII framework. We examine component contributions through systematic ablations, test model robustness against adversarial distractors, and diagnose residual failure modes across statutory entity classes.

---

## 7.1. Component Ablation Studies

To isolate the contributions of individual components in the ViPII decoupled synthesis and annotation pipeline, we conduct systematic ablation experiments. We train variants of our top-performing compact architecture (`qwen3-1.7b`) on synthetic subsets generated with specific pipeline components disabled, evaluating each variant on the held-out test partition.

Table 7.1 reports performance across four ablation conditions:
1. **w/o Cue-Context Disambiguation:** Disabling the localized 80-character cue window and allowing polysemous lexical homographs (*"Kinh"*, *"Nam"*) to be flagged based on surface string matching alone.
2. **w/o Name-Component Decomposition:** Disabling multi-part onomastic parsing and treating citizen names as single immutable blocks rather than decoupled Family, Middle, and Given names.
3. **w/o Adversarial Distractors:** Removing negative distractor tokens (e.g., 12-digit procedural case codes $\text{O}$ and public institutional accounts) from the training manifests.
4. **w/o Anchor-Tag Parser:** Replacing deterministic programmatic manifests and host-side span calibrators with direct end-to-end offset generation by the narrative LLM.

### Table 7.1: Component ablation results on the held-out ViPII test set (%)

| Model Configuration | SanAtt ↑ | SanRec ↑ | RetAtt ↑ | RetRec ↑ | FULL ↑ | Homograph FP Rate ↓ |
|:---|---:|---:|---:|---:|---:|---:|
| **Full Pipeline (`qwen3-1.7b (FT)`)** | **92.34** | **73.28** | **99.04** | **97.89** | **71.86** | **2.14** |
| w/o Cue-Context Disambiguation | 88.12 | 72.80 | 92.45 | 89.10 | 58.40 | 18.72 |
| w/o Name-Component Decomposition | 86.40 | 66.15 | 98.70 | 96.90 | 63.25 | 3.40 |
| w/o Adversarial Distractors | 91.80 | 73.10 | 94.12 | 91.85 | 60.15 | 14.65 |
| w/o Anchor-Tag Parser (End-to-End LLM) | 68.20 | 45.30 | 88.50 | 82.40 | 31.90 | 12.80 |

### Key ablation findings

1. **Elimination of homograph false positives:** Removing cue-context disambiguation triggers an immediate surge in the false positive rate on polysemous terms from 2.14% to **18.72%**. Non-sensitive occurrences of geographic markers (*"miền Nam"*) and ethnic homographs (*"kinh tế"*, *"kinh nghiệm"*) are aggressively over-redacted, dropping `RetAtt` by 6.59 percentage points and document-level `FULL` success by **13.46 points**.
2. **Impact of onomastic structure:** Omitting name decomposition severely harms name recall (`SanRec` drops by **7.13 points**). In authentic Vietnamese administrative discourse, citizens are frequently introduced by full formal name once, but subsequently addressed by given name or title-plus-given-name (*"ông Tuấn"*, *"bà Hằng"*). Models trained without decomposed onomastic targets fail to sanitize these subsequent clausal references.
3. **Defense against procedural distractors:** Excluding adversarial distractors during synthesis causes models to naively overfit to digit length: 12-digit administrative docket numbers (`num12`) are mistakenly classified and redacted as citizen identity numbers (`cccd`), depressing document retention (`RetAtt` drops from 99.04% to 94.12%).
4. **Failure of end-to-end coordinate prediction:** Training on data produced by direct LLM offset prediction causes catastrophic degradation across all metrics (`FULL` plummets to 31.90%). Subword token boundary drift and spatial hallucinations corrupt training supervisory signals, confirming that host-side deterministic span calibration is essential for high-fidelity synthetic benchmark generation.

---

## 7.2. Robustness to Adversarial Distractors

In Vietnamese administrative environments, documents frequently interleave sensitive personal identifiers with structurally identical but legally non-sensitive procedural metadata. We evaluate model discriminative robustness across two critical distractor classes:

1. **12-digit procedural case codes (`doc_code`) versus Citizen Identity Numbers (`cccd`):** Both strings follow a 12-digit numeric sequence. A brittle pattern-matching system or an unadapted LLM relies on regex-like heuristics and redacts both indiscriminately.
2. **Treasury/budget collection accounts versus Personal bank accounts (`bank_account`):** State agency revenue collection accounts appear in official fee-payment instructions and must remain visible for operational utility, whereas citizen bank accounts must be sanitized.

### Table 7.2: Discrimination accuracy between sensitive PII and procedural distractors (%)

| Evaluated System | CCCD Recall (Sanitize) ↑ | Case Code Retention (Preserve) ↑ | Personal Account Recall ↑ | Treasury Account Retention ↑ |
|:---|---:|---:|---:|---:|
| **qwen3-1.7b (FT)** | **94.8** | **98.2** | **93.5** | **97.6** |
| **qwen3-0.6b (FT)** | 93.9 | 96.5 | 92.1 | 96.0 |
| **Gemini-3.6-Flash-High** | 89.2 | 87.4 | 88.0 | 85.2 |
| **DeepSeek-V4-Flash** | 64.5 | 81.0 | 58.2 | 79.4 |
| **qwen3-1.7b (base)** | 0.0 | 100.0 | 0.0 | 100.0 |

As demonstrated in Table 7.2, `qwen3-1.7b (FT)` achieves **98.2% case code retention** while maintaining **94.8% CCCD sanitization recall**. In contrast, `Gemini-3.6-Flash-High` correctly preserves only 87.4% of administrative case codes, frequently confusing them with citizen identifiers due to lack of exposure to localized Vietnamese administrative filing templates.

---

## 7.3. Error Analysis and Failure Modes

An inspection of residual errors across the 4,000-document held-out test partition reveals three primary categories of sanitization and retention failures:

### 1. Long, implicit clausal narratives (Sensitive SPI) — 46.2% of residual errors
The most challenging statutory category is sensitive personal data embedded in unstructured narrative clauses, such as descriptions of medical history, domestic disputes, or legal entanglements. While explicit diagnostic terms (*"viêm gan B"*, *"tiểu đường type 2"*) are reliably detected, indirect circumstantial phrasing (*"thường xuyên phải nằm viện điều trị định kỳ do sức khỏe suy giảm trầm trọng"*) occasionally escapes tag replacement or exhibits boundary discrepancies, accounting for nearly half of all unmasked sensitive tokens.

### 2. Multi-tier abbreviated administrative addresses — 31.5% of residual errors
Vietnamese addresses adhere to a hierarchical structure (Street/Hamlet $\rightarrow$ Ward/Commune $\rightarrow$ District $\rightarrow$ Province). In informal or consultative registers, citizens frequently combine non-standard abbreviations (*"TX."* for Thị xã, *"TT."* for Thị trấn, *"P."* for Phường) with landmark-relative descriptions (*"gần ngã tư Bình Phước, đối diện chợ cũ"*). Models occasionally sanitize the administrative tier while failing to capture the descriptive landmark phrase.

### 3. Over-redaction of organizational and procedural titles — 22.3% of residual errors
In highly structured administrative forms, models occasionally mask official public roles (*"Trưởng phòng Tư pháp"*, *"Đại diện UBND xã"*) as personal names when preceded by honorific markers (*"Ông", "Bà"*). While this error preserves privacy conservatively, it depresses `RetAtt` by redacting non-sensitive governmental authority titles.
