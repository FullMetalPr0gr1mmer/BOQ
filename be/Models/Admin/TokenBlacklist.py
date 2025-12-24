"""
Token Blacklist Model

This module defines the TokenBlacklist model for managing revoked JWT tokens.
When users log out, their access tokens are added to this blacklist to prevent
reuse until they naturally expire.

Security Features:
- Prevents token reuse after logout
- Server-side token invalidation
- Automatic cleanup of expired blacklisted tokens
- Fast lookup with indexed token field

Attributes:
    id (int): Primary key, auto-incrementing
    token (str): The blacklisted JWT access token
    blacklisted_at (datetime): When this token was blacklisted
    expires_at (datetime): When this token naturally expires (for cleanup)

Usage:
    # Blacklist token on logout
    blacklisted_token = TokenBlacklist(
        token=access_token,
        blacklisted_at=datetime.utcnow(),
        expires_at=token_expiry_from_payload
    )
    db.add(blacklisted_token)
    db.commit()

    # Check if token is blacklisted
    is_blacklisted = db.query(TokenBlacklist).filter(
        TokenBlacklist.token == token
    ).first() is not None

    # Cleanup expired tokens (run periodically)
    db.query(TokenBlacklist).filter(
        TokenBlacklist.expires_at < datetime.utcnow()
    ).delete()

Author: Security Hardening Initiative
Created: 2025-12-17
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from Database.session import Base


class TokenBlacklist(Base):
    """
    Token Blacklist Model - Manages revoked JWT access tokens.

    This model stores access tokens that have been revoked (typically on logout)
    to prevent their reuse until they naturally expire.
    """
    __tablename__ = 'token_blacklist'

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Index for cleanup queries
    __table_args__ = (
        Index('idx_blacklist_expires_at', 'expires_at'),
    )

    def __repr__(self):
        return f"<TokenBlacklist(id={self.id}, blacklisted_at={self.blacklisted_at})>"
