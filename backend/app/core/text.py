import hashlib
import re
import unicodedata


# Invisible / control characters that break Thai substring matching.
#   ­  SOFT HYPHEN         — websites insert for line-break hints
#   ​  ZERO WIDTH SPACE
#   ‌  ZERO WIDTH NON-JOINER
#   ‍  ZERO WIDTH JOINER
#   ﻿  BOM / ZERO WIDTH NO-BREAK SPACE
#   ⁠  WORD JOINER
# Non-raw string so \uXXXX escapes are interpreted as Unicode code points.
_INVISIBLE_RE = re.compile("[­​‌‍﻿⁠]")


def clean_text(text: str) -> str:
    """Remove invisible/control characters that break Thai substring matching.

    Strips soft hyphens, zero-width spaces, lone surrogates, and other
    characters that websites inject for rendering hints but that corrupt
    text search when the content is stored in the database.
    """
    # 1. Remove known invisible chars
    text = _INVISIBLE_RE.sub("", text)
    # 2. Remove lone surrogates (U+D800–U+DFFF) via UTF-8 round-trip
    #    encode(..., "ignore") drops any code points that can't be
    #    represented in UTF-8, which includes lone surrogates.
    text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    # 3. Normalize to NFC so combining characters are canonical
    try:
        text = unicodedata.normalize("NFC", text)
    except Exception:
        pass
    return text


def normalize_question(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def is_thai(text: str) -> bool:
    """Return True if the text contains Thai characters (Unicode block U+0E00-U+0E7F).

    Uses ord() so it works regardless of source-file or terminal encoding.
    """
    return any(0x0E00 <= ord(c) <= 0x0E7F for c in text)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_slug(text: str) -> str:
    """Convert text to a URL-safe slug, preserving Thai characters."""
    s = ""
    for c in text.strip().lower():
        cp = ord(c)
        if c.isalnum() or (0x0E00 <= cp <= 0x0E7F):
            s += c
        else:
            s += "-"
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:160] or "untitled"
