# backend/wallets_utils.py

def transfer_ownership(from_wallet, to_wallet, sku):
    print(f"Transferring NFT for {sku} from {from_wallet} to {to_wallet}")
    # Fake transaction hash
    return f"tx_transfer_{sku}_{from_wallet}_to_{to_wallet}"
