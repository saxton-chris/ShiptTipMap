from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, UniqueConstraint, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str] = mapped_column(String(500))
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class Stores(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

class Orders(Base):
    __tablename__ = "orders"

    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_number: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    tip_amount: Mapped[float] = mapped_column(Float)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    store: Mapped["Stores"] = relationship(back_populates="orders")
