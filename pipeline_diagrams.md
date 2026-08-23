# SecurePrep: Detailed Architectural and Workflow Diagrams

This document contains simplified, grouped, and print-friendly visual flowcharts for the **SecurePrep** framework. Following professional graphic design and publication standards (such as IEEE, Elsevier, and Springer), all diagrams use a consistent color-coded scheme designed for high contrast on light backgrounds:
*   **Blue nodes (`fill:#E3F2FD`, `stroke:#1565C0`, `color:#0D47A1`)**: System processes and algorithms.
*   **Yellow nodes (`fill:#FFFDE7`, `stroke:#FBC02D`, `color:#F57F17`)**: Decisions and branching logic.
*   **White nodes (`fill:#FFFFFF`, `stroke:#757575`, `color:#212121`)**: Input/output datasets, databases, and files.
*   **Indigo nodes (`fill:#E8EAF6`, `stroke:#3949AB`, `color:#1A237E`)**: Large Language Models (LLMs) and downstream neural network architectures.

All code filenames (such as `build_profiles.py` and `annotation.py`) have been removed from the nodes and replaced with descriptive method names.

---

## Fig. 1: Overall System Architecture of SecurePrep

This diagram represents the high-level decoupled stages of the framework, showing the flow from seeds through generation and calibration to downstream evaluation.

```mermaid
graph LR
    %% Style Definitions
    classDef process fill:#E3F2FD,stroke:#1565C0,stroke-width:1.5px,color:#0D47A1,font-size:13px;
    classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:1.5px,color:#F57F17,font-size:13px;
    classDef io fill:#FFFFFF,stroke:#757575,stroke-width:1.5px,color:#212121,font-size:13px;
    classDef model fill:#E8EAF6,stroke:#3949AB,stroke-width:1.5px,color:#1A237E,font-size:13px;

    %% Nodes
    A1["Demographic & Sovereign Seeds"]:::io --> B1["Profile Bank Builder"]:::process
    B1 --> B2["70,000 Profile Bank"]:::io
    B2 --> B3["Template-Driven Document Synthesizer"]:::process
    B3 --> B4["Delimited Raw Documents"]:::io
    B4 --> C1["3-Layer Calibration & Overlap Resolver"]:::process
    C1 --> C2["Calibrated BIO Dataset"]:::io
    C2 --> D1["Downstream Model Training<br>(PhoBERT-CRF / XLM-R-CRF)"]:::model
    D1 --> D2["Empirical & Statutory Evaluation"]:::process
```

---

## Fig. 2: Profile Bank Generation & Document Synthesis Workflow

This diagram combines Stage 1 (Profile Generation) and Stage 2 (Document Synthesis) into two vertically stacked, horizontal subgraphs. Minor steps are grouped into high-level sub-processes to keep the layout compact and prevent over-stretching.

```mermaid
graph TD
    %% Style Definitions
    classDef process fill:#E3F2FD,stroke:#1565C0,stroke-width:1.5px,color:#0D47A1,font-size:12px;
    classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:1.5px,color:#F57F17,font-size:12px;
    classDef io fill:#FFFFFF,stroke:#757575,stroke-width:1.5px,color:#212121,font-size:12px;
    classDef model fill:#E8EAF6,stroke:#3949AB,stroke-width:1.5px,color:#1A237E,font-size:12px;

    %% STAGE 1: PROFILE BANK GENERATION
    subgraph Stage1 ["Stage 1: 70,000 Profile Bank Generation"]
        direction LR
        P1["Generate Raw Demographic Attributes<br>(Sample birth date, year, gender, ethnicity)"]:::process --> P2["Ethnic-Specific Naming Realizer<br>(Apply Kinh / Ê Đê / Gia Rai naming rules)"]:::process
        P2 --> P3["Hierarchical Address Synthesizer<br>(Resolution 202/2025/QH15)"]:::process
        P3 --> P4{"Address Format?"}:::decision
        P4 -- "82%" --> P5_New["Modern 2-Tier Address"]:::process
        P4 -- "18%" --> P5_Old["Legacy 3-Tier Address"]:::process
        P5_New & P5_Old --> P6["Deterministic Identifier Calibration<br>(CCCD, GPLX, NAPAS, Plates & Phone)"]:::process
        P6 --> P7["k-Anonymity & Consistency Check"]:::process
        P7 --> P8[("profile_bank.jsonl")]:::io
    end

    %% STAGE 2: DOCUMENT SYNTHESIS
    subgraph Stage2 ["Stage 2: Template-Driven Document Synthesis"]
        direction LR
        S1[("form.json<br>- 9,020 Crawled Forms")]:::io
        S2[("scenario_catalog.json<br>- 24 Scenarios")]:::io
        
        S1 & S2 & P8 --> S3["Form & Scenario Template Ingestion<br>(Layout seed mode: reuse / synthetic)"]:::process
        S3 --> S4["Active Constraint & Manifest Assembly<br>(Select active fields & render surface variations)"]:::process
        S4 --> S5["Decomposed Multi-Stage Prompting<br>(Generate Outline, Draft, and Revision Prompts)"]:::process
        S5 --> S6["LLM Prose Realization<br>(Embed lightweight SPI tags in context)"]:::model
    end

    %% Vertical connection between Stage 1 and Stage 2
    Stage1 --> Stage2
```

---

## Fig. 3: Granular 3-Layer Calibration & Overlap Resolution Workflow

This flowchart details how raw generated documents are parsed by the 3-layer engine and resolved for Flat NER overlap conflicts.

```mermaid
graph TD
    %% Style Definitions
    classDef process fill:#E3F2FD,stroke:#1565C0,stroke-width:1.5px,color:#0D47A1,font-size:12px;
    classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:1.5px,color:#F57F17,font-size:12px;
    classDef io fill:#FFFFFF,stroke:#757575,stroke-width:1.5px,color:#212121,font-size:12px;
    classDef model fill:#E8EAF6,stroke:#3949AB,stroke-width:1.5px,color:#1A237E,font-size:12px;

    %% Row 1: Regularization & Core Stack Parser
    R1["Raw Generated Document"]:::io --> R2["Tag Syntax Regularization & Stack Parsing"]:::process
    
    %% Parallel Outputs
    R2 --> T1["Clean Text Buffer T"]:::io
    R2 --> T2["Layer 3 Accepted Spans (SPI)"]:::io
    
    %% Row 2: Parallel Matchers
    T1 --> L1["Layer 1: Guarded Regex Matcher<br>(Extract structured PII credentials)"]:::process
    T1 --> L2["Layer 2: Cue-Context Lookback Window<br>(Disambiguate soft categorical PII)"]:::process
    
    L1 --> S1["Guarded Verbatim PII Spans"]:::io
    L2 --> S2["Disambiguated PII Spans"]:::io
    
    %% Row 3: Overlap resolution vertical pipeline
    T2 & S1 & S2 --> M1["Priority-Based Greedy Overlap Resolver<br>(Enforce Flat NER constraint using span length)"]:::process
    M1 --> M2["Post-Hoc Name Splitter & Calibration<br>(Decompose macro full name to family/middle/given)"]:::process
    M2 --> M3["Final Calibrated BIO Dataset"]:::io
```

---

## Fig. 4: Downstream Model Training & Evaluation Pipeline

This diagram maps out the downstream model training process. It arranges the sequential preprocessing, encoding, and decoding steps in a vertical pipeline, and branches the final evaluation metrics horizontally to optimize space.

```mermaid
graph TD
    %% Style Definitions
    classDef process fill:#E3F2FD,stroke:#1565C0,stroke-width:1.5px,color:#0D47A1,font-size:12px;
    classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:1.5px,color:#F57F17,font-size:12px;
    classDef io fill:#FFFFFF,stroke:#757575,stroke-width:1.5px,color:#212121,font-size:12px;
    classDef model fill:#E8EAF6,stroke:#3949AB,stroke-width:1.5px,color:#1A237E,font-size:12px;

    %% Main Vertical Sequence
    A1["Calibrated BIO Dataset"]:::io --> A2["Subword Tokenization & Offset Alignment"]:::process
    A2 --> A3["Transformer Encoder & CRF Transition Layer<br>(PhoBERT-CRF / XLM-RoBERTa-CRF)"]:::model
    A3 --> A4["Viterbi Decoding & Loss Backpropagation"]:::process
    
    %% Horizontal Branching at the bottom for evaluation metrics
    A4 --> A5_Metrics["Empirical & Statutory Evaluation<br>- Sliding window MATTR (w=100)<br>- TF-IDF Vendi Score<br>- Statutory Ratio check (PII/SPI)"]:::process
    A4 --> A5_Output["Statutory De-Identified Output Documents"]:::io
```
