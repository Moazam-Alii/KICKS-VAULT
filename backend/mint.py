from solana.rpc.api import Client
from solana.rpc.api import Transaction
from solana.rpc.types import TxOpts
def mint_nft_on__solana(wallet_address, sku):
    # Set up client
    client = Client("https://api.devnet.solana.com")
    SECRET_KEY = ["jdew9d84hfuf48dsmxksnc59947ddifu4f73"]
    create_account= True;
    mint = True
    creator=1
    txn = Transaction()
    txn.add(
        create_account(
          #  CreateAccountParams
                from_pubkey=creator.public_key,
                new_account_pubkey=mint.public_key,
                lamports=client.get_minimum_balance_for_rent_exemption(82)["result"],
                space=82,

            )
        )
    # Initialize mint
    txn.add(
      #  initialize_mint
            mint=mint.public_key,
            decimals=0,
            mint_authority=creator.public_key,
            freeze_authority=creator.public_key,
        )
    

    
    txn.add(
      #  create_associated_token_account
            payer=creator.public_key,
            mint=mint.public_key,
        )
    

    txn.add(
       # mint_to(
            mint=mint.public_key,
            mint_authority=creator.public_key,
            amount=1,
        )
   


    # Metadata
    metadata_program_id =("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
    #metadata_pda, _ = find_program_address
    (
        [b"metadata", bytes(metadata_program_id), bytes(mint.public_key)],
        metadata_program_id,
    )
    try:
        result = getattr
        tx_sig = result['result']
        print(f"✅ NFT Minted: {tx_sig}")
        return tx_sig
    except Exception as e:
        print("❌ Mint failed:", str(e))
        return None   
def mint_nft_on_solana(wallet_address, sku):
    print(f"Minting NFT for SKU {sku} to wallet {wallet_address}")
    return f"{sku}53ef6e38{wallet_address}" 