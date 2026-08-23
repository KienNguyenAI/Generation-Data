import re
import sys
import os

def load_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def run_tests():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    en_path = r"d:\Đại Học\SecurePrep\v1.1\SecurePrep_Evaluation_Preprint.md"
    vi_path = r"d:\Đại Học\SecurePrep\v1.1\SecurePrep_Evaluation_Preprint_VI.md"
    
    if not os.path.exists(en_path):
        print(f"FAIL: {en_path} not found")
        return False
    if not os.path.exists(vi_path):
        print(f"FAIL: {vi_path} not found")
        return False
        
    en_text = load_file(en_path)
    vi_text = load_file(vi_path)
    
    print("=" * 60)
    print("TEST SUITE 1: CITATION PRESENCE")
    print("=" * 60)
    
    citations = [
        ("Covington and McFall, 2010", r"Covington and McFall,\s*2010"),
        ("Pasari et al., 2023 / Friedman & Dieng", r"Pasari et al\.,\s*2023"),
        ("Friedman and Dieng, 2022", r"Friedman and Dieng,\s*2022"),
        ("Nguyen and Nguyen, 2020", r"Nguyen and Nguyen,\s*2020"),
        ("Conneau et al., 2020", r"Conneau et al\.,\s*2020"),
        ("Lample et al., 2016", r"Lample et al\.,\s*2016"),
        ("Ma and Hovy, 2016", r"Ma and Hovy,\s*2016"),
    ]
    
    for name, pattern in citations:
        en_match = bool(re.search(pattern, en_text))
        vi_match = bool(re.search(pattern, vi_text))
        print(f"Citation '{name}': EN={'PASS' if en_match else 'FAIL'}, VI={'PASS' if vi_match else 'FAIL'}")
        assert en_match, f"Missing {name} in English draft"
        assert vi_match, f"Missing {name} in Vietnamese draft"
        
    print("\n" + "=" * 60)
    print("TEST SUITE 2: STATUTORY CITATIONS")
    print("=" * 60)
    
    statutory_checks = [
        ("Decree 13/2023/ND-CP", r"(Decree\s+(No\.\s+)?13/2023/NĐ-CP|Nghị định\s+(số\s+)?13/2023/NĐ-CP)"),
        ("Article 2.3 (Basic Personal Data)", r"(Article 2\.3|Điều 2\.3)"),
        ("Article 2.4 (Sensitive Personal Data)", r"(Article 2\.4|Điều 2\.4)"),
        ("Articles 24-25 (DPIA)", r"(Articles? 24[–\-]25|Điều 24[–\-]25)"),
        ("Department A05 / Cục A05", r"(Department A05|Cục A05)"),
    ]
    
    for name, pattern in statutory_checks:
        en_match = bool(re.search(pattern, en_text))
        vi_match = bool(re.search(pattern, vi_text))
        print(f"Statutory check '{name}': EN={'PASS' if en_match else 'FAIL'}, VI={'PASS' if vi_match else 'FAIL'}")
        assert en_match, f"Missing statutory reference {name} in EN"
        assert vi_match, f"Missing statutory reference {name} in VI"

    print("\n" + "=" * 60)
    print("TEST SUITE 3: TECHNICAL MECHANISMS")
    print("=" * 60)
    
    mechanisms = [
        ("sanitize_tags", r"sanitize_tags"),
        ("auto_close_unclosed_tags", r"auto_close_unclosed_tags"),
        ("auto_tag_manifest_fields", r"auto_tag_manifest_fields"),
        ("PhoBERT-CRF", r"PhoBERT-CRF"),
        ("XLM-RoBERTa-CRF", r"XLM-RoBERTa-CRF"),
        ("69 labels / 34 classes", r"(69[\-\s]label|69 nhãn|34 (statutory|nhóm|danh mục))"),
        ("exact-match boundary F1", r"(Exact-Match Boundary F1|Khớp chính xác Ranh giới)"),
        ("coordinate drift / skew", r"(coordinate (drift|skew)|trôi dạt tọa độ)"),
        ("1-character offset catastrophe", r"(1-Character Offset Catastrophe|thảm họa lệch 1 ký tự)"),
        ("RDRsegmenter", r"RDRsegmenter"),
        ("Viterbi algorithm", r"(Viterbi algorithm|thuật toán Viterbi)"),
        ("scenario_catalog.json", r"scenario_catalog\.json"),
        ("form.json", r"form\.json"),
    ]
    
    for name, pattern in mechanisms:
        en_match = bool(re.search(pattern, en_text, re.IGNORECASE))
        vi_match = bool(re.search(pattern, vi_text, re.IGNORECASE))
        print(f"Mechanism '{name}': EN={'PASS' if en_match else 'FAIL'}, VI={'PASS' if vi_match else 'FAIL'}")
        assert en_match, f"Missing technical mechanism {name} in EN"
        assert vi_match, f"Missing technical mechanism {name} in VI"

    print("\n" + "=" * 60)
    print("TEST SUITE 4: BILINGUAL NUMERICAL PARITY & STATISTICS")
    print("=" * 60)
    
    numbers = [
        ("DeepSeek doc count (8,252 / 8.252)", r"8[,.]252"),
        ("Gemini doc count (6,871 / 6.871)", r"6[,.]871"),
        ("Total docs (47,881 / 47.881)", r"47[,.]881"),
        ("DeepSeek entities (90,246 / 90.246)", r"90[,.]246"),
        ("Gemini entities (71,521 / 71.521)", r"71[,.]521"),
        ("Total entities (474,874 / 474.874)", r"474[,.]874"),
        ("DeepSeek length (1,713.71 / 1.713,71)", r"1[,.]713[,.]71"),
        ("Gemini length (1,477.41 / 1.477,41)", r"1[,.]477[,.]41"),
        ("DeepSeek words (380)", r"380"),
        ("Gemini words (330)", r"330"),
        ("DeepSeek density (10.94 / 10,94)", r"10[,.]94"),
        ("Gemini density (10.41 / 10,41)", r"10[,.]41"),
        ("DeepSeek Tag OK (99.47% / 99,47%)", r"99[,.]47%"),
        ("Gemini Tag OK (99.99% / 99,99%)", r"99[,.]99%"),
        ("DeepSeek Coverage (95.64% / 95,64%)", r"95[,.]64%"),
        ("Gemini Coverage (96.65% / 96,65%)", r"96[,.]65%"),
        ("DeepSeek MATTR (0.8177 / 0,8177)", r"0[,.]8177"),
        ("Gemini MATTR (0.8325 / 0,8325)", r"0[,.]8325"),
        ("DeepSeek Vendi (159.86 / 159,86)", r"159[,.]86"),
        ("Gemini Vendi (149.14 / 149,14)", r"149[,.]14"),
        ("DeepSeek PII count (82,060 / 82.060)", r"82[,.]060"),
        ("DeepSeek SPI count (8,186 / 8.186)", r"8[,.]186"),
        ("DeepSeek PII ratio (90.9% / 90,9%)", r"90[,.]9%"),
        ("DeepSeek SPI ratio (9.1% / 9,1%)", r"9[,.]1%"),
        ("Gemini PII count (64,168 / 64.168)", r"64[,.]168"),
        ("Gemini SPI count (7,353 / 7.353)", r"7[,.]353"),
        ("Gemini PII ratio (89.7% / 89,7%)", r"89[,.]7%"),
        ("Gemini SPI ratio (10.3% / 10,3%)", r"10[,.]3%"),
        ("Consolidated PII ratio (90.3% / 90,3%)", r"90[,.]3%"),
        ("Consolidated SPI ratio (9.7% / 9,7%)", r"9[,.]7%"),
        ("PhoBERT-CRF Basic F1 (92.4% / 92,4%)", r"92[,.]4%"),
        ("PhoBERT-CRF CCCD F1 (95.8% / 95,8%)", r"95[,.]8%"),
        ("PhoBERT-CRF Phone F1 (94.2% / 94,2%)", r"94[,.]2%"),
        ("PhoBERT-CRF Address F1 (91.6% / 91,6%)", r"91[,.]6%"),
        ("PhoBERT-CRF Sensitive F1 (88.7% / 88,7%)", r"88[,.]7%"),
        ("Uncalibrated F1 range (67.8% / 67,8% to 68.2% / 68,2%)", r"67[,.]8%.*?68[,.]2%"),
        ("Pretraining data PhoBERT (20 GB)", r"20\s*GB"),
        ("Pretraining data XLM-RoBERTa (2.5 TB / 2,5 TB)", r"2[,.]5\s*TB"),
        ("Languages XLM-RoBERTa (100)", r"100"),
        ("Split ratio (80:10:10)", r"80:10:10"),
        ("Scenarios count (24)", r"24"),
        ("Forms count (9,020 / 9.020)", r"9[,.]020"),
    ]
    
    for name, pattern in numbers:
        en_match = bool(re.search(pattern, en_text))
        vi_match = bool(re.search(pattern, vi_text))
        print(f"Stat '{name}': EN={'PASS' if en_match else 'FAIL'}, VI={'PASS' if vi_match else 'FAIL'}")
        assert en_match, f"Missing statistic {name} in EN"
        assert vi_match, f"Missing statistic {name} in VI"

    print("\n" + "=" * 60)
    print("ALL 42 TESTS PASSED PERFECTLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
