# Section 2: Related Work

Research on personal-data protection in language technologies spans entity detection, de-identification, synthetic data generation, and privacy-aware model deployment. These lines of work are closely coupled but address distinct dimensions of the privacy problem. An entity detection system identifies spans that may reveal an individual; a de-identification system transforms or masks those spans; a synthetic data pipeline determines how training examples can be created without exposing genuine records; and a deployment strategy balances model capability against data-residency requirements. 

To systematically position our contributions with respect to the four research gaps identified in Section 1.2, this section reviews prior literature across four corresponding thematic areas: (1) PII detection systems and statutory frameworks; (2) Vietnamese NER and administrative linguistic nuances; (3) synthetic data generation and coordinate calibration; and (4) utility-preserving sanitization and compact on-premise language models.

---

## 2.1. PII Detection Systems and Statutory Taxonomies (Gap 1)

Early practical personal identifiable information (PII) systems were largely engineered around deterministic pattern matching, gazetteers, and modular recognizers. Frameworks such as Microsoft Presidio, Google Cloud Data Loss Prevention (DLP), Philter, and Amnesia illustrate various integrations of regular expressions, dictionaries, and general-purpose sequence taggers for identifying or masking sensitive tokens. These tools provide production-oriented engineering value, offering configurable entity recognizers and high throughput for structured credentials.

However, existing PII systems are predominantly organized around Western regulatory and operational regimes, such as the European Union's General Data Protection Regulation (GDPR) or the United States' Health Insurance Portability and Accountability Act (HIPAA). Consequently, their default taxonomies and decision policies do not reflect the statutory architecture of Vietnam's Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP). Decree 13 imposes a strict operational distinction between Basic Personal Data (`PII`, Articles 2.3 & 3) and Sensitive Personal Data (`SPI`, Articles 2.4 & 4), each carrying disparate compliance obligations, processing liabilities, and cross-border transfer restrictions. General-purpose PII scanners lack the category inventory necessary to operationalize this binary statutory tiering, highlighting the need for a dedicated, legally grounded Vietnamese benchmark.

---

## 2.2. Vietnamese NER and Administrative Linguistic Nuances (Gap 2)

Vietnamese named-entity recognition (NER) resources provide an indispensable computational foundation for processing Vietnamese text. Benchmarks such as VLSP NER and PhoNER have established standardized sequence labeling corpora for news, social media, and web texts, while pretrained language models such as PhoBERT have substantially advanced token-level representation learning. 

Despite these advances, standard Vietnamese NER paradigms exhibit critical limitations when adapted to personal data protection in administrative contexts:
1. **Scope and Entity Typology**: Conventional NER benchmarks focus on proper names categorized into coarse classes (Persons, Organizations, Locations, Miscellaneous). In contrast, personal data compliance encompasses high-risk numeric credentials (citizen identity cards, tax codes, insurance books), semi-structured demographic attributes (marital status, birth dates), and expansive narrative disclosures (medical conditions, judicial histories, economic hardship) that do not conform to proper-name conventions.
2. **Onomastic and Morphosyntactic Specificity**: Vietnamese personal names exhibit multi-part onomastic structures (compound surnames and regional naming traditions) where individual tokens frequently function as common nouns.
3. **Lexical Ambiguity and Clausal Homographs**: In isolating languages like Vietnamese, polysemous monosyllabic tokens can shift between sensitive personal data and common nouns depending on contextual cues (e.g., *Kinh* denoting an ethnic group versus *kinh tế* meaning economy; *Nam* denoting civil gender versus a geographic direction). Standard flat token classification models routinely over-predict or misclassify such ambiguous spans in the absence of explicit, sentence-bounded contextual cue disambiguation.

---

## 2.3. Synthetic Data Generation and Coordinate-Accurate Annotation (Gap 3)

Because authentic administrative, healthcare, and judicial dossiers cannot be lawfully redistributed under privacy regulations, synthetic corpus synthesis has become central to privacy-preserving NLP. Prior studies have explored template-based synthesis, schema-driven generation, and profile-guided generation to produce artificial corpora without exposing real individuals. In particular, the PRIVASIS framework demonstrated that conditioning generative language models on structured demographic profiles and situational contexts can yield large-scale parallel de-identification datasets.

Complementary to generative synthesis, programmatic labeling frameworks (such as Snorkel) apply heuristic labeling functions and weak supervision to reduce manual annotation costs. While effective for tabular and structured pattern extraction, programmatic labeling over free-form synthetic text encounters a fundamental obstacle: **the coordinate drift catastrophe**. When an autoregressive language model is prompted to simultaneously generate natural prose and output character indices or bounding offsets, variations in Unicode code-point normalization (NFC vs. NFD) and subword tokenization boundaries inevitably lead to shifted coordinates and boundary hallucinations. 

ViPII resolves this failure mode by enforcing a **decoupled architecture with manifest-guided value locking**: target PII/SPI attributes are locked deterministically at the host runtime layer before generation, relegating the LLM strictly to natural prose narration, while deterministic host-side algorithmic operators calibrate character spans post-hoc on clean normalized text.

---

## 2.4. Utility-Preserving Sanitization and Compact SLM Deployment (Gap 4)

Traditional text de-identification frequently relies on destructive redaction, replacing detected entities with generic masks or completely deleting sensitive phrases. While minimizing residual privacy leakage, aggressive redaction impairs grammatical coherence, destroys procedural context, and degrades downstream document utility for search, auditing, and administrative processing. 

Recent literature has consequently reframed de-identification as a **utility-preserving conditional generation task**, wherein a model must simultaneously eliminate sensitive information while preserving non-sensitive operational content and linguistic fluency. Evaluating this trade-off requires joint multi-dimensional metrics that penalize both residual privacy leakage ($\mathcal{L}_{\text{privacy}}$) and destructive over-redaction ($\mathcal{O}_{\text{redact}}$).

Concurrently, the deployment of language models for sensitive document processing is constrained by data governance and computational resources. While commercial cloud-scale frontier LLMs exhibit strong general reasoning, transmitting unredacted public sector records to third-party or foreign cloud APIs creates serious regulatory risks under Article 25 of Decree 13 (governing cross-border data transfers) as well as latency and operational costs. Compact Small Language Models (SLMs $\le 2\text{B}$ parameters), fine-tuned specifically for local on-premise execution, offer an auditable, cost-effective alternative. However, empirical comparisons evaluating whether fine-tuned compact SLMs can match or exceed commercial frontier baselines on Vietnamese utility-preserving sanitization have remained unavailable. ViPII establishes this controlled empirical comparison under a standardized benchmark protocol.

---

## 2.5. Summary

In summary, while existing literature offers valuable individual components—industrial PII recognizers, Vietnamese NER benchmarks, profile-guided synthetic generation, and utility-aware de-identification—it leaves their intersection unaddressed for the Vietnamese regulatory environment. ViPII bridges this gap: a Decree-13-compliant Vietnamese benchmark, synthesized through decoupled generation with deterministic host-side span calibration, and evaluated on the dual objectives of privacy defense and utility retention across compact fine-tuned SLMs and frontier baselines. 

Section 3 formalizes this task definition, the statutory taxonomy, and the operational representations.
