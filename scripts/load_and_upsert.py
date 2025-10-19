# scripts/load_db_only.py
import os, sys, json, pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# Load environment variables (optional for local dev)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./products.db")

# --- DB setup ---
engine = create_engine(
    DATABASE_URL, pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

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
    main_image = Column(Text, nullable=True)   # one hero image
    images = Column(JSON, nullable=True)       # list[str] gallery
    description = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

def pick_id_col(df):
    for c in ["uniq_id", "id", "sku", "product_id"]:
        if c in df.columns:
            return c
    df["id"] = df.index.astype(str)
    return "id"

def to_float(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    s = str(v).replace("$", "").strip()
    try: return float(s)
    except: return None

def parse_images(v):
    """Accept list as-is; if string that looks like JSON list -> json.loads; if comma string -> split; else None/[]"""
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    if isinstance(v, list): return v
    if isinstance(v, str):
        v = v.strip()
        if not v: return None
        if v.startswith("[") and v.endswith("]"):
            try: return json.loads(v)
            except: pass
        if "," in v:
            return [p.strip() for p in v.split(",") if p.strip()]
        return [v]  # single URL string
    return None

def main(csv_path: str):
    df = pd.read_csv(csv_path)
    id_col = pick_id_col(df)

    # Only map known columns; missing ones become None
    cols = {
        "title": "title", "brand": "brand", "price": "price",
        "main_category": "main_category", "categories": "categories",
        "material": "material", "color": "color",
        "main_image": "main_image", "images": "images",
        "description": "description"
    }
    with Session(engine) as session:
        for _, r in df.iterrows():
            p = Product(
                id=str(r[id_col]),
                title=str(r.get(cols["title"]) or "") if cols["title"] in df.columns else None,
                brand=str(r.get(cols["brand"])) if cols["brand"] in df.columns and pd.notna(r.get(cols["brand"])) else None,
                price=to_float(r.get(cols["price"])) if cols["price"] in df.columns else None,
                main_category=str(r.get(cols["main_category"])) if cols["main_category"] in df.columns and pd.notna(r.get(cols["main_category"])) else None,
                categories=str(r.get(cols["categories"])) if cols["categories"] in df.columns and pd.notna(r.get(cols["categories"])) else None,
                material=str(r.get(cols["material"])) if cols["material"] in df.columns and pd.notna(r.get(cols["material"])) else None,
                color=str(r.get(cols["color"])) if cols["color"] in df.columns and pd.notna(r.get(cols["color"])) else None,
                main_image=str(r.get(cols["main_image"])) if cols["main_image"] in df.columns and pd.notna(r.get(cols["main_image"])) else None,
                images=parse_images(r.get(cols["images"])) if cols["images"] in df.columns else None,
                description=str(r.get(cols["description"])) if cols["description"] in df.columns and pd.notna(r.get(cols["description"])) else None,
            )
            session.merge(p)  # upsert
        session.commit()
    print("✅ DB loaded (main_image + images kept exactly as in CSV).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_db_only.py preprocessed_furniture_data.csv")
        sys.exit(1)
    main(sys.argv[1])
