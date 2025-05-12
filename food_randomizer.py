# Full updated version of food_randomizer.py with enhanced keyword matching across name, cuisine, and description
enhanced_keyword_code = 
import streamlit as st
import requests
import random
import pandas as pd
from datetime import datetime

OPENCAGE_API_KEY = "14334e30b2f64ed991640bbf6d1aacff"
LOG_FILE = "visit_log.csv"

try:
    log_df = pd.read_csv(LOG_FILE)
except FileNotFoundError:
    log_df = pd.DataFrame(columns=["Name", "Address", "Lat", "Lon", "Visited", "Timestamp"])

st.title("The Grazing Trail")
zip_code = st.text_input("Enter ZIP Code", "")
keywords = st.text_input("Enter up to 3 keywords (comma separated)", "")

if st.button("Find Me a Place") and zip_code:
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

        tags = "|".join([kw.strip() for kw in keywords.split(",") if kw.strip()])
        filter_enabled = bool(tags)

        overpass_query = f\"\"\"
        [out:json][timeout:25];
        (
          node["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
          way["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
          relation["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
        );
        out center;
        \"\"\"

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

            if filter_enabled:
                if not any(kw.lower() in search_fields for kw in tags.split("|")):
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
            st.warning("No matching places found. Try adjusting keywords.")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

if not log_df.empty:
    st.markdown("### Visit Log")
    st.dataframe(log_df)

# Save the enhanced version
enhanced_file_path = "/mnt/data/food_randomizer.py"
with open(enhanced_file_path, "w") as f:
    f.write(enhanced_keyword_code)

enhanced_file_path
