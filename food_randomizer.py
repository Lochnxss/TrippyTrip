
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

# State tracking
if "stage" not in st.session_state:
    st.session_state.stage = "form"
if "last_result" not in st.session_state:
    st.session_state.last_result = {}

# FORM screen
if st.session_state.stage == "form":
    st.image("bigfoot_walk.png", width=200)
    st.title("The Grazing Trail")
    zip_code = st.text_input("Enter ZIP Code", "")
    keywords = st.text_input("Enter up to 3 keywords (comma separated)", "")
    if st.button("Find Me a Place") and zip_code:
        st.session_state.zip_code = zip_code
        st.session_state.keywords = keywords
        st.session_state.stage = "loading"

# LOADING screen
if st.session_state.stage == "loading":
    st.image("bigfoot_backdrop.png", use_column_width=True)
    st.markdown("### Bigfoot is scouting your trail...")
    st.markdown("_(Hang tight, he's sniffing out something tasty...)_")
    time.sleep(3.5)
    st.session_state.stage = "result"

# RESULT screen
if st.session_state.stage == "result":
    zip_code = st.session_state.zip_code
    keywords = st.session_state.keywords
    try:
        geo_req = requests.get(
            f"https://api.opencagedata.com/geocode/v1/json?q={zip_code}&key={OPENCAGE_API_KEY}&countrycode=us&limit=1"
        )
        geo_req.raise_for_status()
        geo_res = geo_req.json()

        if not geo_res["results"]:
            st.error("ZIP code not found or blocked. Try a nearby ZIP.")
            st.session_state.stage = "form"
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
            st.session_state.last_result = suggestion
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
                st.session_state.stage = "form"
        else:
            st.warning("No matching places found. Try broadening your search.")
            st.session_state.stage = "form"

    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.session_state.stage = "form"

if not log_df.empty:
    st.markdown("### Visit Log")
    st.dataframe(log_df)
