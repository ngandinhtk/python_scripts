import random

HOOKS = [
    "This Amazon product is going viral 🔥",
    "TikTok made me buy this 😱",
    "Best Amazon deal today 💰",
]

CTA = [
    "Buy now 👇",
    "Save money here 👇",
    "Limited deal 👇"
]

def generate_caption(affiliate_link):
    return f"{random.choice(HOOKS)}\n{random.choice(CTA)}\n{affiliate_link}\n#amazonfinds #tiktokmademebuyit #affiliate"
# Example usage