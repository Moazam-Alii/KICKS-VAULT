# backend/cnn_model.py

def verify_sneaker(image_path, sku):
    print(f"Verifying sneaker for SKU: {sku} at {image_path}")
    # Mock logic — just approve if SKU is even-length
    return len(sku) % 2 == 0
