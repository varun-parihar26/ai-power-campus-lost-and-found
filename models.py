from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()


class Item(db.Model):
    """
    Represents a single Lost or Found report.
    `embedding` stores the CLIP image embedding as a JSON-encoded list of floats,
    so we can load it back into a numpy array for cosine similarity search.
    """
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)       # e.g. "Electronics", "ID Card", "Bag"
    status = db.Column(db.String(10), nullable=False)        # "lost" or "found"
    location = db.Column(db.String(120), nullable=True)
    contact_info = db.Column(db.String(120), nullable=True)
    image_path = db.Column(db.String(255), nullable=False)
    embedding = db.Column(db.Text, nullable=True)             # JSON list[float]
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)

    def set_embedding(self, vector):
        """vector: list[float] or numpy array"""
        self.embedding = json.dumps(list(map(float, vector)))

    def get_embedding(self):
        if not self.embedding:
            return None
        return json.loads(self.embedding)

    def to_dict(self, include_embedding=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "location": self.location,
            "contact_info": self.contact_info,
            "image_url": f"/uploads/{self.image_path}",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved": self.resolved,
        }
        if include_embedding:
            data["embedding"] = self.get_embedding()
        return data
