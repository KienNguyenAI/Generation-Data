from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SECTIONS = [
    ROOT / "01_introduction.md",
    ROOT / "02_related_work.md",
    ROOT / "03_task_definition_legal_taxonomy_and_operational_framework.md",
    ROOT / "04_constraint_first_data_synthesis_and_annotation_pipeline.md",
    ROOT / "05_dataset_statistics_and_quality_analysis.md",
    ROOT / "06_experimental_setup.md",
]
EN_OUT = ROOT / "ViPII_full_en.md"
VI_OUT = ROOT / "ViPII_full_vi.md"

def assemble() -> str:
    return "\n\n---\n\n".join(
        path.read_text(encoding="utf-8-sig").strip() for path in SECTIONS
    ) + "\n"

def translate_text(text: str) -> str:
    query = urllib.parse.urlencode(
        {"client": "gtx", "sl": "en", "tl": "vi", "dt": "t", "q": text}
    )
    url = "https://translate.googleapis.com/translate_a/single?" + query
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
            return "".join(part[0] for part in data[0] if part[0])
        except Exception:
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")

PROTECTED = re.compile(
    r"(`[^`\n]+`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$|https?://\S+)",
    re.MULTILINE,
)

def protect(text: str) -> tuple[str, list[str]]:
    values: list[str] = []
    def repl(match: re.Match[str]) -> str:
        values.append(match.group(0))
        return f"ZXQPROTECT{len(values)-1:04d}QXZ"
    return PROTECTED.sub(repl, text), values

def restore(text: str, values: list[str]) -> str:
    for index, value in enumerate(values):
        token = f"ZXQPROTECT{index:04d}QXZ"
        text = text.replace(token, value)
        text = text.replace(token.lower(), value)
        text = re.sub(
            rf"ZXQ\s*PROTECT\s*{index:04d}\s*QXZ",
            lambda _: value,
            text,
            flags=re.IGNORECASE,
        )
    return text

def translate_block(block: str) -> str:
    if not block.strip() or block.strip() == "---":
        return block
    if block.lstrip().startswith("```"):
        return block
    protected, values = protect(block)
    if len(protected) <= 4200:
        return restore(translate_text(protected), values)
    lines = protected.splitlines()
    translated: list[str] = []
    chunk: list[str] = []
    size = 0
    for line in lines:
        if chunk and size + len(line) + 1 > 4000:
            translated.append(translate_text("\n".join(chunk)))
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        translated.append(translate_text("\n".join(chunk)))
    return restore("\n".join(translated), values)

def split_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            if current and not in_fence:
                blocks.append("\n".join(current))
                current = []
            current.append(line)
            in_fence = not in_fence
            if not in_fence:
                blocks.append("\n".join(current))
                current = []
            continue
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            blocks.append("")
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks

def normalize_terms(text: str) -> str:
    replacements = {
        "# Phần 1: Giới thiệu": "# Mục 1: Giới thiệu",
        "# Phần 2: Công việc liên quan": "# Mục 2: Nghiên cứu liên quan",
        "# Phần 2: Nghiên cứu liên quan": "# Mục 2: Nghiên cứu liên quan",
        "# Phần 3:": "# Mục 3:",
        "# Phần 4:": "# Mục 4:",
        "# Phần 5:": "# Mục 5:",
        "# Phần 6:": "# Mục 6:",
        "Vi PII": "ViPII",
        "Qwen 3": "Qwen3",
        "Nghị định số 13/2023/ND-CP": "Nghị định số 13/2023/NĐ-CP",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def main() -> None:
    english = assemble()
    EN_OUT.write_text(english, encoding="utf-8")
    translated: list[str] = []
    for number, block in enumerate(split_blocks(english), start=1):
        translated.append(translate_block(block))
        if number % 25 == 0:
            print(f"translated {number} blocks", flush=True)
    vietnamese = normalize_terms("\n\n".join(translated))
    VI_OUT.write_text(vietnamese, encoding="utf-8")
    print(f"Wrote {EN_OUT.name} and {VI_OUT.name}", flush=True)

if __name__ == "__main__":
    main()
