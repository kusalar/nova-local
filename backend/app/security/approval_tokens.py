import time
import hmac
import hashlib
import secrets
import json
import base64
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nova.security.tokens")

class ApprovalTokenManager:
    """
    Manages single-use, cryptographically signed, short-lived approval tokens
    bound to specific operations. Invalidates all tokens automatically on restart.
    """

    def __init__(self, default_ttl: int = 300):
        # Ephemeral per-session secret: any tokens generated in a previous session
        # are immediately invalid after restart.
        self._session_secret: bytes = secrets.token_bytes(32)
        self.default_ttl = default_ttl
        self._consumed_token_hashes: set = set()

    def _hash_payload(self, payload: Optional[Dict[str, Any]]) -> str:
        if not payload:
            return "empty"
        try:
            serialized = json.dumps(payload, sort_keys=True)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        except Exception:
            return "hash_error"

    def generate_token(
        self,
        action_type: str,
        target_id: str,
        payload: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Generates a signed, single-use approval token bound to action_type, target_id,
        and payload hash.
        """
        ttl = ttl_seconds or self.default_ttl
        expiry = time.time() + ttl
        payload_hash = self._hash_payload(payload)

        token_data = {
            "act": action_type,
            "tgt": target_id,
            "ph": payload_hash,
            "exp": expiry,
            "nonce": secrets.token_hex(8)
        }

        token_json = json.dumps(token_data, separators=(",", ":"))
        token_b64 = base64.urlsafe_b64encode(token_json.encode("utf-8")).decode("utf-8").rstrip("=")

        # Compute HMAC signature using ephemeral session secret
        sig = hmac.new(self._session_secret, token_b64.encode("utf-8"), hashlib.sha256).hexdigest()

        return f"appr_{token_b64}.{sig}"

    def verify_and_consume_token(
        self,
        token: str,
        expected_action_type: str,
        expected_target_id: str,
        expected_payload: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validates token signature, expiration, bound parameters, and single-use status.
        If valid, marks token as consumed and returns True.
        """
        if not token or not token.startswith("appr_"):
            logger.warning("Invalid token format.")
            return False

        try:
            raw_token = token[5:]
            parts = raw_token.split(".")
            if len(parts) != 2:
                return False

            token_b64, provided_sig = parts

            # 1. Verify HMAC signature
            expected_sig = hmac.new(
                self._session_secret, token_b64.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(provided_sig, expected_sig):
                logger.warning("Approval token signature mismatch.")
                return False

            # 2. Check if already consumed (single-use constraint)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            if token_hash in self._consumed_token_hashes:
                logger.warning(f"Approval token '{token_hash[:8]}' has already been used.")
                return False

            # 3. Decode payload
            padding = "=" * ((4 - len(token_b64) % 4) % 4)
            token_json = base64.urlsafe_b64decode((token_b64 + padding).encode("utf-8")).decode("utf-8")
            data = json.loads(token_json)

            # 4. Check expiration
            expiry = data.get("exp", 0)
            if time.time() > expiry:
                logger.warning(f"Approval token expired at {expiry} (current: {time.time()}).")
                return False

            # 5. Check bound action and target
            if data.get("act") != expected_action_type:
                logger.warning(f"Token action mismatch: expected '{expected_action_type}', got '{data.get('act')}'.")
                return False

            if data.get("tgt") != expected_target_id:
                logger.warning(f"Token target mismatch: expected '{expected_target_id}', got '{data.get('tgt')}'.")
                return False

            # 6. Check payload hash match if payload provided
            if expected_payload:
                expected_ph = self._hash_payload(expected_payload)
                if data.get("ph") != expected_ph:
                    logger.warning("Token payload hash mismatch. Operation payload was altered after token creation.")
                    return False

            # Mark token as consumed
            self._consumed_token_hashes.add(token_hash)
            logger.info(f"Approval token successfully validated and consumed for {expected_action_type}:{expected_target_id}.")
            return True

        except Exception as e:
            logger.error(f"Error validating approval token: {e}")
            return False

approval_token_manager = ApprovalTokenManager()
