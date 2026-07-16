from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuthProviderType, UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    wallet_address: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    auth_provider: Mapped[AuthProviderType] = mapped_column(
        Enum(AuthProviderType), default=AuthProviderType.WALLET
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="users")  # noqa: F821
