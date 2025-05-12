
import streamlit as st
import requests
import random
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="The Grazing Trail", layout="wide")

OPENCAGE_API_KEY = "14334e30b2f64ed991640bbf6d1aacff"
LOG_FILE = "visit_log.csv"
USER_HISTORY_FILE = "user_history.csv"

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

if "user" not in st.session_state:
    st.session_state.user = ""

if "last_result" not in st.session_state:
    st.session_state.last_result = {}

tab1, tab2 = st.tabs(["Trail Start", "My Trail"])

# Trail Start tab (search screen)
with tab1:
    st.image("bigfoot_walk.png", width=200)
    st.title("The Grazing Trail")

    st.text_input("Enter Your Trail Name (Login)", key="user")
    zip_code = st.text_input("Enter ZIP Code", "")
    keywords = st.text_input("Enter up to 3 keywords (comma separated)", "")

    if st.button("Find Me a Place") and zip_code:
        with st.spinner("Bigfoot is scouting your trail..."):
            st.image("bigfoot_backdrop.png", use_column_width=True)
            time.sleep(3)

        try:
            geo_req = requests.get(
                f"https://api.opencagedata.com/geocode/v1/json?q={zip_code}&key={OPENCAGE_API_KEY}&countrycode=us&limit=1"
            )
            geo_req.raise_for_status()
            geo_res = geo_req.json()

            if not geo_res["results"]:
                st.error("ZIP code not found.")
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
                st.session_state.last_result = random.choice(filtered)
                st.success("Trail found! Head to the 'My Trail' tab to see your next stop.")
            else:
                st.warning("No matching places found.")

        except Exception as e:
            st.error(f"Search failed: {e}")

# My Trail tab (shows result and eventually user history)
with tab2:
    st.header("Welcome to your Trail, " + (st.session_state.user or "Guest"))

    if st.session_state.last_result:
        result = st.session_state.last_result
        st.subheader("Try this place:")
        st.markdown(f"**{result['Name']}**")
        st.markdown(f"Location: ({result['Lat']}, {result['Lon']})")

        if st.button("Mark as Visited"):
            new_entry = {
                "Name": result["Name"],
                "Address": result["Address"],
                "Lat": result["Lat"],
                "Lon": result["Lon"],
                "Visited": True,
                "Timestamp": datetime.now().isoformat()
            }
            log_df = pd.concat([log_df, pd.DataFrame([new_entry])], ignore_index=True)
            log_df.to_csv(LOG_FILE, index=False)
            st.success("Trail mark logged.")
            st.session_state.last_result = {}

    st.markdown("---")
    if not log_df.empty:
        st.subheader("Your Visit Log")
        st.dataframe(log_df)
