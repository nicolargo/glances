#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""JWT utilities for Glances REST API authentication."""

import secrets
from datetime import datetime, timedelta, timezone

from glances.logger import logger

# JWT library import with fallback
try:
    from jose import JWTError, jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTError = Exception  # Placeholder


class JWTHandler:
    """Handle JWT token creation and validation."""

    # Algorithm for JWT signing
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str | None = None, expire_minutes: int = 60):
        """Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens. If None, generates a random key.
            expire_minutes: Token expiration time in minutes (default: 60)
        """
        if not JWT_AVAILABLE:
            logger.warning("python-jose library not available. JWT authentication disabled.")
            self._secret_key = None
        else:
            # Use provided key or generate a secure random key
            self._secret_key = secret_key or secrets.token_urlsafe(32)
            if secret_key is None:
                logger.info("JWT secret key generated (valid for this server instance only)")

        self._expire_minutes = expire_minutes

    @property
    def is_available(self) -> bool:
        """Check if JWT functionality is available."""
        return JWT_AVAILABLE and self._secret_key is not None

    @property
    def expire_minutes(self) -> int:
        """Return the token expiration time in minutes."""
        return self._expire_minutes

    def create_access_token(self, username: str) -> str:
        """Create a JWT access token for the given username.

        Args:
            username: The username to encode in the token

        Returns:
            Encoded JWT token string

        Raises:
            RuntimeError: If JWT is not available
        """
        if not self.is_available:
            raise RuntimeError("JWT authentication is not available")

        expire = datetime.now(timezone.utc) + timedelta(minutes=self._expire_minutes)
        to_encode = {
            "sub": username,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": "glances",
        }
        return jwt.encode(to_encode, self._secret_key, algorithm=self.ALGORITHM)

    def verify_token(self, token: str) -> str | None:
        """Verify a JWT token and extract the username.

        Args:
            token: The JWT token to verify

        Returns:
            Username if valid, None otherwise
        """
        if not self.is_available:
            return None

        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return None
            return username
        except JWTError as e:
            logger.debug(f"JWT verification failed: {e}")
            return None
