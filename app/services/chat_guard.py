import re
from fastapi import HTTPException

# Regex for UPI VPAs (e.g. name@upi, 9876543210@ybl, astro@okaxis)
UPI_REGEX = re.compile(r'[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}', re.IGNORECASE)

# Regex for Indian 10-digit mobile numbers (e.g. +91 9876543210, 98765-43210, 9876543210)
PHONE_REGEX = re.compile(r'(\+?91[\-\s]?)?[6-9]\d{9}|\b[6-9]\d{4}[\s\-.]?\d{5}\b', re.IGNORECASE)

# Regex for URLs / External Payment Links
URL_REGEX = re.compile(r'(https?://|www\.|wa\.me|t\.me|paytm\.me|razorpay\.me|upi://)', re.IGNORECASE)

# Forbidden keywords related to personal payment bypass & scanners
FORBIDDEN_KEYWORDS = [
    "scan qr", "scanner", "gpay number", "google pay number", "paytm number",
    "phonepe number", "my upi", "personal qr", "send money directly", "pay outside",
    "personal scanner", "scan this qr", "scanner pic", "scanner photo", "direct pay",
    "bhim upi number"
]


def validate_chat_message(text: str) -> str:
    """
    Validates a chat message for off-platform payment bypass, personal UPI IDs,
    phone numbers, external links, and scanner requests.
    Raises HTTPException (status 400) if a violation is detected.
    """
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        return cleaned_text

    lower_text = cleaned_text.lower()

    # 1. Check UPI ID
    if UPI_REGEX.search(cleaned_text):
        raise HTTPException(
            status_code=400,
            detail="Security Violation: Sharing personal UPI IDs in chat is strictly prohibited. All payments must go through the official platform payment button."
        )

    # 2. Check Phone Number
    if PHONE_REGEX.search(cleaned_text):
        raise HTTPException(
            status_code=400,
            detail="Security Violation: Sharing phone numbers in chat is not allowed for user & astrologer safety."
        )

    # 3. Check External Links
    if URL_REGEX.search(cleaned_text):
        raise HTTPException(
            status_code=400,
            detail="Security Violation: External payment links or web URLs are strictly prohibited in chat."
        )

    # 4. Check Scanner & Payment Keywords
    for kw in FORBIDDEN_KEYWORDS:
        if kw in lower_text:
            raise HTTPException(
                status_code=400,
                detail=f"Security Violation: Phrase '{kw}' flagged. Sharing personal payment scanners or requesting direct payment is strictly prohibited."
            )

    return cleaned_text
