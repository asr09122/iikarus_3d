# app/main.py
import os
import re
import logging
import spacy
from urllib.parse import unquote
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from .db import Base, engine, get_db
from .models import Product
from .schemas import SearchRequest, SearchResponse, ProductCard, ProductDetail
from .pinecone_client import embed_text, query_index
from .deps import add_cors
from .normalize import normalize_listing

# ---------------------------------------------------------
# 🚀 Initialization
# ---------------------------------------------------------
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Furniture Recommendation API", version="3.1.0")
add_cors(app)

# ---------------------------------------------------------
# 🔐 LLM + spaCy Setup (for keyword extraction + creative blurbs)
# ---------------------------------------------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY is missing in environment variables.")

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    model="gpt-4o-mini",
    api_key=OPENROUTER_API_KEY,
    temperature=0.7,
)
desc_prompt = ChatPromptTemplate.from_template(
    "Write a short, creative, under-60-word product blurb for: {title}. "
    "Highlight materials, design vibe, and one specific use-case. Vary the tone each time."
)
description_chain = desc_prompt | llm | StrOutputParser()

# spaCy for keyword extraction
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def extract_keyword(q: str) -> str:
    doc = nlp(q.lower())
    for t in reversed(doc):
        if t.pos_ == "NOUN":
            return t.text
    for t in reversed(doc):
        if t.is_alpha and not t.is_stop:
            return t.text
    return ""

# ---------------------------------------------------------
# 🧹 ID normalization helper (fixes %0A and control chars)
# ---------------------------------------------------------
_CTRL = ''.join(map(chr, list(range(0, 32)) + [127]))
_CTRL_TABLE = str.maketrans('', '', _CTRL)

def _normalize_id(raw: str) -> str:
    """
    Normalize product ID for DB lookup:
      - Strip whitespace, quotes, encoded newlines (%0A/%0D)
      - Decode URL-encoded chars
      - Remove control / zero-width chars
    """
    if raw is None:
        return ""
    s = str(raw).strip().strip('"').strip("'")
    s = re.sub(r'(?:%0A|%0D)+$', '', s, flags=re.IGNORECASE)
    s = unquote(s)
    s = s.replace('\u200b', '').replace('\ufeff', '')
    s = s.translate(_CTRL_TABLE)
    return s.strip()

# ---------------------------------------------------------
# 🩺 Health check
# ---------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------------------------------------
# 🔍 Search Endpoint
# ---------------------------------------------------------
@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    vec = embed_text(req.query)
    res = query_index(vec, top_k=req.candidate_k)
    matches = res.get("matches", []) or []

    key = (req.must_contain or extract_keyword(req.query)).lower() if req.query else None
    cards: List[ProductCard] = []

    for m in matches:
        md = m.get("metadata") or {}
        title = (md.get("title") or "Untitled").strip()
        if key and key not in title.lower():
            continue

        cards.append(ProductCard(
            id=m["id"],
            title=title,
            main_image=md.get("main_image"),
            brand=md.get("brand"),
            price=md.get("price"),
            score=float(m["score"]),
            description=md.get("description"),
        ))
        if len(cards) >= req.top_k:
            break

    return SearchResponse(results=cards)

# ---------------------------------------------------------
# 🪑 Item Details Endpoint (now returns normalized, display-ready fields)
# ---------------------------------------------------------
@app.get("/item/{id}", response_model=ProductDetail)
def get_item(id: str, db: Session = Depends(get_db)):
    raw_id = id
    clean_id = _normalize_id(raw_id)

    # Try normal and fallback lookups
    prod = db.execute(select(Product).where(Product.id == clean_id)).scalar_one_or_none()
    if not prod:
        alt_id = _normalize_id(unquote(str(raw_id).strip()))
        if alt_id and alt_id != clean_id:
            prod = db.execute(select(Product).where(Product.id == alt_id)).scalar_one_or_none()

    if not prod:
        logging.warning(f"❌ Product not found. raw='{raw_id}' normalized='{clean_id}'")
        raise HTTPException(status_code=404, detail=f"Product not found for id={clean_id or raw_id}")

    # Generate creative description using LLM
    title_for_llm = prod.title or "this item"
    creative = "A stylish, functional piece — built for everyday comfort."
    try:
        logging.info(f"✅ Generating description via LangChain for: '{title_for_llm}'")
        creative = description_chain.invoke({"title": title_for_llm}).strip()
    except Exception as e:
        logging.exception(f"❌ LLM generation failed: {e}")

    # ---- Normalize for display (title/description/creative + features/dimensions) ----
    norm = normalize_listing(
        title=prod.title,
        raw_description=prod.description or "",
        raw_creative=creative,
    )

    return ProductDetail(
        id=prod.id,
        title=norm["title"] or prod.title,
        brand=prod.brand,
        price=prod.price,
        main_category=prod.main_category,
        categories=prod.categories,
        material=prod.material,
        color=prod.color,
        main_image=prod.main_image,
        images=prod.images,
        description=norm["description"] or None,
        creative_description=norm["creative"] or None,
    )

# Add this at the very end of your main.py file
if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
