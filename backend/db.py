import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

# Use kicks_vault database and sneakers collection
db = client["kicks_vault"]
sneakers = db["sneakers"]
bids = db["bids"]