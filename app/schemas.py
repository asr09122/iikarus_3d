from pydantic import BaseModel
from typing import Optional, List

class ProductCard(BaseModel):
    id: str
    title: str
    main_image: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[float] = None
    score: float

class ProductDetail(BaseModel):
    id: str
    title: str
    brand: Optional[str] = None
    price: Optional[float] = None
    main_category: Optional[str] = None
    categories: Optional[str] = None
    material: Optional[str] = None
    color: Optional[str] = None
    main_image: Optional[str] = None
    images: Optional[List[str]] = None
    description: Optional[str] = None
    creative_description: str  # always returned fresh

class SearchRequest(BaseModel):
    query: str
    top_k: int = 12
    candidate_k: int = 30
    must_contain: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[ProductCard]
