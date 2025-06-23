import os
import requests
from collections import Counter

# Roboflow API setup
API_URL = "https://detect.roboflow.com/counterfeit-nike-shoes-detection/2"
API_KEY = "1S1UWcRcCDNVRr7cqwk8"  # Replace with your actual key if needed

def verify_sneaker(primary_image_path, sku):
    """
    This function now checks images directly from the TMP directory, based on SKU prefix.
    It assumes images are saved like tmp/sku_0.jpg, tmp/sku_1.jpg, etc.
    """
    print(f"\n🔍 Verifying sneaker for SKU: {sku} using TMP images")

    # Find all temp images matching this SKU
    tmp_dir = os.path.dirname(primary_image_path)
    matching_images = sorted([
        os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)
        if f.startswith(sku) and f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    if not matching_images:
        print("⚠️ No images found in TMP matching this SKU.")
        return False

    print(f"🖼️ Found {len(matching_images)} image(s) for verification.")

    predictions = []
    real_confidences = []

    for img_path in matching_images:
        print(f"📷 Predicting: {os.path.basename(img_path)}")

        with open(img_path, "rb") as image_data:
            response = requests.post(
                f"{API_URL}?api_key={API_KEY}",
                files={"file": image_data},
                data={"name": os.path.basename(img_path)}
            )

        if response.status_code != 200:
            print(f"❌ Failed for {img_path}: HTTP {response.status_code}")
            continue

        result = response.json()

        if result.get("predictions"):
            top = result["predictions"][0]
            label = top["class"].lower()
            confidence = float(top["confidence"]) * 100
            predictions.append(label)
            print(f"✅ Detected: {label.upper()} ({confidence:.2f}%)")

            if "real" in label or "original" in label:
                real_confidences.append(confidence)
        else:
            print("❌ No prediction detected.")

    # Summary
    label_count = Counter(predictions)
    print(f"\n📦 Prediction Summary: {dict(label_count)}")

    if real_confidences:
        avg_conf = sum(real_confidences) / len(real_confidences)
        print(f"📊 Average REAL confidence: {avg_conf:.2f}%")

        if avg_conf >= 75:
            print("🎉 Verdict: AUTHENTIC ✅")
            return True
        else:
            print("🚨 Verdict: LIKELY FAKE ❌")
            return False
    else:
        print("⚠️ No 'real' predictions — verdict: FAKE")
        return False
