# -*- coding: utf-8 -*-
"""
Script to evaluate lexical diversity (MATTR) and semantic diversity (Vendi Score)
of a generated text dataset.
"""

import json
import re
import argparse
import sys
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def clean_and_tokenize(text):
    """
    Cleans text and tokenizes it into syllables/words (Vietnamese-friendly).
    """
    # Convert to lowercase and find all word characters (supports Unicode)
    tokens = re.findall(r'\w+', text.lower(), re.UNICODE)
    return tokens

def calculate_mattr(tokens, window_size=100):
    """
    Calculates the Moving Average Type-Token Ratio (MATTR) for a list of tokens.
    """
    n = len(tokens)
    if n == 0:
        return 0.0
    if n < window_size:
        # Fallback to standard TTR for short texts
        return len(set(tokens)) / n
    
    ttr_sum = 0.0
    num_windows = n - window_size + 1
    for i in range(num_windows):
        window = tokens[i : i + window_size]
        ttr_sum += len(set(window)) / window_size
    return ttr_sum / num_windows

def calculate_vendi_score(texts, sample_size=1000):
    """
    Calculates the Vendi Score (diversity metric) of a list of text documents.
    If the document count exceeds sample_size, it takes a random sample to 
    ensure computational efficiency.
    """
    n = len(texts)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    
    # If dataset is too large, sample it to avoid running out of memory during eigvalsh
    if n > sample_size:
        print(f"      (Dataset size {n} exceeds sample limit {sample_size}. Sampling {sample_size} records...)")
        np.random.seed(42)  # For reproducibility
        indices = np.random.choice(n, sample_size, replace=False)
        texts = [texts[i] for i in indices]
        n = sample_size

    # Convert text to TF-IDF vectors
    vectorizer = TfidfVectorizer()
    embeddings = vectorizer.fit_transform(texts).toarray()
    
    # Compute Cosine Similarity Matrix K (size n x n)
    K = cosine_similarity(embeddings)
    
    # Compute eigenvalues of K / n
    # K/n is positive semi-definite, we use eigvalsh (optimized for symmetric matrices)
    eigenvalues = np.linalg.eigvalsh(K / n)
    
    # Clean up extremely small eigenvalues due to numerical precision limits
    eigenvalues = eigenvalues[eigenvalues > 1e-10]
    
    # Calculate Shannon Entropy
    entropy = -np.sum(eigenvalues * np.log(eigenvalues))
    
    # Vendi Score is the exponential of the entropy
    vendi_score = np.exp(entropy)
    return float(vendi_score)

def main():
    parser = argparse.ArgumentParser(description="Evaluate diversity metrics (MATTR & Vendi Score)")
    parser.add_argument("--input", "-i", type=str, default="3-7-2026/output/dataset.jsonl",
                        help="Path to the dataset .jsonl file")
    parser.add_argument("--window", "-w", type=int, default=100,
                        help="Sliding window size for MATTR (default: 100)")
    parser.add_argument("--sample", "-s", type=int, default=1000,
                        help="Maximum sample size for Vendi Score to avoid out-of-memory (default: 1000)")
    parser.add_argument("--output", "-o", type=str, default="3-7-2026/output/evaluation_report.json",
                        help="Path to save the JSON evaluation report")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' does not exist.")
        sys.exit(1)
        
    print(f"Loading dataset from '{input_path}'...")
    texts = []
    
    # Read .jsonl file
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    if "content" in record:
                        texts.append(record["content"])
                except json.JSONDecodeError:
                    continue
                    
    total_docs = len(texts)
    print(f"Loaded {total_docs} documents.")
    
    if total_docs == 0:
        print("Error: No valid documents containing 'content' field were found.")
        sys.exit(1)
        
    # Calculate MATTR for each document
    print(f"Calculating MATTR (window size: {args.window})...")
    mattr_scores = []
    doc_lengths = []
    
    for idx, text in enumerate(texts):
        tokens = clean_and_tokenize(text)
        doc_lengths.append(len(tokens))
        mattr = calculate_mattr(tokens, window_size=args.window)
        mattr_scores.append(mattr)
        
    avg_mattr = np.mean(mattr_scores)
    min_mattr = np.min(mattr_scores)
    max_mattr = np.max(mattr_scores)
    median_mattr = np.median(mattr_scores)
    avg_len = np.mean(doc_lengths)
    
    # Calculate Vendi Score
    print("Calculating Vendi Score...")
    vendi_score = calculate_vendi_score(texts, sample_size=args.sample)
    
    # Prepare results
    results = {
        "dataset": str(input_path),
        "total_documents": total_docs,
        "average_length_tokens": float(avg_len),
        "mattr": {
            "window_size": args.window,
            "average": float(avg_mattr),
            "median": float(median_mattr),
            "min": float(min_mattr),
            "max": float(max_mattr),
        },
        "vendi_score": vendi_score,
    }
    
    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    # Print results report
    print("\n" + "=" * 50)
    print("           DIVERSITY EVALUATION REPORT")
    print("=" * 50)
    print(f"Dataset:              {input_path.name}")
    print(f"Total Documents:      {total_docs}")
    print(f"Avg Document Length:  {avg_len:.1f} tokens")
    print("-" * 50)
    print("LEXICAL DIVERSITY (MATTR):")
    print(f"  Window Size:        {args.window}")
    print(f"  Average MATTR:      {avg_mattr:.4f}")
    print(f"  Median MATTR:       {median_mattr:.4f}")
    print(f"  Min MATTR:          {min_mattr:.4f}")
    print(f"  Max MATTR:          {max_mattr:.4f}")
    print("-" * 50)
    print("SEMANTIC DIVERSITY (Vendi Score):")
    print(f"  Overall Vendi Score: {vendi_score:.4f}")
    print(f"  Effective Diversity Ratio: {vendi_score / total_docs * 100:.2f}% (Vendi Score / Total)")
    print("=" * 50)
    print(f"Report saved to: {output_path}\n")

if __name__ == "__main__":
    main()
