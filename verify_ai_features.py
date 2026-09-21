import json

print("Checking index.html...")
with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()
    assert "ai-recommender-panel" in html, "ai-recommender-panel missing in index.html"
    assert "ai-elo-predictor-card" in html, "ai-elo-predictor-card missing in index.html"
    assert "AI Dynamic Pricing Engine" in html, "AI Dynamic Pricing missing in index.html"
print("OK: index.html has all AI widgets")

print("Checking js/app.js...")
with open("js/app.js", "r", encoding="utf-8") as f:
    app_js = f.read()
    assert "openAICourtRecommenderModal" in app_js, "openAICourtRecommenderModal missing"
    assert "runAICourtRecommendation" in app_js, "runAICourtRecommendation missing"
    assert "toggleAIEloPredictor" in app_js, "toggleAIEloPredictor missing"
    assert "runAIMatchupCalculation" in app_js, "runAIMatchupCalculation missing"
    assert "simulateAIDynamicPricingRecalc" in app_js, "simulateAIDynamicPricingRecalc missing"
print("OK: js/app.js has all AI functions")

print("Checking css/styles.css...")
with open("css/styles.css", "r", encoding="utf-8") as f:
    css = f.read()
    assert "badge-ai-sparkle" in css, "badge-ai-sparkle missing in css"
print("OK: css/styles.css has all AI styles")

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
