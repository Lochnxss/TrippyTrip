
import streamlit as st
import requests
import random
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="The Grazing Trail", layout="wide")

OPENCAGE_API_KEY = "14334e30b2f64ed991640bbf6d1aacff"
LOG_FILE = "visit_log.csv"

def normalize(word):
    word = word.lower().strip()
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word

intent_map = {
    "pancake": ["pancake", "breakfast", "diner", "waffle", "ihop", "griddle"],
    "steak": ["steak", "steakhouse", "bbq", "grill", "roadhouse", "outback"],
    "burger": ["burger", "grill", "diner", "fast food", "five guys", "wendy's", "mcdonald", "whopper"],
    "pizza": ["pizza", "pizzeria", "italian", "domino", "papa john", "little caesar"],
    "sushi": ["sushi", "japanese", "hibachi", "miso", "ramen", "bento"],
    "chicken": ["chicken", "fried", "kfc", "popeyes", "nashville", "hot"],
    "taco": ["taco", "mexican", "taqueria", "chipotle", "burrito", "quesadilla"],
    "seafood": ["seafood", "shrimp", "crab", "fish", "lobster", "clam", "oyster"],
    "coffee": ["coffee", "cafe", "espresso", "latte", "starbucks", "java", "brew"],
    "salad": ["salad", "healthy", "greens", "vegetarian", "vegan", "bowl"],
    "bbq": ["bbq", "barbecue", "smokehouse", "ribs", "brisket", "pit"],
    "dessert": ["dessert", "ice cream", "sweet", "bakery", "donut", "cake", "pie"]
}

try:
    log_df = pd.read_csv(LOG_FILE)
except FileNotFoundError:
    log_df = pd.DataFrame(columns=["Name", "Address", "Lat", "Lon", "Visited", "Timestamp"])

# AD BOXES
st.markdown("""
<style>
.ad-top-left, .ad-top-right, .ad-bottom-left, .ad-bottom-right {
    position: fixed;
    background: #f8f8f8;
    padding: 6px 10px;
    z-index: 9999;
    font-size: 12px;
    font-weight: bold;
    border: 1px solid #ddd;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.1);
    opacity: 0.9;
}
.ad-top-left { top: 5px; left: 5px; }
.ad-top-right { top: 5px; right: 5px; }
.ad-bottom-left { bottom: 5px; left: 5px; }
.ad-bottom-right { bottom: 5px; right: 5px; }
</style>
<div class="ad-top-left">[AD] Eat Local</div>
<div class="ad-top-right">[AD] Bigfoot's Burgers</div>
<div class="ad-bottom-left">[AD] Trail Mix Deals</div>
<div class="ad-bottom-right">[AD] Hike & Bite App</div>
""", unsafe_allow_html=True)

st.image("bigfoot_walk.png", width=200)
st.title("The Grazing Trail")

zip_code = st.text_input("Enter ZIP Code", "")
keywords = st.text_input("Enter up to 3 keywords (comma separated)", "")

if st.button("Find Me a Place") and zip_code:
    st.markdown("## Bigfoot is scouting your trail...")
    st.image("bigfoot_backdrop.png", use_column_width=True)
    st.markdown("_(Hang tight, he's sniffing out something tasty...)_")
    time.sleep(3.5)

    try:
        geo_req = requests.get(
            f"https://api.opencagedata.com/geocode/v1/json?q={zip_code}&key={OPENCAGE_API_KEY}&countrycode=us&limit=1"
        )
        geo_req.raise_for_status()
        geo_res = geo_req.json()

        if not geo_res["results"]:
            st.error("ZIP code not found or blocked. Try a nearby ZIP.")
            st.stop()

        coords = geo_res["results"][0]["geometry"]
        lat = coords["lat"]
        lon = coords["lng"]

        raw_keywords = [normalize(kw) for kw in keywords.split(",") if kw.strip()]
        expanded_terms = set()
        for kw in raw_keywords:
            expanded_terms.update(normalize(term) for term in intent_map.get(kw, [kw]))

        filter_enabled = bool(expanded_terms)

        overpass_query = f"""
        [out:json][timeout:25];
        (
          node["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
          way["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
          relation["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
        );
        out center;
        """

        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": overpass_query})
        res.raise_for_status()
        data = res.json().get("elements", [])

        filtered = []
        for place in data:
            tags_dict = place.get("tags", {})
            name = tags_dict.get("name", "")
            cuisine = tags_dict.get("cuisine", "")
            description = tags_dict.get("description", "")

            if not name:
                continue

            search_fields = f"{name} {cuisine} {description}".lower()
            search_words = [normalize(word) for word in search_fields.split()]

            if filter_enabled:
                if not any(term in search_words for term in expanded_terms):
                    continue

            lat = place.get("lat") or place.get("center", {}).get("lat")
            lon = place.get("lon") or place.get("center", {}).get("lon")
            address = tags_dict.get("addr:full", "Unknown")
            filtered.append({"Name": name, "Address": address, "Lat": lat, "Lon": lon})

        if filtered:
            suggestion = random.choice(filtered)
            st.subheader("Try this place:")
            st.markdown(f"**{suggestion['Name']}**")
            st.markdown(f"Location: ({suggestion['Lat']}, {suggestion['Lon']})")

            if st.button("Mark as Visited"):
                new_entry = {
                    "Name": suggestion["Name"],
                    "Address": suggestion["Address"],
                    "Lat": suggestion["Lat"],
                    "Lon": suggestion["Lon"],
                    "Visited": True,
                    "Timestamp": datetime.now().isoformat()
                }
                log_df = pd.concat([log_df, pd.DataFrame([new_entry])], ignore_index=True)
                log_df.to_csv(LOG_FILE, index=False)
                st.success("Visit logged.")
        else:
            st.warning("No matching places found. Try broadening your search.")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

if not log_df.empty:
    st.markdown("### Visit Log")
    st.dataframe(log_df)
