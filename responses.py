import random

TEMPLATES = {
"sadness": [
"💛 Psalm 34:18 — 'The Lord is close to the broken-hearted.' You’re not alone.",
"🌧️ It’s okay to feel low. God is still working for your good even in silence.",
"🕊️ God’s love never fails, even when everything else feels shaky.",
],
"fear": [
"🕊️ Isaiah 41:10 — 'Do not fear, for I am with you.' Take courage today.",
"💫 You’re safe in His hands; He’s bigger than your worries.",
"🌤️ Even in uncertainty, God’s presence is steady and sure.",
],
"joy": [
"✨ Rejoice! God delights in your happiness.",
"🙌 Keep shining — your joy is light to others.",
"🌻 Gratitude multiplies joy; keep thanking Him.",
],
"neutral": [
"💛 Whatever you face, you’re not walking alone.",
"🕊️ God’s timing is perfect; keep trusting.",
"🌿 Rest in His peace; He’s guiding your next step.",
],
"anger": [
"🌾 Breathe and let God calm your heart — His peace is stronger than anger.",
"💭 It’s okay to feel frustrated; God can handle your honesty.",
"🕊️ Surrender the weight of anger; let His grace renew you.",
],
"stress": [
"🙏 Cast all your burdens on Him, for He cares for you.",
"💖 Pause, breathe, and remember: God is in control.",
"🌼 Let go and rest — His peace will steady your spirit.",
],
"loneliness": [
"❤️ You are never truly alone — God’s presence surrounds you.",
"💭 He hears even the prayers you can’t put into words.",
"🕊️ God’s love fills the quiet places of your heart.",
],
}

def get_response(category: str) -> str:
"""Return a warm, faith-based message aligned with detected emotion."""
category = (category or "neutral").lower().strip()
if category not in TEMPLATES:
category = "neutral"
return random.choice(TEMPLATES[category])
