import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError
from datetime import datetime

from db import sneakers  # Ensure this connects correctly
from cnn_model import verify_sneaker
from mint import mint_nft_on_solana
from wallets_utils import transfer_ownership

# 🔧 Disable default static folder
app = Flask(__name__, static_folder=None)
CORS(app)

# Helper paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
STATIC_DIR = os.path.join(FRONTEND_DIR, 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')
TMP_DIR = os.path.join(BASE_DIR, 'tmp')

# Ensure folders exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# Serve frontend
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_root_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

# 🧠 Handle /static/* manually
@app.route('/static/<path:filename>')
def serve_static(filename):
    full_path = os.path.join(STATIC_DIR, filename)
    print(f"[DEBUG] Trying to serve: {full_path}")
    return send_from_directory(STATIC_DIR, filename)

@app.route('/static/uploads/<filename>')
def serve_uploaded_image(filename):
    return send_from_directory(UPLOADS_DIR, filename)

# Health check for MongoDB
@app.route('/health', methods=['GET'])
def health_check():
    try:
        test_doc = {"status": "ok"}
        sneakers.insert_one(test_doc)
        sneakers.delete_one(test_doc)
        return jsonify({"status": "MongoDB connected"})
    except PyMongoError as e:
        return jsonify({"status": "MongoDB connection error", "error": str(e)}), 500

# Get all sneakers
@app.route('/sneakers', methods=['GET'])
def get_all_sneakers():
    sneaker_list = list(sneakers.find())
    for s in sneaker_list:
        s['_id'] = str(s['_id'])
    return jsonify(sneaker_list)

# Get a single sneaker by ID
@app.route('/sneaker/<id>', methods=['GET'])
def get_sneaker(id):
    sneaker = sneakers.find_one({"_id": ObjectId(id)})
    if sneaker:
        sneaker['_id'] = str(sneaker['_id'])
        return jsonify(sneaker)
    return jsonify({"error": "Sneaker not found"}), 404

# Upload a sneaker
@app.route('/upload', methods=['POST'])
def upload_sneaker():
    sku = request.form.get('sku')
    name = request.form.get('name')
    owner = request.form.get('wallet')
    price = request.form.get('price')
    size = request.form.get('size')
    color = request.form.get('color')
    bid_start = request.form.get('bid_start')
    bid_end = request.form.get('bid_end')
    image_files = request.files.getlist('images')

    if not all([sku, name, owner, price, size, color, bid_start, bid_end]) or not image_files or len(image_files) < 1:
        return jsonify({"message": "Missing required fields or images"}), 400

    if len(image_files) > 5:
        return jsonify({"message": "Upload between 1 to 5 images only."}), 400

    try:
        image_urls = []

        for idx, image_file in enumerate(image_files):
            tmp_image_path = os.path.join(TMP_DIR, f'{sku}_{idx}.jpg')
            image_file.save(tmp_image_path)

            if idx == 0:
                verified = verify_sneaker(tmp_image_path, sku)
                if not verified:
                    return jsonify({"message": "Sneaker image verification failed"}), 403

            final_image_path = os.path.join(UPLOADS_DIR, f'{sku}_{idx}.jpg')
            image_file.seek(0)
            image_file.save(final_image_path)
            image_url = f"/static/uploads/{sku}_{idx}.jpg"
            image_urls.append(image_url)

        mint_tx = mint_nft_on_solana(owner, sku)
        mint_date = datetime.utcnow().isoformat()

        sneaker_doc = {
            "sku": sku,
            "name": name,
            "image_urls": image_urls,
            "owner": owner,
            "price": float(price),
            "size": size,
            "color": color,
            "bid_start": bid_start,
            "bid_end": bid_end,
            "mint_history": [
                {
                    "mint_tx": mint_tx,
                    "owner": owner,
                    "date": mint_date
                }
            ]
        }

        insert_result = sneakers.insert_one(sneaker_doc)
        print(f"[INFO] Sneaker saved with ID: {insert_result.inserted_id}")

        return jsonify({
            "message": "✅ Sneaker uploaded and minted successfully",
            "id": str(insert_result.inserted_id)
        })

    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return jsonify({"message": "Server error", "error": str(e)}), 500

# Buy sneaker (transfer ownership)
@app.route('/buy/<id>', methods=['POST'])
def buy_sneaker(id):
    buyer_wallet = request.json.get('buyer_wallet')
    if not buyer_wallet:
        return jsonify({"error": "Missing buyer wallet"}), 400

    sneaker = sneakers.find_one({"_id": ObjectId(id)})
    if not sneaker:
        return jsonify({"error": "Sneaker not found"}), 404

    seller_wallet = sneaker['owner']
    transfer_tx = transfer_ownership(seller_wallet, buyer_wallet, sneaker['sku'])
    transfer_date = datetime.utcnow().isoformat()

    sneakers.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "owner": buyer_wallet,
            "mint_tx": transfer_tx
        },
         "$push": {
             "mint_history": {
                 "mint_tx": transfer_tx,
                 "owner": buyer_wallet,
                 "date": transfer_date
             }
         }}
    )

    return jsonify({"message": "Ownership transferred", "tx": transfer_tx})

# DB test
@app.route('/test-db', methods=['GET'])
def test_db():
    try:
        test_doc = {"sku": "TEST", "name": "Test Sneaker"}
        result = sneakers.insert_one(test_doc)
        return jsonify({"inserted_id": str(result.inserted_id)})
    except Exception as e:
        return jsonify({"error": str(e)})

# Run the server
if __name__ == '__main__':
    app.run(debug=True)
