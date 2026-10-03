# Section 8: Ethical Considerations, Limitations, and Reproducibility

This section outlines the ethical principles governing the construction of ViPII, identifies inherent methodological and empirical limitations, and provides concrete specifications to ensure open reproducibility.

---

## 8.1. Ethical Considerations and Privacy Protection

### Absolute synthetic generation and zero citizen data leakage
A central ethical commitment of this work is the strict exclusion of authentic citizen records. All 51,880 documents and 524,655 annotated entity spans in ViPII were generated through a fully decoupled programmatic pipeline combining synthetic profile registries with natural language generators. Personal identification numbers (such as 12-digit Citizen Identity Card numbers `cccd`, driver's licenses, and social insurance numbers) were synthesized using procedural algorithmic generators conforming to official formatting standards while deliberately utilizing unallocated prefixes, test series, and algorithmic check-sum sequences to prevent accidental collisions with real living individuals.

Under Vietnam's Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP), processing authentic sensitive personal data without explicit informed consent constitutes a severe regulatory violation. By employing purely synthetic generation governed by deterministic programmatic manifests, ViPII provides a risk-free, ethically sound research testbed that allows the AI research community to evaluate privacy protection technologies without compromising the rights or confidentiality of Vietnamese citizens.

### Dual-use mitigation and defensive alignment
Technologies designed for PII detection and sanitization inherently carry dual-use potential: an entity detector can theoretically be repurposed by malicious actors to automate targeted data scraping, surveillance, or citizen re-identification. To mitigate this risk, ViPII is explicitly oriented toward **defensive utility-preserving sanitization**. Our benchmark and model weights are trained to sanitize and redact sensitive attributes rather than extract citizen databases. Furthermore, the synthetic profiles contain no actionable real-world intelligence, ensuring that model training produces robust contextual sanitizers rather than entity knowledge bases.

---

## 8.2. Limitations

While ViPII provides the first comprehensive, Decree-13-aligned sanitization benchmark for Vietnamese, several technical limitations must be acknowledged:

1. **Synthetic-to-real domain gap:** Although our demographic engine models Vietnamese onomastic structures, administrative jurisdictions, and 19 scenario archetypes across three registers, synthetic text cannot fully duplicate the stylistic noise, typos, scan artifacts, and irregular formatting encountered in real-world administrative paper trails. Future research must evaluate model resilience against real-world scanned documents with OCR errors.
2. **Focus on formal and semi-formal registers:** ViPII intentionally concentrates on administrative, legal, medical, and consultative interactions where Decree 13 compliance is most critical. It does not comprehensively cover informal conversational text, social media slang (*teencode*), or regional colloquialisms common in unregulated online communication.
3. **Complex multi-party narrative disambiguation:** When documents recount intricate multi-party disputes involving numerous relatives with shared family names, compact SLMs occasionally struggle to disambiguate which attributes belong to the primary citizen versus secondary third parties.
4. **Regulatory scope boundary:** The ViPII legal taxonomy operationalizes the 34 statutory attributes defined in Articles 2–4 of Decree 13. However, legal compliance in production systems involves broader organizational, technical, and governance requirements beyond text-level masking. Achieving high performance on ViPII is a necessary technical capability, but does not by itself constitute legal certification under Vietnamese law.

---

## 8.3. Reproducibility and Artifact Release

To facilitate rigorous peer review, encourage independent verification, and advance open privacy research for low-resource languages, we commit to releasing all artifacts under open research licenses:

1. **Codebase and synthesis pipeline:** The complete decoupled synthesis framework, programmatic profile manifests, deterministic calibrators, cue-windowing algorithms, and evaluation harnesses will be published on GitHub under the permissive Apache 2.0 license.
2. **Evaluation benchmark:** The standardized 4,000-document held-out test partition, complete with character-level ground-truth annotations and metric evaluation scripts (`SanRec`, `RetRec`, `FULL`), will be released on the Hugging Face Datasets hub.
3. **Trained model checkpoints:** Fine-tuned model checkpoints for `qwen3-0.6b (FT)`, `qwen3-1.7b (FT)`, and `qwen3.5-0.8b (FT)`, along with quantization scripts for INT4 edge deployment, will be hosted on Hugging Face under open research access.
4. **Experimental configuration:** Exact training hyperparameters, seed configurations, prompt templates, and hardware specifications are documented to ensure that all experimental findings reported in Sections 6 and 7 can be independently reproduced.
