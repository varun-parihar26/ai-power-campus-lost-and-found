import os
import uuid
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename

load_dotenv()  # reads backend/.env if present

from models import db, Item
from embedding import get_image_embedding, find_top_matches
from notifications import send_match_alert
from qr_utils import generate_qr_image_bytes, verify_claim_token

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
CORS(app)  # allow the React/HTML frontend (different port) to call this API

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'lost_found.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8MB max upload

db.init_app(app)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/api/items", methods=["POST"])
def create_item():
    """
    Create a new Lost or Found report.
    Expects multipart/form-data:
      - image (file, required)
      - title (str, required)
      - status ("lost" | "found", required)
      - description, category, location, contact_info (optional)
    """
    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400

    image = request.files["image"]
    title = request.form.get("title")
    status = request.form.get("status")

    if not title or not status:
        return jsonify({"error": "title and status are required"}), 400
    if status not in ("lost", "found"):
        return jsonify({"error": "status must be 'lost' or 'found'"}), 400
    if image.filename == "" or not allowed_file(image.filename):
        return jsonify({"error": "invalid or missing image file"}), 400

    # Save image with a unique filename to avoid collisions
    ext = image.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(unique_name))
    image.save(save_path)

    # Compute CLIP embedding for later matching
    embedding = get_image_embedding(save_path)

    item = Item(
        title=title,
        description=request.form.get("description"),
        category=request.form.get("category"),
        status=status,
        location=request.form.get("location"),
        contact_info=request.form.get("contact_info"),
        image_path=unique_name,
    )
    item.set_embedding(embedding)

    db.session.add(item)
    db.session.commit()

    # --- Unique feature: auto-match immediately on upload, not just on-demand ---
    opposite_status = "found" if item.status == "lost" else "lost"
    candidates_query = Item.query.filter_by(status=opposite_status, resolved=False).all()
    candidates = [(c, c.get_embedding()) for c in candidates_query]
    auto_matches = find_top_matches(item.get_embedding(), candidates, top_k=3, min_score=0.75)

    auto_match_payload = []
    for matched_item, score in auto_matches:
        auto_match_payload.append({**matched_item.to_dict(), "similarity": round(score, 4)})
        contact = item.contact_info or ""
        if "@" in contact:
            send_match_alert(
                to_email=contact,
                item_title=item.title,
                matched_title=matched_item.title,
                similarity=score,
                matched_image_url=matched_item.to_dict()["image_url"],
            )

    result = item.to_dict()
    result["auto_matches"] = auto_match_payload
    return jsonify(result), 201


@app.route("/api/items", methods=["GET"])
def list_items():
    """
    List items, optionally filtered by status/category/resolved.
    Query params: status, category, resolved
    """
    query = Item.query
    status = request.args.get("status")
    category = request.args.get("category")
    resolved = request.args.get("resolved")

    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if resolved is not None:
        query = query.filter_by(resolved=(resolved.lower() == "true"))

    items = query.order_by(Item.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])


@app.route("/api/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify(item.to_dict())


@app.route("/api/items/<int:item_id>/matches", methods=["GET"])
def get_matches(item_id):
    """
    Core feature: given a lost item, find visually similar found items (and vice versa).
    Only compares against items with the OPPOSITE status (lost <-> found).
    """
    item = Item.query.get_or_404(item_id)
    opposite_status = "found" if item.status == "lost" else "lost"

    candidates_query = Item.query.filter_by(status=opposite_status, resolved=False).all()
    candidates = [(c, c.get_embedding()) for c in candidates_query]

    query_embedding = item.get_embedding()
    if query_embedding is None:
        return jsonify({"error": "this item has no embedding computed"}), 500

    min_score = float(request.args.get("min_score", 0.6))
    top_k = int(request.args.get("top_k", 5))

    matches = find_top_matches(query_embedding, candidates, top_k=top_k, min_score=min_score)

    return jsonify([
        {**matched_item.to_dict(), "similarity": round(score, 4)}
        for matched_item, score in matches
    ])


@app.route("/api/items/search", methods=["GET"])
def search_items():
    """
    Unique feature: text search across title/description/category/location,
    combined with the usual status filter. Lets users type 'blue backpack library'
    instead of only relying on image matching.
    """
    q = request.args.get("q", "").strip()
    status = request.args.get("status")

    query = Item.query.filter_by(resolved=False)
    if status:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Item.title.ilike(like),
                Item.description.ilike(like),
                Item.category.ilike(like),
                Item.location.ilike(like),
            )
        )
    items = query.order_by(Item.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])


@app.route("/api/items/<int:item_id>/claim-qr/<int:matched_item_id>", methods=["GET"])
def claim_qr(item_id, matched_item_id):
    """
    Unique feature: generates a QR 'claim slip' PNG for a confirmed match.
    The claimant shows this at the lost-and-found desk; staff scan it to
    verify the pairing is genuine (via verify_claim_token) instead of trusting
    a verbal claim.
    """
    Item.query.get_or_404(item_id)
    Item.query.get_or_404(matched_item_id)
    png_bytes = generate_qr_image_bytes(item_id, matched_item_id)
    return Response(png_bytes, mimetype="image/png")


@app.route("/api/claim/verify", methods=["GET"])
def verify_claim():
    """Desk-side verification: given the three values encoded in the QR, confirm authenticity."""
    item_id = request.args.get("item_id", type=int)
    matched_item_id = request.args.get("matched_item_id", type=int)
    token = request.args.get("token", "")
    valid = verify_claim_token(item_id, matched_item_id, token) if item_id and matched_item_id else False
    return jsonify({"valid": valid})


@app.route("/api/items/<int:item_id>/resolve", methods=["PATCH"])
def resolve_item(item_id):
    """Mark an item as resolved (claimed/returned)."""
    item = Item.query.get_or_404(item_id)
    item.resolved = True
    db.session.commit()
    return jsonify(item.to_dict())


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    # Clean up the stored image file too
    image_path = os.path.join(app.config["UPLOAD_FOLDER"], item.image_path)
    if os.path.exists(image_path):
        os.remove(image_path)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "deleted"})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
