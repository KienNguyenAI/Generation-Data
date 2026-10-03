# Section 1: Introduction

The rapid adoption of artificial intelligence in Vietnamese public administration, healthcare, finance, and legal services has increased the need to process documents that contain personal data. Such documents commonly combine structured identifiers—such as citizen identity numbers, telephone numbers, and dates of birth—with context-dependent information, including family circumstances, health status, and location. A system that releases these documents to an external service for analysis may therefore create privacy, governance, and operational risks. At the same time, simply deleting every potentially sensitive string can make an administrative document unusable for search, auditing, case handling, or downstream language processing.

This paper studies **utility-preserving sanitization** for Vietnamese personal data. The objective is not only to identify sensitive spans, but also to remove or replace them while retaining the non-sensitive procedural content and the linguistic coherence of the document. We focus on the terminology of Vietnam's Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP), using `PII` and `SPI` as dataset-level shorthand for the decree's basic and sensitive personal-data tiers, respectively. The legal mapping defines the scope of the benchmark; it is not, by itself, a complete legal-compliance certification for any deployment.

## 1.1. Motivation and Problem Setting

Existing multilingual PII tools provide useful starting points, but their entity inventories and decision rules are not designed around Vietnamese administrative conventions. Vietnamese documents contain identity numbers with local formatting, multi-component personal names, hierarchical addresses, and lexical items whose interpretation depends strongly on nearby cues. For example, *Nam* may denote a person's gender, a geographic region, or part of a name, while *Kinh* may denote an ethnicity or occur inside an unrelated phrase. Sensitive information such as health or family circumstances is often expressed as a long narrative clause rather than a short, regular expression match.

These characteristics create two coupled technical requirements. First, a benchmark must represent the relevant legal fields and provide reliable character-level boundaries. Second, a sanitization system must optimize two objectives simultaneously: reducing residual privacy leakage and avoiding destructive over-redaction. ViPII addresses the first requirement through controlled synthetic generation and deterministic character-span calibration, and evaluates the second through a dual privacy–utility metric suite.

## 1.2. Research Gaps

We identify four gaps that motivate the study:

1. **Regulatory and taxonomy mismatch.** Widely used PII resources and tools are generally organized around other legal or operational taxonomies. They do not directly expose the 34-field PII/SPI inventory used by this benchmark under the Vietnamese regulatory scope.
2. **Vietnamese administrative and linguistic specificity.** Local identity formats, multi-level addresses, Vietnamese name structure, and context-dependent words create failure cases that are underrepresented in general-purpose PII benchmarks.
3. **Reliable span construction for synthetic text.** When a language model is asked to generate prose and character offsets at the same time, changes in Unicode text and subword tokenization can produce incorrect boundaries. A reproducible benchmark therefore needs to separate text generation from coordinate calculation.
4. **Privacy–utility trade-off in local deployment.** Cloud-scale models may be difficult to use for sensitive documents because of governance, latency, cost, or data-residency requirements. The relative value of compact models adapted to the local task has not been established under a common Vietnamese sanitization protocol.

## 1.3. The ViPII Approach

ViPII is a benchmark and data-construction framework for Vietnamese PII/SPI detection and utility-preserving sanitization. Its central design principle is to assign different responsibilities to the generator and the annotation pipeline. A manifest fixes the sensitive values and the fields that should appear; a language model renders those values in natural administrative contexts; and deterministic host-side procedures compute character spans after generation. The pipeline combines guarded verbatim matching, cue-context disambiguation, disjoint name-component decomposition, and semantic anchor-tag parsing. These mechanisms construct the ground truth offline and are not treated as the neural architecture of the evaluated models.

The resulting corpus contains 47,881 documents and 474,874 annotated character spans covering 34 field classes. Each instance provides natural-language input, flat non-overlapping character spans, and sanitization targets. The benchmark reports privacy protection and utility retention together, with document-level `FULL` success requiring both the removal of annotated sensitive units and the preservation of evaluated non-sensitive operational units.

## 1.4. Contributions

This paper makes the following contributions:

1. **A Vietnamese legal-scope benchmark.** We introduce a 34-field PII/SPI benchmark aligned with the operational scope of Decree No. 13/2023/NĐ-CP, covering structured identifiers, context-dependent attributes, name components, and narrative sensitive information.
2. **A constraint-first synthesis and annotation pipeline.** We present a decoupled generation process in which manifests and controlled profiles specify target values, while deterministic post-processing computes accepted character spans and resolves candidate conflicts.
3. **A joint privacy–utility evaluation framework.** We define sanitization and retention metrics at span, field, and document levels, including the strict `FULL` measure for end-to-end success.
4. **An empirical study of compact models.** On the current held-out benchmark, fine-tuned Qwen3 compact models substantially improve over their unadapted counterparts. The 0.6B model achieves 72.46% `SanRec` and 70.10% `FULL`, while the 1.7B model provides higher retention scores; comparisons with general-purpose baselines are reported under the same evaluation protocol.

## 1.5. Scope and Organization

The study focuses on Vietnamese text generated for administrative, legal, healthcare, and related social contexts. It evaluates the quality of synthetic annotations and the behavior of sanitization systems under the benchmark protocol; it does not claim that synthetic data fully represents all real-world documents or that a model score alone establishes legal compliance. Section 2 reviews related work. Section 3 defines the tasks, legal taxonomy, and operational representation. Section 4 describes the constraint-first synthesis and annotation pipeline, and Section 5 reports corpus statistics and quality diagnostics. Section 6 presents the experimental comparison and main results. Subsequent sections analyze component effects, robustness, error patterns, practical deployment considerations, ethics, limitations, and reproducibility before concluding the paper.
