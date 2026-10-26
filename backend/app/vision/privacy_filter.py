import re
from typing import Tuple, List, Optional
from .vision_schemas import OcrResult, OcrLine, OcrWord

# Regex patterns for sensitive credentials, secrets, and PII
SENSITIVE_PATTERNS = [
    # API Keys & Cloud Tokens
    (re.compile(r'\b(AIza[0-9A-Za-z-_]{20,45})\b', re.IGNORECASE), "[REDACTED_API_KEY]"),
    (re.compile(r'\b(sk-[a-zA-Z0-9]{20,48})\b'), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r'\b(ghp_[a-zA-Z0-9]{36})\b'), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r'\b(glpat-[a-zA-Z0-9\-_]{20,})\b'), "[REDACTED_GITLAB_TOKEN]"),
    (re.compile(r'\b(AKIA[0-9A-Z]{16})\b'), "[REDACTED_AWS_KEY]"),
    (re.compile(r'\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b'), "[REDACTED_SLACK_TOKEN]"),
    # JWT Tokens (header.payload.signature)
    (re.compile(r'\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'), "[REDACTED_JWT_TOKEN]"),
    # Bearer Authorization headers
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*', re.IGNORECASE), r'\1[REDACTED_AUTH_TOKEN]'),
    # Passwords or secrets in key-value format (e.g. password = "xyz" or password: 'xyz')
    (re.compile(r'((?:password|passwd|secret|api_key|token|auth_token)\s*[:=]\s*)(?:["\']([^"\']+)["\']|([^\s;,]+))', re.IGNORECASE), r'\1[REDACTED_SECRET]'),
    # Credit Card numbers (Luhn/standard 13-19 digits formatted)
    (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), "[REDACTED_CARD_NUMBER]"),
    # Private Key blocks
    (re.compile(r'-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY[^-]*-----', re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
]

# Sensitive window processes and title keywords
SENSITIVE_PROCESSES = {
    "1password.exe", "1password",
    "bitwarden.exe", "bitwarden",
    "keepass.exe", "keepassxc.exe", "keepass", "keepassxc",
    "lastpass.exe", "lastpass",
    "dashlane.exe", "dashlane",
    "credentialui.exe", "consent.exe",
    "authy.exe", "authy"
}

SENSITIVE_TITLE_KEYWORDS = [
    "password manager", "bitwarden", "1password", "keepass",
    "authenticator", "credential", "master password", "private key"
]

class PrivacyFilter:
    """
    Enforces privacy and security safeguards for screen captures and OCR extraction:
    - Redacts API keys, passwords, tokens, auth headers, and credit card numbers.
    - Flags sensitive windows (password managers, authenticators, credential prompts).
    """

    @classmethod
    def is_window_sensitive(cls, title: str, process_name: str) -> bool:
        """
        Determines whether a window or process contains sensitive security information.
        """
        if process_name and process_name.lower() in SENSITIVE_PROCESSES:
            return True
        title_lower = (title or "").lower()
        for kw in SENSITIVE_TITLE_KEYWORDS:
            if kw in title_lower:
                return True
        return False

    @classmethod
    def redact_text(cls, text: str) -> Tuple[str, int]:
        """
        Redacts any sensitive tokens/credentials found in the provided text.
        Returns (redacted_text, count_of_redactions).
        """
        if not text:
            return "", 0
        
        redacted = text
        total_redactions = 0

        for pattern, replacement in SENSITIVE_PATTERNS:
            matches = list(pattern.finditer(redacted))
            if matches:
                total_redactions += len(matches)
                redacted = pattern.sub(replacement, redacted)

        return redacted, total_redactions

    @classmethod
    def sanitize_ocr_result(cls, ocr_result: OcrResult) -> OcrResult:
        """
        Applies privacy filtering to all lines, words, and text in an OcrResult.
        """
        full_text, count1 = cls.redact_text(ocr_result.full_text)
        structured_text, count2 = cls.redact_text(ocr_result.structured_text)
        
        sanitized_lines: List[OcrLine] = []
        line_redactions = 0

        for line in ocr_result.lines:
            redacted_line_text, line_count = cls.redact_text(line.text)
            line_redactions += line_count
            
            sanitized_words: List[OcrWord] = []
            for word in line.words:
                redacted_w, _ = cls.redact_text(word.text)
                sanitized_words.append(OcrWord(
                    text=redacted_w,
                    confidence=word.confidence,
                    x=word.x,
                    y=word.y,
                    width=word.width,
                    height=word.height
                ))
                
            sanitized_lines.append(OcrLine(
                text=redacted_line_text,
                confidence=line.confidence,
                words=sanitized_words,
                x=line.x,
                y=line.y,
                width=line.width,
                height=line.height
            ))

        total_redactions = max(count1, count2, line_redactions)
        
        return OcrResult(
            total_lines=len(sanitized_lines),
            total_words=sum(len(l.words) for l in sanitized_lines),
            full_text=full_text,
            structured_text=structured_text,
            lines=sanitized_lines,
            regions=ocr_result.regions, # Regions can also be sanitized if needed
            confidence=ocr_result.confidence,
            redacted_count=ocr_result.redacted_count + total_redactions,
            duration_ms=ocr_result.duration_ms
        )
