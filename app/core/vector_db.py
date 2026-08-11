# app/core/vector_db.py
import os
import lancedb
from pyarrow import schema, field, float32, string, list_
from dotenv import load_dotenv

load_dotenv()

LANCEDB_URI = os.getenv("LANCEDB_URI", "./.lancedb_data")
CATALOG_TABLE_NAME = "product_catalog"

# Default to 384 for HuggingFace all-MiniLM-L6-v2
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))

catalog_schema = schema([
    field("id", string()),
    field("vector", list_(float32(), VECTOR_DIMENSION)),
    field("text", string()),
    field("category", string()),
    field("title", string())
])

def get_vector_db():
    return lancedb.connect(LANCEDB_URI)

def get_catalog_table():
    db = get_vector_db()
    if CATALOG_TABLE_NAME not in db.table_names():
        return db.create_table(CATALOG_TABLE_NAME, schema=catalog_schema)
    return db.open_table(CATALOG_TABLE_NAME)