# Section 9: Conclusion and Future Work

This paper addressed the dual challenges of statutory personal data protection and utility preservation in Vietnamese administrative language processing. Motivated by the legal mandates of Vietnam's Personal Data Protection Decree (Decree No. 13/2023/NĐ-CP) and the structural deficiencies of existing multilingual PII tools, we introduced **ViPII**, an end-to-end framework encompassing statutory taxonomy formalization, decoupled synthetic data generation, and rigorous empirical evaluation of compact language models for local deployment.

---

## 9.1. Summary of Scientific Contributions

Through systematic methodological design and extensive experimental evaluation, this study establishes four primary findings:

1. **A statutory Vietnamese benchmark:** ViPII formalizes a 34-attribute legal taxonomy distinguishing Basic Personal Data (`PII`) from Sensitive Personal Data (`SPI`) across 51,880 realized documents and 524,655 annotated entity spans, capturing the full linguistic complexity of Vietnamese onomastics, administrative hierarchies, and polysemous lexical homographs.
2. **Elimination of coordinate drift:** By enforcing a strict architectural decoupling between creative natural language generation and host-side spatial coordinate calibration, ViPII proves that programmatic manifests combined with deterministic algorithmic calibrators eliminate index drift and coordinate hallucination by construction, providing 100% boundary fidelity without manual re-annotation.
3. **Dual-objective privacy–utility paradigm:** We demonstrated that effective de-identification cannot be evaluated solely on privacy recall. The ViPII dual-objective metric suite penalizes both residual leakage and destructive over-redaction, establishing a realistic standard where document utility is rigorously preserved alongside sensitive data removal.
4. **Superiority of compact, on-premise SLMs:** Extensive empirical evaluation on a 4,000-document held-out benchmark and a 200-document human evaluation audit demonstrated that specialized compact Small Language Models (`qwen3-1.7b (FT)` and `qwen3-0.6b (FT)`) decisively outperform commercial frontier baselines (`Gemini-3.6-Flash-High`) and open-weight general-purpose models (`DeepSeek-V4-Flash`). Achieving **71.86% FULL** automated document success and **95.5% human-verified leakage-free sanitization**, compact SLMs deliver near-human accuracy while consuming under 3.5 GB VRAM. This proves that high-performance, cost-effective, and fully air-gapped on-premise data sanitization is immediately viable for public administration and healthcare under Article 25 of Decree 13.

---

## 9.2. Future Directions

The resources and findings established by ViPII open several promising avenues for future research:

1. **Multimodal sanitization for scanned administrative records:** Real-world government archives and hospital intake counters process millions of physical, handwritten, or scanned paper forms daily. Extending ViPII to multimodal vision-language models capable of simultaneous layout understanding, OCR error correction, and visual de-identification represents a vital operational next step.
2. **Audio and speech sanitization for public administrative hotlines:** Extending the statutory taxonomy to spoken Vietnamese dialogue streams would enable municipal citizen service hotlines and call centers to sanitize voice recordings in real time prior to secondary quality auditing or storage.
3. **Adaptive online sanitization and continuous feedback loops:** Future work should explore continuous self-updating gateway architectures that employ active learning and human-in-the-loop validation to adaptively detect emerging administrative form templates and slang without requiring full model retraining.
