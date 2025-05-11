
import streamlit as st
import requests
import random
import pandas as pd
from datetime import datetime

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
            f"https://nominatim.openstreetmap.org/search?postalcode={zip_code}&country=us&format=json",
            headers={"User-Agent": "TheGrazingTrail/1.0 (you@example.com)"}
        )
        geo_req.raise_for_status()
        geo_res = geo_req.json()
    except Exception as e:
        st.error(f"ZIP code lookup failed: {e}")
        st.stop()

    if not geo_res:
        st.error("ZIP code not found. Try another.")
        st.stop()

    lat = geo_res[0]["lat"]
    lon = geo_res[0]["lon"]

    tags = "|".join([kw.strip() for kw in keywords.split(",") if kw.strip()])
    filter_enabled = bool(tags)

    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
      way["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
      relation["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
    );
    out center;
    """

    try:
        res = requests.post("https://overpass-api.de/api/interpreter", data={"data": overpass_query})
        res.raise_for_status()
        data = res.json().get("elements", [])
    except Exception as e:
        st.error(f"Failed to get data from Overpass API: {e}")
        data = []

    filtered = []
    for place in data:
        name = place.get("tags", {}).get("name", "")
        if not name:
            continue

        if filter_enabled:
            if not any(kw.lower() in name.lower() for kw in tags.split("|")):
                continue

        lat = place.get("lat") or place.get("center", {}).get("lat")
        lon = place.get("lon") or place.get("center", {}).get("lon")
        address = place.get("tags", {}).get("addr:full", "Unknown")
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

if not log_df.empty:
    st.markdown("### Visit Log")
    st.dataframe(log_df)
