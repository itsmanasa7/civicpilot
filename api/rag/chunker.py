import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Chunk:
    id: str               # e.g., "PMK-G-4.2", "PMK-FAQ-3", "PMK-A-1.1"
    doc_id: str           # Source filename e.g. "guidelines.md"
    title: str            # Clause/section title
    clause_num: str       # E.g., "4.2", "3", "1.1"
    text: str             # Full clause text content


class Chunker:
    """Chunks PM-KISAN markdown/text documents by clause or section and assigns stable IDs."""

    @staticmethod
    def get_doc_prefix(filename: str) -> str:
        lower = filename.lower()
        if "guideline" in lower or "scheme" in lower:
            return "PMK-G"
        if "faq" in lower or "qna" in lower:
            return "PMK-FAQ"
        if "amendment" in lower or "notice" in lower:
            return "PMK-A"
        return "PMK-DOC"

    @classmethod
    def chunk_text(cls, content: str, filename: str) -> List[Chunk]:
        prefix = cls.get_doc_prefix(filename)
        chunks: List[Chunk] = []

        # Split content by markdown headings (e.g. ## or ### or #)
        sections = re.split(r"\n(?=#{1,3}\s+)", content)
        section_idx = 1

        for raw_sec in sections:
            sec = raw_sec.strip()
            if not sec:
                continue

            lines = sec.splitlines()
            first_line = lines[0].strip()

            # Heading line matching (e.g. "## Clause 4.2: Eligibility Criteria" or "## FAQ 3: ...")
            header_text = re.sub(r"^#{1,3}\s*", "", first_line).strip()
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

            # Check for explicit ID comment or tag like <!-- id: PMK-G-4.2 --> or [PMK-G-4.2] or bare PMK-A-1.1
            explicit_id_match = re.search(r"<!--\s*id:\s*([A-Za-z0-9\-\._]+)\s*-->|\[(PMK\-[A-Za-z0-9\-\._]+)\]|\b(PMK\-[A-Za-z0-9\-\._]+)\b", sec)
            if explicit_id_match:
                stable_id = explicit_id_match.group(1) or explicit_id_match.group(2) or explicit_id_match.group(3)
                clause_match = re.search(r"(\d+(?:\.\d+)*)", stable_id)
                clause_num = clause_match.group(1) if clause_match else str(section_idx)
                title = header_text
            else:
                # Look for clause pattern in heading (e.g., "Clause 4.2:", "Clause 4.2", "FAQ 3:", "Amendment 1.1:")
                clause_num_match = re.search(
                    r"(?:clause|section|faq|amendment|rule|para)\s*(\d+(?:\.\d+)*)",
                    header_text,
                    re.IGNORECASE,
                )
                if not clause_num_match:
                    # Look for starting digits e.g. "4.2 Eligibility Criteria"
                    clause_num_match = re.match(r"^(\d+(?:\.\d+)*)", header_text)

                if clause_num_match:
                    clause_num = clause_num_match.group(1)
                else:
                    clause_num = f"{section_idx}.0"

                stable_id = f"{prefix}-{clause_num}"
                title = header_text

            # If body is empty and header contains content, store header as text
            full_text = f"{header_text}\n{body}".strip() if body else header_text

            # Avoid storing document-level title without body (e.g. "# PM-KISAN Operational Scheme Guidelines")
            if not body and first_line.startswith("# ") and len(sections) > 1:
                continue

            chunks.append(
                Chunk(
                    id=stable_id,
                    doc_id=filename,
                    title=title,
                    clause_num=clause_num,
                    text=full_text,
                )
            )
            section_idx += 1

        return chunks

    @classmethod
    def chunk_file(cls, file_path: Path) -> List[Chunk]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        return cls.chunk_text(content, path.name)

    @classmethod
    def chunk_directory(cls, dir_path: Path) -> List[Chunk]:
        path = Path(dir_path)
        if not path.exists():
            return []

        chunks: List[Chunk] = []
        # Find all markdown and text files
        for ext in ("*.md", "*.txt"):
            for file_path in sorted(path.glob(ext)):
                chunks.extend(cls.chunk_file(file_path))
        return chunks
