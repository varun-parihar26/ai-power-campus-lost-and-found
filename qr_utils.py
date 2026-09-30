"""
Generates a QR-code 'claim slip' for a resolved match.
Unique feature: when two items are matched and confirmed, the finder gets a
QR code the claimant shows in person to the lost-and-found desk — the QR
encodes a signed claim token so the desk can verify authenticity at a glance,
instead of relying on someone's word.
"""

import hashlib
import io
import os
import qrcode

SECRET_SALT = os.environ.get("CLAIM_SECRET", "campus-lost-found-secret")


def generate_claim_token(item_id: int, matched_item_id: int) -> str:
    """Deterministic short token so the same pair always produces the same
    verifiable code (no DB column needed to store it separately)."""
    raw = f"{item_id}:{matched_item_id}:{SECRET_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def verify_claim_token(item_id: int, matched_item_id: int, token: str) -> bool:
    return generate_claim_token(item_id, matched_item_id) == token


def generate_qr_image_bytes(item_id: int, matched_item_id: int) -> bytes:
    """Returns PNG bytes of a QR code encoding the claim verification string."""
    token = generate_claim_token(item_id, matched_item_id)
    payload = f"CLAIM|{item_id}|{matched_item_id}|{token}"

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E2A2F", back_color="#F6F3EC")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
