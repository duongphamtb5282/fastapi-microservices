from enum import IntEnum

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base

from .enum import IntegerEnum


class Status(IntEnum):
    INACTIVE = 0
    ACTIVE = 1
    DELETED = 2


Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(IntegerEnum(Status), nullable=False, default=Status.INACTIVE)


engine = create_engine("sqlite:///:memory:", echo=False, future=True)
Base.metadata.create_all(engine)

with Session(engine) as session:
    u = User(name="Bob", status=Status.ACTIVE)
    session.add(u)
    session.commit()

    u2 = session.query(User).filter_by(name="Bob").one()
    print(u2.status, type(u2.status))  # prints: Status.ACTIVE <enum 'Status'>
