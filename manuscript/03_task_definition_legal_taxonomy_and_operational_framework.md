# Section 3: Task Definition, Legal Taxonomy, and Operational Framework

In this section, we formulate the dual tasks of span-level detection and generative sanitization in **ViPII**, ground the taxonomy in the statutory requirements of Vietnam's Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP), and detail the deterministic operational mechanisms and conflict-resolution policies employed for ground-truth construction.

---

## 3.1. Formal Task Formulation

### Input Representation and Unicode Coordinate Space
Let $\mathcal{C}$ denote the finite alphabet of Unicode code points. To ensure strict canonical equivalence across Vietnamese combining diacritics and varying Input Method Editor (IME) representations, all text instances are normalized to Unicode Normalization Form C (NFC). An input document is represented as an ordered sequence of $N$ Unicode code points:
$$X_{\text{raw}} = (c_1, c_2, \dots, c_N), \quad c_t \in \mathcal{C}$$

Within $X_{\text{raw}}$, sensitive personal data instances reside as contiguous subsequences, termed **character spans**. A ground-truth personal data span is formally denoted by the tuple:
$$y_i = \bigl(s_i, e_i, f_i, l_i\bigr)$$
where:
* $s_i \in \{0, \dots, N-1\}$ is the 0-indexed inclusive start code-point offset in Python string representation.
* $e_i \in \{1, \dots, N\}$ is the 0-indexed exclusive end code-point offset ($s_i < e_i$).
* $f_i \in \mathcal{F}$ designates the fine-grained attribute category selected from the **34 fields** ($\mathcal{F} = \{f_1, \dots, f_{34}\}$).
* $l_i \in \{\text{PII}, \text{SPI}\}$ denotes the statutory classification under Decree 13: Basic Personal Data ($\text{PII}$) or Sensitive Personal Data ($\text{SPI}$).

> **Measurement Invariant**: Character offsets in ViPII are defined strictly over **Unicode code points after NFC normalization** ($0 \le s_i < e_i \le \text{len}(X)$ in Python 3). They are strictly distinct from multi-byte UTF-8 byte offsets (where Vietnamese accented characters occupy 2–3 bytes) and from tokenizer-dependent subword BPE token indices.

```
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │                     Input: Raw Text X_raw                   │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                 ┌───────────────────────────────┴──────────────────────────────┐
                                 ▼                                                              ▼
                  ┌──────────────────────────────┐                              ┌──────────────────────────────┐
                  │           TASK 1:            │                              │           TASK 2:            │
                  │     Span-level detection     │                              │      Utility-preserving      │
                  │        and annotation        │                              │         sanitization         │
                  └──────────────┬───────────────┘                              └──────────────┬───────────────┘
                                 │                                                             │
                                 ▼                                                             ▼
                  ┌──────────────────────────────┐                              ┌──────────────────────────────┐
                  │   Character Spans Y_hat      │                              │     Sanitized Text X_san     │
                  │ {(s, e, field, PII/SPI)}     │                              │ Tag Masking / Synthetic Swap │
                  └──────────────────────────────┘                              └──────────────┬───────────────┘
                                                                                               │
                                                                 ┌─────────────────────────────┴───────────────┐
                                                                 ▼                                             ▼
                                                  ┌──────────────────────────────┐              ┌──────────────────────────────┐
                                                  │       Privacy Defense        │              │     Utility Preservation     │
                                                  │  Residual Privacy Leakage ≈0 │              │       Over-redaction ≈ 0     │
                                                  │    (High Sanitization Rec)   │              │     (High Retention Rec)     │
                                                  └──────────────────────────────┘              └──────────────────────────────┘
```

### Clarification of Text States in the Generation Pipeline
To prevent mathematical conflation between intermediate pipeline artifacts and downstream inference inputs, we formally distinguish four text states:
1. $X_{\text{tagged}}$: The raw draft emitted by the generator LLM containing inline semantic markup `⟦field⟧...⟦/field⟧`.
2. $X_{\text{clean}}$: The clean natural language text resulting from parsing and completely stripping markup tags via a deterministic LIFO stack parser; ground-truth span offsets $\mathcal{Y}^*$ are calibrated on this string.
3. $X_{\text{raw}}$: The unannotated natural language document presented as input to downstream models ($X_{\text{raw}} \equiv X_{\text{clean}}$ during benchmark inference).
4. $X_{\text{sanitized}}$: The final de-identified text generated by the sanitization model $\mathcal{M}(X_{\text{raw}})$.

### Canonical Schema: Flat, Non-Overlapping Spans and Name Projection
The benchmark ground truth $\mathcal{Y}^*$ exported in `dataset.jsonl` strictly follows a **flat, non-overlapping schema**:
$$\mathcal{Y}^* = \{y_1^*, y_2^*, \dots, y_M^*\}, \quad \text{such that } e_i^* \le s_j^* \quad \forall i < j$$

To reconcile flat sequence evaluation with the hierarchical nature of Vietnamese civil names (where a full name encompasses a surname, middle name, and given name), ViPII formalizes a **Disjoint Name Projection Operator** $\Pi_{\text{name}}$.

Let $y_{\text{full}} = (s, e, \text{'full\_name'}, \text{'PII'})$ denote a composite civil name span. The operator $\Pi_{\text{name}}(y_{\text{full}}, X)$ projects $y_{\text{full}}$ onto a sequence of contiguous, non-overlapping sub-spans:
$$\Pi_{\text{name}}(y_{\text{full}}, X) = \{(s_{\text{fam}}, e_{\text{fam}}, \text{'family\_name'}, \text{'PII'}), (s_{\text{mid}}, e_{\text{mid}}, \text{'middle\_name'}, \text{'PII'}), (s_{\text{giv}}, e_{\text{giv}}, \text{'given\_name'}, \text{'PII'})\}_{\text{non-empty}}$$
satisfying the boundary ordering:
$$s = s_{\text{fam}} < e_{\text{fam}} \le s_{\text{mid}} < e_{\text{mid}} \le s_{\text{giv}} < e_{\text{giv}} = e$$

The fine-grained ground-truth representation $\mathcal{Y}^*_{\text{decomposed}}$ is obtained via disjoint projection:
$$\mathcal{Y}^*_{\text{decomposed}} = \Bigl(\mathcal{Y}^* \setminus \{y \in \mathcal{Y}^* \mid y.\text{field} = \text{'full\_name'}\}\Bigr) \cup \bigcup_{y \in \mathcal{Y}^*, y.\text{field} = \text{'full\_name'}} \Pi_{\text{name}}(y, X)$$

This formulation ensures that both the composite view $\mathcal{Y}^*$ and the decomposed view $\mathcal{Y}^*_{\text{decomposed}}$ are strictly flat partitions over the code-point space, avoiding invalid nested span collisions during sequence evaluation.

### Task 1: Span-Level Detection and Annotation
In this structured prediction mode, a model $g: \mathcal{X} \to 2^{\mathcal{S}}$ ingests $X_{\text{raw}}$ and predicts a set of character spans:
$$\hat{\mathcal{Y}} = \bigl\{\hat{y}_j = (\hat{s}_j, \hat{e}_j, \hat{f}_j, \hat{l}_j)\bigr\}_{j=1}^{\hat{M}}$$

A predicted span $\hat{y}_j$ is evaluated as a strict exact match against a ground-truth entity $y_i^*$ if and only if:
$$\hat{s}_j = s_i^* \quad \land \quad \hat{e}_j = e_i^* \quad \land \quad \hat{f}_j = f_i^* \quad \land \quad \hat{l}_j = l_i^*$$

### Task 2: Utility-Preserving Sanitization
In this generative de-identification mode, an end-to-end model $\mathcal{M}: \mathcal{X} \to \mathcal{X}$ transforms $X_{\text{raw}}$ directly into a **sanitized text**:
$$X_{\text{sanitized}} = \mathcal{M}(X_{\text{raw}})$$

De-identification follows two operational paradigms:
1. **Tag Masking**: Replacing sensitive spans $X_{\text{raw}}[s_i:e_i]$ with standardized category mask tokens:
   $$\tau(f_i) \in \bigl\{\texttt{[HỌ\_TÊN]}, \texttt{[CCCD]}, \texttt{[SỐ\_ĐIỆN\_THOẠI]}, \texttt{[TÌNH\_TRẠNG\_SỨC\_KHỎE]}, \dots\bigr\}$$
2. **Consistent Synthetic Replacement**: Substituting sensitive spans with synthetic values from an isolated demographic database, preserving global grammatical agreement and referential coherence across documents.

---

## 3.2. Conceptual Objectives: Privacy Leakage versus Utility Retention

The evaluation of utility-preserving de-identification balances privacy defense against information utility. We formalize this duality conceptually through **residual privacy leakage** and **over-redaction**.

Let $\mathcal{P}(X_{\text{raw}})$ denote the set of ground-truth sensitive personal data units (spans or attributes) contained within document $X_{\text{raw}}$, and let $\mathcal{U}(X_{\text{raw}})$ denote the set of non-sensitive operational, procedural, administrative, and syntactic information units necessary to preserve document utility.

### Residual Privacy Leakage
When a sanitization model processes $X_{\text{raw}}$, any personal data entity belonging to $\mathcal{P}(X_{\text{raw}})$ that remains identifiable or recoverable in $X_{\text{sanitized}}$ constitutes an empirical privacy failure.

Let $\mathbb{I}_{\text{leak}}(y_i^*, X_{\text{sanitized}})$ be an indicator function evaluated under an explicit verification protocol $\mathcal{V}_{\text{privacy}}(y_i^*, X_{\text{sanitized}})$, returning 1 if the sensitive content of ground-truth span $y_i^*$ persists in $X_{\text{sanitized}}$ in unredacted or recoverable form, and 0 if successfully sanitized. The empirical **Residual Privacy Leakage Rate** ($\mathcal{L}_{\text{privacy}}$) across a test corpus of $D$ documents is expressed as:

$$\mathcal{L}_{\text{privacy}} = 1 - \text{SanRec} = \frac{\sum_{d=1}^D \sum_{i=1}^{M_d} \mathbb{I}_{\text{leak}}(y_{d,i}^*, X_{d,\text{sanitized}})}{\sum_{d=1}^D M_d}$$

where $\text{SanRec}$ denotes **Sanitization Recall**.

> **Methodological Disclaimer**: Residual leakage is measured specifically against the predefined ground-truth sensitive units under an explicitly specified matching and privacy-audit protocol. While $1 - \text{SanRec}$ quantifies the empirical leakage rate of annotated entities, in production environments privacy verification also requires auditing partial obfuscations, model hallucinations, and linkage attacks; these operational evaluation protocols are formalized in Section 6. A zero-leakage target ($\mathcal{L}_{\text{privacy}} = 0$) is adopted as a conservative engineering objective for privacy-sensitive deployments; it should not be interpreted as a complete legal compliance determination.

### Over-Redaction and Utility Retention
Conversely, if the sanitization model aggressively suppresses or deletes non-sensitive administrative content, procedural instructions, legal references, or grammatical connectives ($u_k \in \mathcal{U}(X_{\text{raw}})$), the document's downstream utility is compromised.

Let $\mathbb{I}_{\text{suppress}}(u_k, X_{\text{sanitized}})$ indicate whether a valid operational information token $u_k \in \mathcal{U}(X_{\text{raw}})$ has been erroneously masked or destroyed. The **Over-Redaction Rate** ($\mathcal{O}_{\text{redact}}$) is defined conceptually as:

$$\mathcal{O}_{\text{redact}} = 1 - \text{RetRec} = \frac{\sum_{d=1}^D \sum_{k=1}^{K_d} \mathbb{I}_{\text{suppress}}(u_{d,k}, X_{d,\text{sanitized}})}{\sum_{d=1}^D K_d}$$

where $\text{RetRec}$ denotes **Retention Recall**. The operational construction of $\mathcal{U}(X)$ (derived from procedural form slots and lexical references), the matching policy (accounting for semantic paraphrasing vs. destructive deletion), and the aggregation schemes across tokens, attributes, and records ($\text{RetAtt}$, $\text{RetA/R}$, $\text{RetRec}$) are concretely specified in Section 6.

### Comprehensive Success Metric: $\text{FULL}$
A sanitization system achieves full end-to-end success on a document if and only if it incurs zero residual privacy leakage and zero over-redaction of operational slots:

$$\text{FULL} = \frac{1}{D} \sum_{d=1}^D \Biggl[ \prod_{i=1}^{M_d} \bigl(1 - \mathbb{I}_{\text{leak}}(y_{d,i}^*, X_{d,\text{sanitized}})\bigr) \times \prod_{k=1}^{K_d} \bigl(1 - \mathbb{I}_{\text{suppress}}(u_{d,k}, X_{d,\text{sanitized}})\bigr) \Biggr]$$

---

## 3.3. Legal Scope and the Decree-13 Taxonomy (34 Fields)

### Statutory Context and Jurisdiction
The statutory taxonomy of ViPII is established under the legal framework of the Socialist Republic of Vietnam, categorized across three legal instruments:
1. **Enacted Statutory Law (Currently in Effect)**: **Decree No. 13/2023/NĐ-CP on Personal Data Protection (PDPD)**, promulgated by the Government of Vietnam on April 17, 2023, and effective July 1, 2023:
   * **Articles 2(3) and 3**: Formally define and list the classes comprising Basic Personal Data ($\text{PII}$).
   * **Articles 2(4) and 4**: Formally define and list the classes comprising Sensitive Personal Data ($\text{SPI}$).
   * **Article 8**: Stipulates strict prohibitions against illegal processing or unauthorized disclosure of personal data.
   * **Article 25**: Imposes stringent regulatory conditions on cross-border transfers of Vietnamese citizen data, underscoring the necessity for compact, local on-premise de-identification models.
2. **Enacted Administrative Instrument**: **Resolution No. 202/2025/QH15** of the National Assembly on administrative territorial restructuring, which mandates tracking historical and merged provincial/communal designations in civil documentation.
3. **Prospective Regulatory Horizon**: The **Draft Law on Personal Data Protection (PDPD 2025/2026)**, which outlines enhanced audit obligations; this draft is cited strictly as motivational background for forward-looking compliance, not as currently enacted statutory law.

### The 34 Field Classes
Under Decree 13, personal data is partitioned into two statutory tiers:
* **Basic Personal Data ($\text{PII}$ - 18 Fields)**: Identifiers that uniquely or collectively identify an individual in civil, administrative, and commercial spheres.
* **Sensitive Personal Data ($\text{SPI}$ - 16 Fields)**: Information intimately linked to private rights and liberties which, if breached, directly imperils dignity, financial standing, social security, or personal safety.

#### Table 3.1: Summary of the 34 Fields under the ViPII Decree-13 Legal Taxonomy
*(For the exhaustive statutory citations, detailed legal definitions, and canonical Vietnamese examples for all 34 fields, see Appendix A).*

| Statutory Tier | Field Count | Category Clusters | Field Identifiers ($f \in \mathcal{F}$) |
|:---|:---:|:---|:---|
| **Basic Personal Data**<br/>(**PII** - Decree 13, Art. 2(3) & 3) | **18** | **Civil & Identity Numbers**<br/>*(8 fields)* | `cccd` (Citizen ID 12 digits), `cmnd` (Legacy ID 9 digits), `phone`, `email`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code` |
| | | **Civil Identifiers & Names**<br/>*(5 fields)* | `full_name`, `family_name`, `middle_name`, `given_name`, `address` |
| | | **Demographic & Digital**<br/>*(5 fields)* | `dob` (Date of birth), `gender`, `marital_status`, `nationality`, `digital_account` |
| **Sensitive Personal Data**<br/>(**SPI** - Decree 13, Art. 2(4) & 4) | **16** | **Financial & Digital Credential**<br/>*(4 fields)* | `bank_account`, `social_insurance_no` (BHXH), `health_insurance_no` (BHYT), `eid_credentials` (VNeID) |
| | | **Belief, Origin & Tracking**<br/>*(6 fields)* | `ethnicity`, `religion`, `political_view`, `location_data`, `behavioral_data`, `place_components` |
| | | **Vulnerable Life & Health**<br/>*(6 fields)* | `health_status`, `criminal_record`, `private_life`, `family_relations`, `sexual_orientation`, `biometric` |
| **Total** | **34** | — | — |

---

## 3.4. Operational Ground-Truth Construction Mechanisms

> **Important Architectural Clarification**: The four mechanisms described below are **deterministic algorithmic modules executed offline within the pipeline** to construct ground-truth annotations ($\mathcal{Y}^*$) and calibrate span coordinates with zero offset error. They do **not** constitute the neural model architecture evaluated in Section 6. Downstream models (such as fine-tuned Qwen-3 SLMs and frontier LLMs) receive only unannotated natural language ($X_{\text{raw}}$) and must learn to identify spans or generate sanitized text end-to-end without auxiliary symbolic cues.

To eliminate coordinate drift without manual re-annotation, the pipeline partitions the 34 fields across **four primary operational mechanisms**:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          FOUR GROUND-TRUTH CALIBRATION MECHANISMS IN VIPII                              │
├───────────────────────────────┬─────────────────────────────────────────────────────────────────────────┤
│ 1. Verbatim Matching          │ Guarded word-boundary Regex lookaround matching invariant values.       │
│    (via: verbatim - 13 fields)│ Applied to canonical credentials, phone, CCCD, email, full names.       │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
│ 2. Cue-Context Disambiguation │ 80-character sentence-bounded lookback window for trigger cues.         │
│    (via: cue_context - 10 fld)│ Disambiguates homographs (e.g., "Kinh" ethnicity vs. "kinh tế").        │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
│ 3. Name-Component             │ Algorithmic decomposition of Vietnamese personal names into             │
│    Decomposition              │ Surname, Middle Name, and Given Name components.                        │
│    (via: name_component - 3 f)│ Handled via disjoint parsing over resolved full_name spans.             │
├───────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
│ 4. Semantic Anchor-Tag        │ Linear-time O(N) LIFO stack parser decoding inline tags                 │
│    Parsing (via: anchor_tag)  │ ⟦field⟧...⟦/field⟧ for complex, free-form, variable-length SPI clauses  │
│    (8 fields: 1 PII, 7 SPI)   │ (plus conversational PII digital_account handles).                      │
└───────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘
```

1. **Guarded Verbatim Matching (`via: verbatim` - 13 fields)**:
   * *Principle*: Matches invariant alphanumeric credentials and addresses pre-specified in the generation manifest. Uses Unicode-aware zero-width lookaround assertions:
     $$R(v) = \texttt{(?<!\textbackslash{}w)} + \text{re.escape}(v) + \texttt{(?!\textbackslash{}w)}$$
   * *Fields (13 fields: 10 PII, 3 SPI)*: Basic PII: `cccd`, `cmnd`, `phone`, `email`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code`, `address`, `full_name`. Sensitive SPI: `bank_account`, `social_insurance_no`, `health_insurance_no`.

2. **Cue-Context Disambiguation (`via: cue_context` - 10 fields)**:
   * *Principle*: Resolves lexical homographs (e.g., ethnic *Kinh* vs. *kinh tế*, gender *Nam* vs. geographic *miền Nam*) and general dates. The matcher inspects a sliding window backwards up to $W = 80$ characters, bounded by sentence terminators (`.`, `;`, `\n`, `!`, `?`). A span is extracted only when an authoritative trigger cue is co-located in the clause.
   * *Fields (10 fields: 4 PII, 6 SPI)*: Basic PII: `dob`, `gender`, `marital_status`, `nationality`. Sensitive SPI: `ethnicity`, `religion`, `political_view`, `location_data`, `behavioral_data`, `place_components`.

3. **Name-Component Decomposition (`via: name_component` - 3 fields)**:
   * *Principle*: Splits validated `full_name` strings into onomastic constituents using rule-based parsing over Vietnamese compound surnames (`ho_kep`) and ethnic patronymic prefixes ($Y$, $H'$).
   * *Fields (3 fields: 3 PII, 0 SPI)*: Basic PII: `family_name`, `middle_name`, `given_name`.

4. **Semantic Anchor-Tag Parsing (`via: anchor_tag` - 8 fields)**:
   * *Principle*: Variable-length, narrative clauses lacking fixed patterns are enclosed by the generator in lightweight delimiters `⟦field⟧...⟦/field⟧`. A single-pass $\mathcal{O}(N)$ LIFO stack parser extracts exact coordinates, records ground-truth spans, and strips all tags to yield $X_{\text{clean}}$.
   * *Fields (8 fields: 1 PII, 7 SPI)*: Basic PII (1 field): `digital_account` (informal OTT conversational handles; standard URLs can also be extracted verbatim). Sensitive SPI (7 fields): `health_status`, `criminal_record`, `private_life`, `family_relations`, `sexual_orientation`, `biometric`, `eid_credentials`.

### Table 3.2: Disjoint Cross-Mapping Matrix: Decree 13 Statutory Tiers vs. Primary Operational Mechanisms
Every field is assigned to **exactly one primary operational mechanism**, producing an exact mathematical partition:

| Primary Operational Mechanism | Basic Personal Data (PII) [18 Fields] | Sensitive Personal Data (SPI) [16 Fields] | Total Partition |
|:---|:---|:---|:---:|
| **1. Verbatim Matching** (`via: verbatim`) | `cccd`, `cmnd`, `phone`, `email`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code`, `address`, `full_name` [10 fields] | `bank_account`, `social_insurance_no`, `health_insurance_no` [3 fields] | **13** |
| **2. Cue-Context Disambiguation** (`via: cue_context`) | `dob`, `gender`, `marital_status`, `nationality` [4 fields] | `ethnicity`, `religion`, `political_view`, `location_data`, `behavioral_data`, `place_components` [6 fields] | **10** |
| **3. Name-Component Decomposition** (`via: name_component`) | `family_name`, `middle_name`, `given_name` [3 fields] | *(None)* [0 fields] | **3** |
| **4. Semantic Anchor-Tag Parsing** (`via: anchor_tag`) | `digital_account` [1 field] | `health_status`, `criminal_record`, `private_life`, `family_relations`, `sexual_orientation`, `biometric`, `eid_credentials` [7 fields] | **8** |
| **Total Exact Partition** | **18 Fields** | **16 Fields** | **34 Fields** |

---

## 3.5. Conflict Resolution and Priority Lattice Policy

During ground-truth construction, multiple matchers may yield overlapping candidate spans. For example, an atomic credential may appear inside a narrative `private_life` clause, or a surname matcher may conflict with an encompassing full name. To enforce a strict flat representation $\mathcal{Y}^*$, the pipeline executes a deterministic **5-Tier Priority Lattice** conflict resolution policy.

### Formal Set Relationships
We formally partition all extracted spans into three sets:
1. **Candidate Spans ($\mathcal{S}_{\text{cand}}$)**: The raw set of all span hypotheses produced by the four offline extraction mechanisms:
   $$\mathcal{S}_{\text{cand}} = \mathcal{S}_{\text{sensitive-cand}} \cup \mathcal{S}_{\text{distractor}}, \quad \mathcal{S}_{\text{sensitive-cand}} \cap \mathcal{S}_{\text{distractor}} = \emptyset$$
2. **Adversarial Distractor Spans ($\mathcal{S}_{\text{distractor}}$)**: Non-sensitive structural tokens injected during generation to test discrimination—specifically 12-digit administrative document codes (`doc_code` of type `num12`) carrying label `O`. These spans participate actively during overlap resolution to suppress false-positive matching against 12-digit `cccd` credentials.
3. **Resolved Set ($\mathcal{S}_{\text{resolved}}$)**: The maximal conflict-free subset produced by the priority lattice operator $\Omega(\mathcal{S}_{\text{cand}})$.
4. **Final Ground-Truth Spans ($\mathcal{Y}^*$)**: The finalized, non-overlapping set of validated PII/SPI spans exported in `dataset.jsonl`, obtained by filtering out distractors:
   $$\mathcal{Y}^* = \{s \in \mathcal{S}_{\text{resolved}} \mid \text{label}(s) \neq \text{'O'}\}, \quad \text{where } \mathcal{S}_{\text{distractor}} \cap \mathcal{Y}^* = \emptyset$$

### The 5-Tier Priority Lattice
Candidate spans are prioritized according to semantic precision and statutory sensitivity:
$$\text{Tier 1 (Weight 100)} \succ \text{Tier 2 (Weight 80)} \succ \text{Tier 3 (Weight 60)} \succ \text{Tier 4 (Weight 50)} \succ \text{Tier 5 (Weight 40)}$$

* **Tier 1 (Invariant Atomic IDs, Weight 100)**: `cccd`, `cmnd`, `phone`, `email`, `passport_number`, `driver_license`, `vehicle_plate`, `tax_code`, `dob`, `bank_account`, `social_insurance_no`, `health_insurance_no`, `eid_credentials`, and non-PII distractor codes (`doc_code`). *Atomic credentials take absolute precedence and cannot be overwritten.*
* **Tier 2 (Specialized SPI Clauses, Weight 80)**: `health_status`, `criminal_record`, `biometric`, `ethnicity`, `religion`, `political_view`, `sexual_orientation`.
* **Tier 3 (Core Civil PII, Weight 60)**: `full_name`, `address`, `family_relations`, `digital_account`, `marital_status`, `gender`, `nationality`.
* **Tier 4 (Standalone Personal Names, Weight 50)**: Standalone `given_name` appearing in dialogue greetings or signature lines outside a `full_name` span.
* **Tier 5 (Broad Contextual SPI, Weight 40)**: `private_life`, `location_data`, `behavioral_data`.

### Algorithmic Tie-Breaking and Formal Interval Subtraction
When two candidate spans $s_a, s_b \in \mathcal{S}_{\text{cand}}$ collide ($s_a.\text{start} < s_b.\text{end} \land s_b.\text{start} < s_a.\text{end}$), collisions are resolved via a deterministic hierarchy:
1. **Primary: Priority Weight**: Higher tier weight wins ($\text{weight}(s_a) > \text{weight}(s_b)$).
2. **Secondary: Span Length**: If weights are equal, the longer span is retained (Longest-Match: $e_a - s_a > e_b - s_b$).
3. **Tertiary: Start Offset**: If weights and lengths are identical, the earlier span wins (Left-to-Right: $s_a.\text{start} < s_b.\text{start}$).

> **Formal Interval Subtraction for Broad Narrative Contexts (Tier 5)**: When a Tier 5 broad narrative span $I_{\text{broad}} = [s_{\text{broad}}, e_{\text{broad}})$ intersects with a set of $K$ already accepted higher-priority intervals $\mathcal{I}_{\text{higher}} = \{[s_k, e_k)\}_{k=1}^K$, rather than dropping the broad context entirely, the pipeline computes the set difference:
> $$\text{Res}(I_{\text{broad}}) = I_{\text{broad}} \setminus \bigcup_{k=1}^K [s_k, e_k) = \bigcup_{j=1}^J [s'_j, e'_j)$$
> where each $[s'_j, e'_j)$ is a maximal contiguous, non-empty sub-interval. A residual sub-interval is retained as a valid ground-truth span if and only if $e'_j - s'_j \ge \theta_{\text{min}}$ (where $\theta_{\text{min}} = 5$ code points), ensuring surrounding domestic and narrative hardship is preserved without swallowing atomic credentials.

```
Algorithm 1: Deterministic 5-Tier Priority Overlap Resolution (Ω)
──────────────────────────────────────────────────────────────────────────────────
Input  : Raw candidate spans S_cand, Priority weight function w(·), 
         Minimum residual context threshold θ_min = 5
Output : Conflict-free ground-truth span set Y*

1:  S_sorted ← Sort S_cand by primary key w(s) descending, 
                     secondary key (e - s) descending, tertiary key s ascending
2:  S_accepted ← ∅
3:  for each span s in S_sorted do
4:      I_collide ← {a ∈ S_accepted | s.start < a.end ∧ a.start < s.end}
5:      if I_collide = ∅ then
6:          S_accepted ← S_accepted ∪ {s}
7:      else if w(s) = 40 then  // Tier 5: Broad contextual narrative span
8:          Res(s) ← [s.start, s.end) \ ⋃_{a ∈ I_collide} [a.start, a.end)
9:          for each contiguous interval [s'_j, e'_j) in Res(s) do
10:             if (e'_j - s'_j) ≥ θ_min then
11:                 s_trim ← InstantiateSpan(s'_j, e'_j, s.field, s.label, s.via)
12:                 S_accepted ← S_accepted ∪ {s_trim}
13:             end if
14:         end for
15:     end if
16: end for
17: Y* ← {s ∈ S_accepted | s.label ≠ "O"}  // Filter out adversarial non-PII distractors
18: return Sort Y* by start offset ascending
──────────────────────────────────────────────────────────────────────────────────
```

By formalizing these definitions, set relations, and deterministic policies, Section 3 provides an unambiguous, mathematically consistent foundation for the synthesis pipeline (Section 4), benchmark statistics (Section 5), and experimental evaluations (Section 6).
