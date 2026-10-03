# -*- coding: utf-8 -*-
"""
Script to evaluate comprehensive dataset statistics and algorithmic metrics
for a generated text dataset (SecurePrep dataset format).
"""

import json
import re
import argparse
import sys
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def tokenize(text):
    """
    Cleans text and tokenizes it into syllables/words (Vietnamese-friendly).
    """
    return re.findall(r'\w+', text.lower(), re.UNICODE)

def calculate_mattr(tokens, window_size=100):
    """
    Calculates the Moving Average Type-Token Ratio (MATTR).
    """
    n = len(tokens)
    if n == 0:
        return 0.0
    if n < window_size:
        return len(set(tokens)) / n
    
    ttr_sum = 0.0
    num_windows = n - window_size + 1
    for i in range(num_windows):
        window = tokens[i : i + window_size]
        ttr_sum += len(set(window)) / window_size
    return ttr_sum / num_windows

def calculate_vendi_score(texts, sample_size=1000):
    """
    Calculates the Vendi Score using TF-IDF and Cosine Similarity.
    """
    n = len(texts)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    
    if n > sample_size:
        np.random.seed(42)
        indices = np.random.choice(n, sample_size, replace=False)
        texts = [texts[i] for i in indices]
        n = sample_size

    vectorizer = TfidfVectorizer()
    embeddings = vectorizer.fit_transform(texts).toarray()
    K = cosine_similarity(embeddings)
    eigenvalues = np.linalg.eigvalsh(K / n)
    eigenvalues = eigenvalues[eigenvalues > 1e-10]
    entropy = -np.sum(eigenvalues * np.log(eigenvalues))
    vendi_score = np.exp(entropy)
    return float(vendi_score)

def main():
    parser = argparse.ArgumentParser(description="Evaluate Dataset Statistics & Algorithmic Metrics")
    parser.add_argument("--input", "-i", type=str, default="3-7-2026/output/dataset.jsonl",
                        help="Path to the dataset .jsonl file")
    parser.add_argument("--window", "-w", type=int, default=100,
                        help="Sliding window size for MATTR (default: 100)")
    parser.add_argument("--sample", "-s", type=int, default=1000,
                        help="Maximum sample size for Vendi Score (default: 1000)")
    parser.add_argument("--output", "-o", type=str, default="3-7-2026/output/dataset_statistics_report.json",
                        help="Path to save the JSON report")
    
    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' does not exist.")
        sys.exit(1)
        
    print(f"Loading dataset from '{input_path}'...")
    records = []
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                    
    total_docs = len(records)
    print(f"Loaded {total_docs} records.")
    
    if total_docs == 0:
        print("Error: No valid documents found.")
        sys.exit(1)
        
    # Extracted fields
    texts = []
    mattr_scores = []
    char_lengths = []
    word_lengths = []
    
    total_spans_count = 0
    annotated_chars_count = 0
    total_chars_count = 0
    
    field_counts = Counter()
    label_counts = Counter()
    
    tag_ok_count = 0
    full_coverage_count = 0
    missing_fields_counter = Counter()
    
    for r in records:
        content = r.get("content", "")
        texts.append(content)
        
        # Lengths
        char_len = len(content)
        tokens = tokenize(content)
        word_len = len(tokens)
        
        char_lengths.append(char_len)
        word_lengths.append(word_len)
        total_chars_count += char_len
        
        # MATTR
        mattr = calculate_mattr(tokens, window_size=args.window)
        mattr_scores.append(mattr)
        
        # Spans (Annotations)
        spans = r.get("spans", [])
        total_spans_count += len(spans)
        for s in spans:
            field_counts[s.get("field")] += 1
            label_counts[s.get("label")] += 1
            span_len = s.get("end", 0) - s.get("start", 0)
            annotated_chars_count += max(0, span_len)
            
        # Metadata Quality
        meta = r.get("meta", {})
        if meta.get("tag_ok") is True:
            tag_ok_count += 1
            
        miss = meta.get("missing_coverage", [])
        if not miss:
            full_coverage_count += 1
        else:
            for m_fld in miss:
                missing_fields_counter[m_fld] += 1
                
    # Averages & Statistics
    avg_char_len = np.mean(char_lengths)
    avg_word_len = np.mean(word_lengths)
    
    avg_mattr = np.mean(mattr_scores)
    vendi_score = calculate_vendi_score(texts, sample_size=args.sample)
    
    avg_spans_per_doc = total_spans_count / total_docs
    span_char_density = (annotated_chars_count / total_chars_count) * 100 if total_chars_count > 0 else 0.0
    spans_per_100_words = (total_spans_count / sum(word_lengths)) * 100 if sum(word_lengths) > 0 else 0.0
    
    tag_ok_rate = (tag_ok_count / total_docs) * 100
    full_coverage_rate = (full_coverage_count / total_docs) * 100
    
    # Structure Results
    results = {
        "dataset_name": input_path.name,
        "total_documents": total_docs,
        "text_statistics": {
            "avg_char_length": float(avg_char_len),
            "avg_word_length": float(avg_word_len),
            "min_word_length": int(np.min(word_lengths)),
            "max_word_length": int(np.max(word_lengths))
        },
        "diversity_metrics": {
            "mattr_window_size": args.window,
            "avg_mattr": float(avg_mattr),
            "vendi_score": vendi_score,
            "vendi_diversity_ratio": float(vendi_score / total_docs)
        },
        "annotation_density": {
            "total_annotations": total_spans_count,
            "avg_annotations_per_doc": float(avg_spans_per_doc),
            "span_character_density_percent": float(span_char_density),
            "annotations_per_100_words": float(spans_per_100_words)
        },
        "generation_quality": {
            "tag_ok_percentage": float(tag_ok_rate),
            "full_coverage_percentage": float(full_coverage_rate),
            "most_frequently_missed_fields": dict(missing_fields_counter.most_common(10))
        },
        "entity_type_distribution": dict(field_counts),
        "label_distribution": dict(label_counts)
    }
    
    # Save Report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    # Print Console Report
    print("\n" + "=" * 60)
    print("         DATASET ALGORITHMIC STATS REPORT")
    print("=" * 60)
    print(f"Dataset:                  {results['dataset_name']}")
    print(f"Total Documents:          {results['total_documents']}")
    print(f"Avg Length:               {avg_word_len:.1f} words / {avg_char_len:.1f} chars")
    
    print("-" * 60)
    print("DIVERSITY:")
    print(f"  Avg MATTR (w={args.window}):      {avg_mattr:.4f}")
    print(f"  Vendi Score:            {vendi_score:.4f} (~{results['diversity_metrics']['vendi_diversity_ratio']*100:.1f}% ratio)")
    
    print("-" * 60)
    print("ANNOTATION DENSITY:")
    print(f"  Total Annotations:      {total_spans_count}")
    print(f"  Avg Spans / Doc:        {avg_spans_per_doc:.2f}")
    print(f"  Span Char Density:      {span_char_density:.2f}% (ratio of annotated chars)")
    print(f"  Spans / 100 Words:      {spans_per_100_words:.2f}")
    
    print("-" * 60)
    print("GENERATION PIPELINE QUALITY:")
    print(f"  Tag Bal. Success Rate:  {tag_ok_rate:.2f}% (tag_ok=True)")
    print(f"  Field Coverage Rate:    {full_coverage_rate:.2f}% (no missing_coverage)")
    if missing_fields_counter:
        print("  Top Missed Fields:")
        for fld, cnt in missing_fields_counter.most_common(5):
            print(f"    - {fld}: {cnt} times")
            
    print("-" * 60)
    print("LABEL DISTRIBUTION:")
    for lbl, cnt in label_counts.items():
        print(f"  - {lbl}: {cnt} ({cnt/total_spans_count*100:.1f}%)")
        
    print("-" * 60)
    print("TOP 10 ENTITY FIELDS:")
    for fld, cnt in field_counts.most_common(10):
        print(f"  - {fld:<20}: {cnt} ({cnt/total_spans_count*100:.1f}%)")
    print("=" * 60)
    print(f"Report saved to: {output_path}\n")

if __name__ == "__main__":
    main()
