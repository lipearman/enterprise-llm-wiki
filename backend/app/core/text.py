import hashlib
import re


def normalize_question(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9ก-๙]+", "-", text.strip().lower())
    return s.strip("-")[:160] or "untitled"
