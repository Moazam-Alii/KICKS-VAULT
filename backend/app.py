import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError
from datetime import datetime, timezone
from dotenv import load_dotenv
from email.mime.text import MIMEText
import smtplib
from .db import sneakers, bids
from .cnn_model import verify_sneaker
from .mint import mint_nft_on_solana
from .wallets_utils import transfer_ownership
from flask_mail import Mail, Message
from datetime import datetime, timezone,timedelta


load_dotenv()
app = Flask(__name__, static_folder=None)
CORS(app)

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
STATIC_DIR = os.path.join(FRONTEND_DIR, 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')
TMP_DIR = os.path.join(BASE_DIR, 'tmp')

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# Email sender utility
def send_email_notification(to_email, subject, body):
    try:
        sender_email = "kicksvault99@gmail.com"
        app_password = "dylspkywtuhvsdel"

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        
        print(f"[EMAIL] Sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_root_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/static/uploads/<filename>')
def serve_uploaded_image(filename):
    return send_from_directory(UPLOADS_DIR, filename)

@app.route('/health', methods=['GET'])
def health_check():
    try:
        sneakers.insert_one({"test": True})
        sneakers.delete_one({"test": True})
        return jsonify({"status": "MongoDB connected"})
    except PyMongoError as e:
        return jsonify({"status": "MongoDB error", "error": str(e)}), 500

@app.route('/sneakers', methods=['GET'])
def get_all_sneakers():
    sneaker_list = list(sneakers.find())
    for s in sneaker_list:
        s['_id'] = str(s['_id'])
    return jsonify(sneaker_list)

@app.route('/sneaker/<id>', methods=['GET'])
def get_sneaker(id):
    sneaker = sneakers.find_one({"_id": ObjectId(id)})
    if sneaker:
        sneaker['_id'] = str(sneaker['_id'])
        return jsonify(sneaker)
    return jsonify({"error": "Sneaker not found"}), 404

@app.route('/upload', methods=['POST'])
def upload_sneaker():
    sku = request.form.get('sku')
    name = request.form.get('name')
    owner = request.form.get('wallet')
    email = request.form.get('email')
    price = request.form.get('price')
    size = request.form.get('size')
    color = request.form.get('color')

    bid_start = request.form.get('bid_start')
    bid_end = request.form.get('bid_end')

    try:
        PAKISTAN_TZ = timezone(timedelta(hours=5))
        bid_start = datetime.fromisoformat(bid_start).replace(tzinfo=PAKISTAN_TZ).astimezone(timezone.utc).isoformat()
        bid_end = datetime.fromisoformat(bid_end).replace(tzinfo=PAKISTAN_TZ).astimezone(timezone.utc).isoformat()   
    

    except Exception:
        return jsonify({"message": "Invalid datetime format"}), 400

    image_files = request.files.getlist('images')
    if not all([sku, name, owner, email, price, size, color, bid_start, bid_end]) or not image_files:
        return jsonify({"message": "Missing required fields"}), 400
    if len(image_files) > 5:
        return jsonify({"message": "Max 5 images allowed"}), 400

    try:
        image_urls = []
        for idx, image_file in enumerate(image_files):
            tmp_image_path = os.path.join(TMP_DIR, f'{sku}_{idx}.jpg')
            image_file.save(tmp_image_path)

            if idx == 0 and not verify_sneaker(tmp_image_path, sku):
                return jsonify({"message": "Verification failed"}), 403

            final_image_path = os.path.join(UPLOADS_DIR, f'{sku}_{idx}.jpg')
            image_file.seek(0)
            image_file.save(final_image_path)
            image_urls.append(f"/static/uploads/{sku}_{idx}.jpg")

        mint_tx = mint_nft_on_solana(owner, sku)
        mint_date = datetime.utcnow().isoformat()

        sneaker_doc = {
            "sku": sku,
            "name": name,
            "image_urls": image_urls,
            "owner": owner,
            "email": email,
            "price": float(price),
            "size": size,
            "color": color,
            "bid_start": bid_start,
            "bid_end": bid_end,
            "mint_history": [{
                "mint_tx": mint_tx,
                "owner": owner,
                "date": mint_date
            }]
        }

        insert_result = sneakers.insert_one(sneaker_doc)

        send_email_notification(email, "✅ Sneaker Verified & Listed", f"Your sneaker '{name}' (SKU: {sku}) is now live.")
        return jsonify({"message": "✅ Sneaker uploaded", "id": str(insert_result.inserted_id)})
    except Exception as e:
        return jsonify({"message": "Upload error", "error": str(e)}), 500

@app.route('/buy/<id>', methods=['POST'])
def buy_sneaker(id):
    buyer_wallet = request.json.get('buyer_wallet')
    sneaker = sneakers.find_one({"_id": ObjectId(id)})
    if not sneaker:
        return jsonify({"error": "Sneaker not found"}), 404

    tx = transfer_ownership(sneaker['owner'], buyer_wallet, sneaker['sku'])
    transfer_date = datetime.utcnow().isoformat()

    sneakers.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"owner": buyer_wallet, "mint_tx": tx},
         "$push": {"mint_history": {"mint_tx": tx, "owner": buyer_wallet, "date": transfer_date}}}
    )
    return jsonify({"message": "Transferred", "tx": tx})

# Bidding logic
mail = Mail(app)

@app.route("/bid/<sku>", methods=["POST"])
def place_bid(sku):
    data = request.json
    wallet = data.get("wallet")
    amount = float(data.get("amount", 0))
    email = data.get("email")
    option = data.get("option")  # trade or delivery

    sneaker = sneakers.find_one({"sku": sku})
    if not sneaker:
        return jsonify({"error": "Sneaker not found"}), 404

    now = datetime.now(timezone.utc)
    try:
        bid_start = datetime.fromisoformat(sneaker["bid_start"]).replace(tzinfo=timezone.utc)
        bid_end = datetime.fromisoformat(sneaker["bid_end"]).replace(tzinfo=timezone.utc)
    except KeyError:
        return jsonify({"error": "Sneaker does not have bid_start/bid_end"}), 400

    if now < bid_start:
        return jsonify({"error": "Bidding not started yet"}), 403
    if now > bid_end:
        return jsonify({"error": "Bidding ended"}), 403

    bid_doc = bids.find_one({"sku": sku}) or {"sku": sku, "bids": []}
    existing_bids = bid_doc["bids"]

    # Get highest existing bid
    highest_bid = max(existing_bids, key=lambda b: b["amount"], default=None) if existing_bids else None
    highest_amount = highest_bid["amount"] if highest_bid else sneaker["price"]

    if amount <= highest_amount:
        return jsonify({"error": "Bid must exceed current highest"}), 400

    new_bid = {
        "wallet": wallet,
        "amount": amount,
        "email": email,
        "option": option,
        "timestamp": datetime.utcnow().isoformat(),
        "paid": False
    }

    # Send email to previous highest bidder
    if highest_bid:
        prev_email = highest_bid.get("email")
        prev_amount = highest_bid.get("amount")
        sneaker_name = sneaker.get("name", sku)
        subject = f"Someone outbid you on {sneaker_name}"
        body = f"""
Hi,

You previously placed a bid of {prev_amount} SOL on the sneaker: {sneaker_name} (SKU: {sku}).

Unfortunately, someone has just placed a higher bid of {amount} SOL.

You can visit the product page to place a higher bid if you want to stay in the game!

Regards,  
KICKS-VAULT Team
        """
        send_email_notification(prev_email, subject, body)

    # Save new bid
    bids.update_one({"sku": sku}, {"$push": {"bids": new_bid}}, upsert=True)

    return jsonify({"message": "✅ Bid submitted successfully!"})

@app.route("/bids/<sku>", methods=["GET"])
def get_bids(sku):
    bid_doc = bids.find_one({"sku": sku})
    if not bid_doc or "bids" not in bid_doc:
        return jsonify([])  # Return empty list if no bids found

    return jsonify(bid_doc["bids"])



@app.route("/admin/evaluate-all-bids", methods=["POST"])
def evaluate_all_bids():
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    expired_sneakers = list(sneakers.find({"bid_end": {"$lt": now},
                                            "sold": {"$ne": True},
                                       "notified": {"$ne": True}}))

    results = []

    for sneaker in expired_sneakers:
        sku = sneaker["sku"]
        seller_email = sneaker["email"]
        sneaker_name = sneaker["name"]

        bid_doc = bids.find_one({"sku": sku})
        if not bid_doc or not bid_doc.get("bids"):
            send_email_notification(
                seller_email,
                f"❌ Sneaker Unsold: {sneaker_name}",
                f"""Hi,\n\nYour sneaker '{sneaker_name}' (SKU: {sku}) received no bids and has been removed from KICKS-VAULT.\n\nRegards,\nKICKS-VAULT Team"""
            )
            sneakers.delete_one({"sku": sku})
            results.append({"sku": sku, "status": "Deleted (no bids)"})
            continue

        sorted_bids = sorted(bid_doc["bids"], key=lambda b: -b["amount"])
        top_bid = sorted_bids[0]

        buyer_email = top_bid["email"]
        amount = top_bid["amount"]
        option = top_bid["option"]
        buyer_wallet = top_bid["wallet"]

        send_email_notification(
            buyer_email,
            f" You are the highest bidder for {sneaker_name}!",
            f"""
Hi,

You won the bid for '{sneaker_name}' (SKU: {sku}) with a bid of {amount} SOL.

 Please transfer {amount} SOL to our official wallet within 2 hours.
 Option selected: {option.upper()}

 If Trade: Sneaker will be relisted in 3 days after human verification.
 If Delivery: You'll receive your sneaker in 7 days after verification.

Include this SKU in your transfer memo: **{sku}**

If verification fails, your funds will be refunded.

Regards,  
KICKS-VAULT Team
            """
        )

        send_email_notification(
            seller_email,
            f"📦 Sneaker Sold: {sneaker_name}",
            f"""
Hi,

Your sneaker '{sneaker_name}' (SKU: {sku}) has been sold for {amount} SOL.

Please ship the sneaker to our warehouse for human verification.

Once verified, your wallet will receive the funds (minus 1% fee).

Fake or unverifiable sneakers will be returned.

Regards,  
KICKS-VAULT Team
            """
        )
        sneakers.update_one({"sku": sku}, {"$set": {"notified": True}})
        results.append({"sku": sku, "status": "Buyer & seller notified"})

    return jsonify(results)


@app.route("/admin/finalize-bids/<sku>", methods=["POST"])
def finalize_bid(sku):
    bid_doc = bids.find_one({"sku": sku})
    sneaker = sneakers.find_one({"sku": sku})

    if not bid_doc or not sneaker:
        return jsonify({"error": "Sneaker or bids not found"}), 404

    paid_bids = [b for b in bid_doc["bids"] if b.get("paid")]
    if not paid_bids:
        return jsonify({"message": "Still no payment received"})

    highest = sorted(paid_bids, key=lambda b: -b["amount"])[0]

    # Update sneaker as sold
    sneakers.update_one({"sku": sku}, {"$set": {"sold": True, "owner": highest["wallet"]}})
    
    send_email_notification(
        highest["email"],
        " Payment Confirmed",
        f"Your payment for sneaker '{sneaker['name']}' (SKU: {sku}) has been confirmed. Thank you!"
    )

    send_email_notification(
        sneaker["email"],
        " Buyer Payment Received",
        f"The buyer for your sneaker '{sneaker['name']}' (SKU: {sku}) has paid. Please proceed with shipment."
    )

    return jsonify({"message": f"✅ Marked as sold to {highest['wallet']}"})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

