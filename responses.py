import random

TEMPLATES = {
    "sadness": [
        "Psalm 34:18 — 'The Lord is close to the broken-hearted.' You’re not alone. 💛",
        "It’s okay to feel low. God is still working for your good even in silence.",
    ],
    "fear": [
        "Isaiah 41:10 — 'Do not fear, for I am with you.' Take courage today. 🕊️",
        "You’re safe in His hands; He’s bigger than your worries.",
    ],
    "pain": [
        "God sees your pain and holds you through it. Rest, breathe, and know you’re loved. 🌿",
        "Your body and spirit are both precious to Him. 💪",
    ],
    "anxiety": [
        "Philippians 4:7 — 'The peace of God will guard your heart and mind.' 🕊️",
        "Slow down and breathe; He’s got you covered. ❤️",
    ],
    "loneliness": [
        "You are never truly alone — God’s presence surrounds you. ❤️",
        "He hears even the prayers you can’t put into words.",
    ],
    "joy": [
        "Rejoice! God delights in your happiness. ✨",
        "Keep shining — your joy is light to others. 🙌",
    ],
    "neutral": [
        "Whatever you face, you’re not walking alone. 💛",
        "God’s timing is perfect; keep trusting.",
    ],
}

def get_response(category):
    return random.choice(TEMPLATES.get(category, TEMPLATES["neutral"]))
