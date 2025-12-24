"""
Refresh Token Model

This module defines the RefreshToken model for managing JWT refresh tokens.
Refresh tokens allow users to obtain new access tokens without re-authenticating,
providing a better user experience while maintaining security.

Security Features:
- Longer expiration (7 days) compared to access tokens (30 minutes)
- Stored in database for validation and revocation
- Automatic cleanup of expired tokens
- One refresh token per user (revokes old token on new login)

Attributes:
    id (int): Primary key, auto-incrementing
    user_id (int): Foreign key to User model
    token (str): The actual refresh token JWT string
    expires_at (datetime): When this refresh token expires
    created_at (datetime): When this token was created
    revoked (bool): Whether this token has been manually revoked

Usage:
    # Create new refresh token on login
    refresh_token = RefreshToken(
        user_id=user.id,
        token=encoded_jwt,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(refresh_token)
    db.commit()

    # Validate refresh token
    token_record = db.query(RefreshToken).filter(
        RefreshToken.token == token,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

Author: Security Hardening Initiative
Created: 2025-12-17
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from Database.session import Base


class RefreshToken(Base):
    """
    Refresh Token Model - Manages long-lived refresh tokens for JWT authentication.

    Refresh tokens allow users to obtain new access tokens without entering credentials.
    They are stored in the database to allow server-side revocation and validation.
    """
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    # Relationship to User model
    user = relationship("User", back_populates="refresh_tokens")

    # Composite index for common query pattern
    __table_args__ = (
        Index('idx_refresh_token_lookup', 'token', 'revoked', 'expires_at'),
    )

    def is_valid(self) -> bool:
        """
        Check if this refresh token is valid.

        Returns:
            bool: True if token is not revoked and not expired, False otherwise
        """
        return not self.revoked and self.expires_at > datetime.utcnow()

    def revoke(self) -> None:
        """Mark this refresh token as revoked."""
        self.revoked = True

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, valid={self.is_valid()})>"
