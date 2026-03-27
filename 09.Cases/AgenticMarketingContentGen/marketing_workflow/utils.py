"""Utility helpers for the marketing workflow."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

_JSON_BLOCK_RE = re.compile(r"```(?:json)?(.*?)```", re.DOTALL | re.IGNORECASE)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


def slugify(value: str, *, max_length: int = 60) -> str:
    """Convert arbitrary text into a filesystem-friendly slug."""

    value_ascii = value.strip().lower()
    slug = _NON_ALNUM_RE.sub("-", value_ascii).strip("-")
    if not slug:
        slug = "campaign"
    return slug[:max_length]


def extract_json_object(payload: str) -> str:
    """Best-effort extraction of a JSON object from agent text output.
    
    This function attempts to extract and fix common JSON issues from LLM outputs,
    including:
    - JSON wrapped in markdown code blocks
    - Trailing commas
    - Unescaped control characters
    - Invalid escape sequences
    """

    if not payload:
        raise ValueError("Empty payload cannot be parsed as JSON")

    text = payload.strip()
    fenced_match = _JSON_BLOCK_RE.search(text)
    if fenced_match:
        text = fenced_match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not locate JSON object boundaries in agent output")

    json_str = text[start : end + 1]

    # Try to validate and fix common JSON issues
    json_str = _fix_json_string(json_str)
    
    # Final validation
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON after fixes: {e}")


def _fix_json_string(json_str: str) -> str:
    """Fix common JSON issues in LLM outputs.
    
    Handles:
    - Trailing commas before ] or }
    - Unescaped control characters (newlines, tabs inside strings)
    - Invalid escape sequences (like \效, \s, etc.)
    """
    # Step 1: Try parsing as-is
    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass
    
    # Step 2: Remove trailing commas before ] or }
    fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass
    
    # Step 3: Fix control characters and invalid escape sequences character by character
    # Valid JSON escapes are: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
    VALID_ESCAPE_CHARS = set('"\\bfnrt/')
    # Control characters that need to be escaped in JSON strings
    CONTROL_CHAR_MAP = {
        '\n': '\\n',
        '\r': '\\r', 
        '\t': '\\t',
        '\b': '\\b',
        '\f': '\\f',
    }
    
    result = []
    i = 0
    in_string = False
    
    while i < len(fixed):
        char = fixed[i]
        
        if char == '"':
            # Check if this quote is escaped by counting preceding backslashes
            num_backslashes = 0
            j = len(result) - 1
            while j >= 0 and result[j] == '\\':
                num_backslashes += 1
                j -= 1
            if num_backslashes % 2 == 0:
                in_string = not in_string
            result.append(char)
            i += 1
        elif in_string and char in CONTROL_CHAR_MAP:
            # Real control character inside a string - escape it
            result.append(CONTROL_CHAR_MAP[char])
            i += 1
        elif in_string and ord(char) < 32:
            # Other control characters - use unicode escape
            result.append(f'\\u{ord(char):04x}')
            i += 1
        elif char == '\\' and in_string:
            # We're inside a string and found a backslash
            if i + 1 < len(fixed):
                next_char = fixed[i + 1]
                if next_char == 'u':
                    # Could be \uXXXX - check if valid hex
                    if i + 5 < len(fixed) and all(c in '0123456789abcdefABCDEF' for c in fixed[i+2:i+6]):
                        # Valid unicode escape
                        result.append(fixed[i:i+6])
                        i += 6
                    else:
                        # Invalid \u sequence - escape the backslash
                        result.append('\\\\')
                        i += 1
                elif next_char in VALID_ESCAPE_CHARS:
                    # Valid escape sequence
                    result.append(char)
                    result.append(next_char)
                    i += 2
                else:
                    # Invalid escape - double the backslash to escape it
                    result.append('\\\\')
                    i += 1
            else:
                # Backslash at end of string - escape it
                result.append('\\\\')
                i += 1
        else:
            # Regular character or backslash outside string
            result.append(char)
            i += 1
    
    fixed = ''.join(result)
    
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass
    
    # Step 4: Try with strict=False decoder (allows control chars)
    try:
        decoder = json.JSONDecoder(strict=False)
        decoder.decode(fixed)
        return fixed
    except json.JSONDecodeError:
        pass
    
    # Return the best effort fixed version
    return fixed


def ensure_directory(path: str | Path) -> Path:
    """Create the directory if necessary and return it as a Path."""

    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def dump_json(data: Any, path: Path) -> None:
    """Write JSON to disk with UTF-8 encoding."""

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def timestamp_id() -> str:
    """Return a compact UTC timestamp for folder naming."""

    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")
