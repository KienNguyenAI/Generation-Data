# Section 6: Experimental Evaluation and Results

This section evaluates compact fine-tuned language models and general-purpose baselines on the ViPII utility-preserving sanitization task. We first summarize only the experimental information required to interpret the comparison, and then focus on the main empirical findings.

---

## 6.1. Concise Experimental Setup

### Data and evaluation protocol

ViPII contains 47,881 documents and 474,874 annotated character spans. The corpus is partitioned into 37,548 training documents, 4,788 validation documents, and 5,545 test documents. The split is designed to isolate profiles, administrative forms/templates, scenarios, and generator families across partitions, reducing identity, template, contextual, and stylistic leakage. All reported systems are evaluated on the same held-out test set.

### Compared systems

We compare eight configurations in four functional groups:

1. **Proposed compact models:** `qwen3-0.6b (FT)` and `qwen3-1.7b (FT)`, supervised fine-tuned on the ViPII training partition.
2. **Unadapted compact baselines:** the corresponding `qwen3-0.6b (base)` and `qwen3-1.7b (base)` models evaluated without ViPII fine-tuning.
3. **General-purpose and reference systems:** `DeepSeek-V4-Flash`, `Gemini-3.6-Flash-High`, and `GLM-5.1-Flash (Pipeline)`. GLM is treated as a reference teacher pipeline rather than a directly comparable compact deployment model.
4. **Control condition:** untouched raw text, representing maximum content retention without privacy sanitization.

All systems receive unannotated Vietnamese text and produce sanitized text under a common output convention. Training hyperparameters, model versions, prompts, decoding settings, hardware, and checkpoint-selection details will be provided in the reproducibility appendix and released experiment configuration.

### Evaluation metrics

The primary privacy metric is **SanRec**, the proportion of annotated PII/SPI units successfully sanitized. **SanAtt** macro-averages sanitization performance across the 34 fields, whereas **SanA/R** averages sanitization success across documents. Their utility counterparts—**RetRec**, **RetAtt**, and **RetA/R**—measure preservation of non-sensitive operational content. **FULL** is the strict document-level success rate: a document succeeds only when all sensitive units are sanitized and all evaluated utility units are retained. The formal definitions follow Section 3.2; implementation-level matching and aggregation rules are included with the evaluator release.

---

## 6.2. Main Results

Table 6.1 reports the central benchmark results. Higher values are better for every metric.

### Table 6.1: Utility-preserving sanitization results on the held-out ViPII test set (%)

| System | Role | SanAtt | SanA/R | SanRec | RetAtt | RetA/R | RetRec | FULL |
|:---|:---|---:|---:|---:|---:|---:|---:|---:|
| **GLM-5.1-Flash (Pipeline)** | Reference teacher | **96.15** | **96.04** | **85.03** | 98.63 | 98.80 | 97.02 | **82.64** |
| **qwen3-0.6b (FT)** | Proposed compact model | 92.17 | 92.10 | 72.46 | 98.26 | 98.38 | 96.20 | 70.10 |
| **qwen3-1.7b (FT)** | Proposed compact model | 90.61 | 90.84 | 68.88 | 99.23 | 99.34 | 98.31 | 67.90 |
| **Gemini-3.6-Flash-High** | Commercial baseline | 89.30 | 90.10 | 68.78 | 97.49 | 97.83 | 94.62 | 64.82 |
| **DeepSeek-V4-Flash** | General-purpose baseline | 73.72 | 74.37 | 40.97 | 95.84 | 95.96 | 91.90 | 37.72 |
| **qwen3-0.6b (base)** | Unadapted compact baseline | 19.44 | 19.80 | 4.49 | 80.17 | 81.79 | 70.59 | 0.82 |
| **qwen3-1.7b (base)** | Unadapted compact baseline | 4.21 | 4.33 | 0.00 | **99.86** | **99.84** | **99.72** | 0.00 |
| **Untouched raw text** | Control | 1.16 | 1.22 | 0.00 | 99.19 | 99.28 | 98.26 | 0.00 |

The reference GLM pipeline obtains the highest overall result, with 85.03% SanRec and 82.64% FULL. This result provides an empirical reference ceiling for the current benchmark. Among the compact deployment candidates, the fine-tuned 0.6B model achieves the strongest privacy–utility balance, reaching 72.46% SanRec and 70.10% FULL while retaining 98.26% of evaluated utility attributes.

---

## 6.3. Effect of ViPII Fine-Tuning

Fine-tuning produces the largest observed performance change. For Qwen3-0.6B, SanRec increases from 4.49% to 72.46% (**+67.97 percentage points**) and FULL increases from 0.82% to 70.10% (**+69.28 points**). SanAtt similarly rises from 19.44% to 92.17% (**+72.73 points**).

The Qwen3-1.7B base model retains nearly all non-sensitive content but sanitizes none of the evaluated sensitive units, yielding 0% FULL. After fine-tuning, it reaches 68.88% SanRec and 67.90% FULL while maintaining 98.31% RetRec. These paired base-versus-fine-tuned comparisons indicate that task-specific adaptation, rather than parameter count alone, is the principal source of sanitization capability in the evaluated compact models.

---

## 6.4. Compact Models versus General-Purpose Baselines

The fine-tuned Qwen3-0.6B model exceeds DeepSeek-V4-Flash by **31.49 points in SanRec** (72.46% versus 40.97%) and **32.38 points in FULL** (70.10% versus 37.72%). It also exceeds Gemini-3.6-Flash-High by **5.28 points in FULL** (70.10% versus 64.82%) and by **3.68 points in SanRec** (72.46% versus 68.78%).

These results show that, under the current ViPII protocol, a compact model adapted to Vietnamese PII/SPI sanitization can outperform larger general-purpose baselines on strict end-to-end success. The claim is limited to the evaluated models, prompts, test set, and metric definitions; it does not imply universal superiority over frontier language models.

---

## 6.5. Privacy–Utility Trade-off between the 0.6B and 1.7B Models

The two fine-tuned models exhibit a consistent trade-off. Qwen3-0.6B provides stronger sanitization, outperforming Qwen3-1.7B by **3.58 points in SanRec** and **2.20 points in FULL**. Conversely, Qwen3-1.7B preserves more operational content, improving RetAtt from 98.26% to 99.23% and RetRec from 96.20% to 98.31%.

Accordingly, the 0.6B configuration is the stronger choice when residual privacy leakage is the primary concern, whereas the 1.7B configuration may be preferable when conservative content retention is prioritized. Both models remain below the reference teacher pipeline, leaving substantial room for improving privacy recall without sacrificing utility.

---

## 6.6. Summary of Findings

The experimental results support three conclusions. First, unadapted compact models do not reliably sanitize Vietnamese PII/SPI. Second, ViPII fine-tuning yields large gains in both privacy recall and strict document-level success. Third, the 0.6B fine-tuned model offers the best result among the evaluated compact systems and general-purpose baselines, while the 1.7B model provides slightly stronger utility retention. Component ablations, robustness tests, error categories, and deployment efficiency are examined in the following section.
