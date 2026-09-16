from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    preferred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")

class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="store")

class Order(Base):
    __tablename__ = "orders"

    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_number: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    tip_amount: Mapped[float | None] = mapped_column(Float, default=None)  # allow nullable — some orders have no tip yet
    tip_logged: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    store: Mapped["Store"] = relationship(back_populates="orders")
