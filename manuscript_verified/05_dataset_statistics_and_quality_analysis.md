# Section 5: Dataset Statistics and Quality Analysis

In this section, we present an empirical evaluation of the **ViPII** corpus based on exhaustive census measurements over the finalized benchmark repository. We analyze corpus scale and field composition across the statutory categories, establish lexical and semantic diversity through moving-average token ratios (MATTR) and kernel Vendi Scores, and report verification diagnostics on annotation integrity, manifest coverage, and span calibration quality.

---

## 5.1. Corpus Scale and Composition

### Global Corpus Characteristics
The finalized ViPII corpus comprises **51,880 documents** containing **524,655 annotated character spans**. Table 5.1 summarizes the global scale, demographic source assets, register diversity, and structural length distributions of the benchmark.

#### Table 5.1: Overall Structural Characteristics of the ViPII Benchmark Corpus

| Metric / Dimension | Statistical Value | Operational Description & Sub-Categorization |
|:---|:---:|:---|
| **Total Documents ($D$)** | **51,880** | Fully realized natural language documents (`content`). |
| • Multi-Model Synthesis Pool | **47,880** (92.29%) | Training/validation pool generated across diverse frontier LLMs. |
| • Held-Out Benchmark Partition | **4,000** (7.71%) | Isolated evaluation benchmark (2,000 standard + 2,000 hard mode). |
| **Total Character Spans ($M$)** | **524,655** | Flat, non-overlapping ground-truth annotations ($\mathcal{Y}^*$). |
| **Average Spans per Document** | **10.11** (median: 10) | Range: 0 to 41 spans per document. |
| **Statutory Data Distribution** | | |
| • Basic Personal Data (**PII**) | **469,778** (89.54%) | Civil registration credentials, full name components, contact info. |
| • Sensitive Personal Data (**SPI**) | **54,877** (10.46%) | High-risk personal disclosures (health, judicial, financial, family). |
| **Foundational Asset Coverage** | | |
| • Synthetic Demographic Bank | Diverse Persona Repository | Artificially generated citizens across 54 ethnic groups. |
| • Situational Scenarios | **19** scenarios | Procedural motivations across civil, labor, health, and judicial domains. |
| • Public Service Form Metadata | **9,020** procedures | Reference metadata mapped across public service domains. |
| **Stylistic Register Breakdown** | | |
| • Third-Person Narrative (`third_person`) | **17,459** (33.65%) | Third-person administrative records and case histories. |
| • Formal Administrative (`administrative`) | **17,298** (33.34%) | Official petitions, administrative applications, and declarations. |
| • Consultative Dialogue (`dialogue`) | **17,123** (33.01%) | Public service consultations and citizen intake dialogues. |
| **Document Length Statistics** | | |
| • Total Syllables (Morphemes) | **19,757,596** | Monosyllabic morphemes after NFC normalization. |
| • Mean Document Length | **380.8** syllables | Median: 359.0 syllables (Std: 136.2; Range: 10 to 2,390). |
| **Generator Architectures** | | |
| • Synthesis Generators | 92.29% of corpus | Gemini-3.5-Flash-Low (8,262), Qwen3.5-122B (8,262), Qwen3.5-397B (8,256), DeepSeek-V4-Flash (8,252), Gemini-2.5-Flash-Lite (7,977), Gemini-3.1-Flash-Lite (6,871). |
| • Held-Out Benchmark Generator | 7.71% of corpus | GPT-5.5 (4,000 held-out evaluation instances). |

---

### Granular Distribution of the Statutory Fields
Table 5.2 provides the complete frequency census and character span length statistics across all actively populated fields in the corpus. In accordance with Vietnamese administrative naming conventions, personal names are fully decomposed into onomastic constituents (`given_name`, `family_name`, `middle_name`), ensuring granular evaluation without spatial collisions.

#### Table 5.2: Granular Frequency Census and Span Length Distribution across Fields in ViPII

| STT | Field Identifier ($f$) | Tier | Primary Mechanism | Span Count | Relative % | Mean Len (chars) | Median Len | Min–Max Len |
|:---:|:---|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | `given_name` | PII | Name-Comp. | 110,290 | 21.02% | 3.8 | 4 | 1 – 7 |
| 2 | `family_name` | PII | Name-Comp. | 74,873 | 14.27% | 4.2 | 4 | 1 – 7 |
| 3 | `middle_name` | PII | Name-Comp. | 57,183 | 10.90% | 4.8 | 4 | 1 – 20 |
| 4 | `phone` | PII | Verbatim | 55,168 | 10.52% | 12.4 | 12 | 10 – 1,676 |
| 5 | `dob` | PII | Cue-Context / Date | 54,145 | 10.32% | 12.4 | 10 | 4 – 1,864 |
| 6 | `cccd` | PII | Verbatim | 53,591 | 10.21% | 13.9 | 14 | 8 – 1,723 |
| 7 | `address` | PII | Verbatim | 53,360 | 10.17% | 60.1 | 61 | 6 – 1,776 |
| 8 | `name_alias` | PII | Anchor-Tag | 1,473 | 0.28% | 11.1 | 5 | 2 – 1,708 |
| 9 | `email` | PII | Verbatim | 1,396 | 0.27% | 26.1 | 26 | 5 – 40 |
| 10 | `marital_status` | PII | Cue-Context | 1,343 | 0.26% | 8.6 | 10 | 3 – 27 |
| 11 | `nationality` | PII | Cue-Context | 1,165 | 0.22% | 8.0 | 8 | 4 – 18 |
| 12 | `driver_license` | PII | Verbatim | 763 | 0.15% | 12.1 | 12 | 12 – 32 |
| 13 | `vehicle_plate` | PII | Verbatim | 591 | 0.11% | 9.6 | 10 | 9 – 10 |
| 14 | `gender` | PII | Cue-Context | 576 | 0.11% | 2.6 | 3 | 2 – 4 |
| 15 | `passport_number` | PII | Verbatim | 402 | 0.08% | 8.0 | 8 | 8 – 20 |
| 16 | `tax_code` | PII | Verbatim | 389 | 0.07% | 10.0 | 10 | 10 – 10 |
| **—** | **Subtotal Basic PII** | **PII** | — | **469,778** | **89.54%** | **15.4** | **10** | **1 – 1,864** |
| 17 | `bank_account` | SPI | Verbatim | 16,766 | 3.20% | 14.4 | 14 | 8 – 1,772 |
| 18 | `location_data` | SPI | Anchor-Tag | 10,057 | 1.92% | 39.1 | 33 | 3 – 2,118 |
| 19 | `private_life` | SPI | Anchor-Tag | 5,236 | 1.00% | 81.6 | 68 | 5 – 2,488 |
| 20 | `political_view` | SPI | Cue-Context | 4,128 | 0.79% | 38.8 | 37 | 6 – 1,302 |
| 21 | `health_status` | SPI | Anchor-Tag | 3,665 | 0.70% | 21.5 | 20 | 6 – 1,130 |
| 22 | `ethnicity` | SPI | Cue-Context | 3,114 | 0.59% | 4.1 | 4 | 2 – 18 |
| 23 | `family_relations` | SPI | Anchor-Tag | 3,070 | 0.59% | 21.6 | 22 | 2 – 90 |
| 24 | `sexual_orientation` | SPI | Anchor-Tag | 2,628 | 0.50% | 12.9 | 9 | 4 – 1,020 |
| 25 | `criminal_record` | SPI | Anchor-Tag | 2,327 | 0.44% | 59.5 | 62 | 10 – 1,588 |
| 26 | `biometric` | SPI | Anchor-Tag | 1,983 | 0.38% | 42.4 | 36 | 1 – 1,893 |
| 27 | `behavioral_data` | SPI | Anchor-Tag | 1,663 | 0.32% | 94.2 | 86 | 10 – 1,206 |
| 28 | `religion` | SPI | Cue-Context | 1,596 | 0.30% | 13.3 | 12 | 4 – 37 |
| 29 | `health_insurance_no` | SPI | Verbatim | 1,127 | 0.21% | 15.0 | 15 | 15 – 33 |
| 30 | `social_insurance_no` | SPI | Verbatim | 587 | 0.11% | 10.0 | 10 | 10 – 10 |
| **—** | **Subtotal Sensitive SPI** | **SPI** | — | **54,877** | **10.46%** | **38.2** | **24** | **1 – 2,488** |
| **ALL** | **Total Benchmark** | — | — | **524,655** | **100.00%** | **17.8** | **10** | **1 – 2,488** |

---

## 5.2. Lexical Diversity, Semantic Representation, and Anti-Mode-Collapse Analysis

A critical concern in synthetic text generation is whether the corpus exhibits authentic linguistic diversity or collapses into formulaic templates (*mode collapse*). To address this, we evaluate ViPII across multi-window lexical turnover (MATTR), semantic feature dispersion (Vendi Score), and document length distributions.

### Multi-Window Lexical Turnover: MATTR Evaluation
In isolating languages such as Vietnamese, monosyllabic morphemes (*tiếng*) are whitespace-delimited. Evaluating diversity solely at a single window size can introduce local artifacts. Table 5.3 reports Moving-Average Type-Token Ratio ($\text{MATTR}$) across expanding window sizes ($w \in \{10, 20, 50, 100\}$):

$$\text{MATTR}_w(D) = \frac{1}{N - w + 1} \sum_{i=1}^{N - w + 1} \frac{|\text{UniqueTokens}(D[i : i+w-1])|}{w}$$

#### Table 5.3: Empirical Lexical Diversity and Semantic Dispersion on ViPII

| Metric / Dimension | Window / Scope | Empirical Measurement |
|:---|:---:|:---:|
| **$\text{MATTR}_{w=10}$** | $w = 10$ syllables | **0.989** |
| **$\text{MATTR}_{w=20}$** | $w = 20$ syllables | **0.972** |
| **$\text{MATTR}_{w=50}$** | $w = 50$ syllables | **0.913** |
| **$\text{MATTR}_{w=100}$** | $w = 100$ syllables | **0.832** |
| **TF-IDF Kernel Vendi Score ($V_{\text{TF-IDF}}$)** | Sample $n = 1,000$ | **153.4** |

#### Analysis of Metric Trajectory
As the evaluation window expands from $w=10$ to $w=100$, MATTR scales gracefully from $0.989$ to $0.832$. Under $w=100$ (covering approximately 50–60 words, equivalent to 2–3 full administrative clauses), lexical turnover remains at $0.832$, confirming that administrative texts maintain continuous vocabulary variation rather than cycling repetitive stock phrases.

### Semantic Dispersion: Vendi Score Analysis
To quantify semantic dispersion without being confounded by length variations, we compute the **Vendi Score** over TF-IDF feature space:
$$V = \exp\left(-\sum_{i=1}^n \lambda_i \ln \lambda_i\right)$$
where $\lambda_i$ are the positive eigenvalues of the normalized cosine kernel matrix $K/n$. 

The corpus achieves a Vendi Score of **$V_{\text{TF-IDF}} = 153.4$**. Across the 19 canonical scenarios in the catalog, this score reflects an effective number of distinct semantic sub-clusters of approximately $8.1$ per scenario, confirming that the combination of procedural forms, demographic backgrounds, and stylistic registers prevents template collapse.

---

## 5.3. Annotation Integrity and Validation Verification

Across the pipeline execution, three verification stages ensure annotation integrity:
1. **Manifest Coverage**: During drafting and revision, generations are verified against target manifest slots, achieving $>98.5\%$ compliance.
2. **Anchor Syntax Validation**: Single-pass stack parsing checks delimiter balance, ensuring clean text $X_{\text{clean}}$ contains no residual tag syntax.
3. **Non-Overlapping Flat Partition**: Deterministic overlap resolution ensures the output ground truth satisfies $e_i^* \le s_j^*$ for all consecutive spans, providing valid target sequences for neural training and evaluation.
