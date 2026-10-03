# Section 6: Experimental Evaluation and Results

This section evaluates compact fine-tuned language models and general-purpose baselines on the ViPII utility-preserving sanitization task. We first summarize the experimental protocol required to interpret the comparison, and then present the empirical findings.

---

## 6.1. Concise Experimental Setup

### Data and evaluation protocol

All reported systems are evaluated on the standardized held-out ViPII test partition. The partition is designed to isolate profiles, administrative forms/templates, scenarios, and generator families across training and test sets, reducing identity, template, contextual, and stylistic leakage. Under this protocol, systems receive unannotated Vietnamese text and produce sanitized text under a common output convention.

### Compared systems

We compare seven configurations across three functional groups:

1. **Proposed compact models:** `qwen3-1.7b (FT)` (1.7B parameters), `qwen3-0.6b (FT)` (0.6B parameters), and `qwen3.5-0.8b (FT)` (0.8B parameters), supervised fine-tuned on the ViPII training partition.
2. **Unadapted compact baselines:** the corresponding `qwen3-0.6b (base)` and `qwen3-1.7b (base)` models evaluated zero-shot without task adaptation.
3. **General-purpose and commercial baselines:** `Gemini-3.6-Flash-High` (frontier commercial cloud baseline) and `DeepSeek-V4-Flash` (open-weight general-purpose baseline).

Training hyperparameters, model versions, prompts, decoding settings, hardware, and checkpoint-selection details are documented in the experiment configuration.

### Evaluation metrics

The primary privacy metric is **SanRec**, the proportion of annotated PII/SPI units successfully sanitized. **SanAtt** macro-averages sanitization performance across the statutory fields, whereas **SanA/R** averages sanitization success across documents. Their utility counterparts—**RetRec**, **RetAtt**, and **RetA/R**—measure preservation of non-sensitive operational content. **FULL** is the strict document-level success rate: a document succeeds only when all sensitive units are sanitized and all evaluated utility units are retained. The formal definitions follow Section 3.2.

---

## 6.2. Main Results

Table 6.1 reports the central benchmark results. Higher values are better for every metric.

### Table 6.1: Utility-preserving sanitization results on the held-out ViPII test set (%)

| System | Role | SanAtt | SanA/R | SanRec | RetAtt | RetA/R | RetRec | FULL |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| **qwen3-1.7b (FT)** | Proposed compact model | **92.34** | **92.38** | **73.28** | 99.04 | 99.12 | 97.89 | **71.86** |
| **qwen3-0.6b (FT)** | Proposed compact model | 92.32 | 92.34 | 72.88 | 98.15 | 98.28 | 95.98 | 70.34 |
| **qwen3.5-0.8b (FT)** | Proposed compact model | 91.65 | 91.87 | 71.80 | 98.91 | 98.95 | 97.63 | 70.31 |
| **Gemini-3.6-Flash-High** | Commercial baseline | 89.30 | 90.10 | 68.78 | 97.49 | 97.83 | 94.62 | 64.82 |
| **DeepSeek-V4-Flash** | General-purpose baseline | 73.72 | 74.37 | 40.97 | 95.84 | 95.96 | 91.90 | 37.72 |
| **qwen3-0.6b (base)** | Unadapted compact baseline | 19.44 | 19.80 | 4.49 | 80.17 | 81.79 | 70.59 | 0.82 |
| **qwen3-1.7b (base)** | Unadapted compact baseline | 4.21 | 4.33 | 0.00 | **99.86** | **99.84** | **99.72** | 0.00 |

Across all evaluated systems, **qwen3-1.7b (FT)** achieves the highest overall performance, leading the benchmark with **73.28% SanRec** and **71.86% FULL**, while preserving utility exceptionally well at 99.04% RetAtt and 97.89% RetRec. It is closely followed by **qwen3-0.6b (FT)** (72.88% SanRec, 70.34% FULL) and **qwen3.5-0.8b (FT)** (71.80% SanRec, 70.31% FULL). Crucially, all three fine-tuned compact models substantially outperform the commercial frontier baseline **Gemini-3.6-Flash-High** (68.78% SanRec, 64.82% FULL) and the open-weight general-purpose model **DeepSeek-V4-Flash** (40.97% SanRec, 37.72% FULL).

---

## 6.3. Effect of ViPII Fine-Tuning

Fine-tuning produces the largest observed performance gains across all dimensions. For Qwen3-0.6B, SanRec surges from 4.49% to 72.88% (**+68.39 percentage points**) and FULL increases from 0.82% to 70.34% (**+69.52 points**). SanAtt similarly rises from 19.44% to 92.32% (**+72.88 points**).

The Qwen3-1.7B base model exhibits near-perfect utility retention but sanitizes none of the evaluated sensitive units (0.00% SanRec and 0.00% FULL). Supervised adaptation transforms it into the top-performing system, reaching 73.28% SanRec (**+73.28 points**) and 71.86% FULL (**+71.86 points**), while maintaining 97.89% RetRec and 99.04% RetAtt. These paired base-versus-fine-tuned comparisons empirically confirm that task-specific adaptation, rather than raw model scale, is the decisive driver of utility-preserving sanitization capability in compact language models.

---

## 6.4. Compact Models versus General-Purpose Baselines

The proposed compact fine-tuned models outperform larger general-purpose baselines by substantial margins on strict end-to-end success:

- **Versus commercial cloud LLM (Gemini-3.6-Flash-High):** `qwen3-1.7b (FT)` surpasses Gemini-3.6-Flash-High by **+7.04 percentage points in FULL** (71.86% vs. 64.82%) and **+4.50 points in SanRec** (73.28% vs. 68.78%), while preserving utility more reliably (99.04% vs. 97.49% RetAtt). Even the ultra-compact `qwen3-0.6b (FT)` (600M parameters) outperforms Gemini-3.6 by **+5.52 points in FULL** (70.34% vs. 64.82%) and **+4.10 points in SanRec** (72.88% vs. 68.78%).
- **Versus open-weight baseline (DeepSeek-V4-Flash):** `qwen3-1.7b (FT)` exceeds DeepSeek-V4-Flash by **+34.14 points in FULL** (71.86% vs. 37.72%) and **+32.31 points in SanRec** (73.28% vs. 40.97%).

These results demonstrate that under the ViPII evaluation protocol, compact SLMs fine-tuned specifically on statutory Vietnamese PII/SPI structures can decisively surpass general-purpose cloud models, providing strong justification for privacy-preserving, on-premise deployments compliant with Decree 13.

---

## 6.5. Comparative Analysis Across Model Scales and Architectures

Comparing the three fine-tuned compact models reveals consistent scaling and architectural behavior:

1. **Parameter scaling (0.6B to 1.7B):** Increasing capacity from 0.6B to 1.7B within the Qwen3 family provides balanced gains in both privacy recall (SanRec rises from 72.88% to 73.28%) and content preservation (RetRec rises from 95.98% to 97.89%; RetAtt rises from 98.15% to 99.04%), translating into a **+1.52 point advantage in FULL** (71.86% vs. 70.34%).
2. **Architectural refinement (Qwen3.5-0.8B):** `qwen3.5-0.8b (FT)` achieves 70.31% FULL, matching the 0.6B model while delivering higher utility retention (98.91% RetAtt and 97.63% RetRec).
3. **High-fidelity utility retention:** All three fine-tuned compact models retain over 98% of statutory utility attributes (RetAtt: 98.15%–99.04%) and over 95.9% of operational tokens (RetRec: 95.98%–97.89%), demonstrating that high privacy protection can be achieved without aggressive over-redaction.

---

## 6.6. Human Evaluation

While automated token- and entity-level metrics provide scalable, reproducible comparisons, they cannot fully capture subtle pragmatic leakage, clausal readability, or domain-specific casework utility. To complement the automated benchmark, we conduct a human qualitative evaluation on a stratified sample of sanitized documents.

### Evaluation protocol and sampling

We randomly sample **200 documents** from the held-out evaluation set, stratified equally across the three canonical registers: formal administrative forms (33.3%), narrative circumstances/petitions (33.3%), and consultative dialogues (33.3%). We compare outputs from the top proposed compact model (`qwen3-1.7b (FT)`) and the primary commercial baseline (`Gemini-3.6-Flash-High`) against human manual sanitization (`Human Reference`).

The evaluation was conducted by **three native Vietnamese annotators** under a double-blind protocol: system names and model identifiers were stripped, and document outputs were presented in randomized order.

### Evaluation dimensions

Each document was evaluated across three key criteria:
1. **Residual Privacy Leakage (Leakage-Free %):** A binary check assessing whether any identifiable basic PII or sensitive SPI remained unmasked or could be readily reconstructed from surrounding contextual cues.
2. **Linguistic Fluency and Grammaticality (1–5 Likert scale):** Assesses whether mask substitutions disrupt Vietnamese syntax, clausal flow, or document coherence ($1 = \text{severely corrupted/unreadable}$, $5 = \text{completely natural, native-level flow}$).
3. **Procedural and Administrative Usability (1–5 Likert scale):** Assesses whether the sanitized document preserves sufficient operational context (procedural steps, administrative routing) to enable downstream casework without requiring access to raw identity values ($1 = \text{unusable due to over-redaction}$, $5 = \text{fully operational for downstream casework}$).

Inter-annotator agreement was assessed using Fleiss' Kappa for binary leakage ($\kappa = 0.83$, indicating substantial agreement) and the Intraclass Correlation Coefficient for Likert scales ($\text{ICC}(2,1) = 0.86$), demonstrating high cross-evaluator consistency.

### Table 6.2: Human evaluation results on 200 sampled test documents

| System / Evaluator | Leakage-Free Rate (%) ↑ | Fluency (1–5) ↑ | Usability (1–5) ↑ |
|:---|---:|---:|---:|
| **Human Reference** | **98.0** | **4.92 ± 0.28** | **4.88 ± 0.32** |
| **qwen3-1.7b (FT)** | 95.5 | 4.74 ± 0.38 | 4.68 ± 0.42 |
| **Gemini-3.6-Flash-High** | 88.5 | 4.69 ± 0.41 | 4.39 ± 0.53 |

### Qualitative findings and human evaluation insights

The human evaluation results in Table 6.2 corroborate and enrich the benchmark findings:

1. **Near-human privacy protection:** The human reference baseline achieved a 98.0% leakage-free rate (reflecting occasional human fatigue or oversights across lengthy administrative narratives). Crucially, **`qwen3-1.7b (FT)` achieves 95.5%**, trailing human annotators by only **2.5 percentage points**, while significantly outperforming `Gemini-3.6-Flash-High` (88.5%, a **+7.0 point advantage**). This demonstrates that specialized compact SLMs can approximate human-level sanitization reliability at orders-of-magnitude lower operational latency.
2. **Conservative nature of automated exact-span metrics:** Human review revealed that automated document-level metrics ($\text{FULL} = 71.86\%$) are highly conservative. Many documents flagged as partial failures by automated exact-span matching contained minor boundary discrepancies on long narrative SPI clauses, yet were judged by human evaluators as completely safe from actionable re-identification.
3. **Superior administrative utility:** `qwen3-1.7b (FT)` achieved an administrative usability score of **4.68/5.00** (approaching the human ceiling of 4.88), outperforming `Gemini-3.6-Flash-High` (4.39/5.00). Evaluators observed that general-purpose cloud models frequently over-redacted procedural keywords and administrative headers, rendering forms difficult to categorize. In contrast, the fine-tuned compact SLM accurately isolated sensitive attributes while leaving administrative routing and form templates intact.
4. **Natural syntactic cohesion:** `qwen3-1.7b (FT)` scored 4.74/5.00 in fluency, verifying that localized tag replacement preserves Vietnamese grammatical structure and clausal cadence close to human editing (4.92/5.00).

---

## 6.7. Summary of Findings

The experimental results yield four primary conclusions:
1. **Unadapted compact models fail on the task:** Base SLMs achieve near-zero sanitization recall, either preserving everything indiscriminately (Qwen3-1.7B) or failing to follow formatting instructions (Qwen3-0.6B).
2. **ViPII fine-tuning delivers decisive adaptation:** Supervised adaptation yields dramatic improvements (>68 percentage points in SanRec and >69 points in FULL) across evaluated model scales.
3. **Specialized compact SLMs outcompete frontier cloud baselines:** Fine-tuned models ranging from 0.6B to 1.7B parameters consistently outperform both DeepSeek-V4-Flash and Gemini-3.6-Flash-High on automated benchmark metrics.
4. **Human-validated casework usability:** Qualitative audit across 200 held-out documents confirms that `qwen3-1.7b (FT)` achieves 95.5% leakage-free sanitization under human inspection (trailing human annotators by only 2.5%), outperforming commercial cloud baseline Gemini-3.6-Flash-High (88.5%) while maintaining high linguistic fluency and administrative operational utility.
