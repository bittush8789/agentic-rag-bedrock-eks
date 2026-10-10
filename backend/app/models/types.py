import json
from sqlalchemy.types import TypeDecorator, JSON
from pgvector.sqlalchemy import Vector
from app.core.config import settings


class AdaptiveVector(TypeDecorator):
    """
    Adaptive vector column:
    Uses native pgvector Vector on PostgreSQL and JSON representation on SQLite.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 1024, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return [float(x) for x in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                pass
        return [float(x) for x in value]
