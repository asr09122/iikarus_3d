from sqlalchemy import Column, String, Float, Text
from sqlalchemy.types import JSON
from .db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    brand = Column(String, index=True)
    price = Column(Float, nullable=True)
    main_category = Column(String, nullable=True)
    categories = Column(Text, nullable=True)
    material = Column(String, nullable=True)
    color = Column(String, nullable=True)

    # Images
    main_image = Column(Text, nullable=True)   # hero image for card/detail
    images = Column(JSON, nullable=True)       # list[str] gallery (may include main)

    # Content
    description = Column(Text, nullable=True)
    # NOTE: no creative_description column because we always generate fresh
