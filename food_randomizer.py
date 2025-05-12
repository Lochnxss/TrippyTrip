
import streamlit as st
import sqlite3
import pandas as pd
import random
import requests
import time
from datetime import datetime
from hashlib import sha256

st.set_page_config(page_title="The Grazing Trail", layout="wide")

# Initialize DB
conn = sqlite3.connect("grazing_trail.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    place TEXT,
    lat REAL,
    lon REAL,
    timestamp TEXT
)
""")
conn.commit()

if "user" not in st.session_state:
    st.session_state.user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "last_place" not in st.session_state:
    st.session_state.last_place = None

def hash_pw(pw):
    return sha256(pw.encode()).hexdigest()

def register(username, pw):
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_pw(pw)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login(username, pw):
    cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, hash_pw(pw)))
    row = cur.fetchone()
    if row:
        st.session_state.user = username
        st.session_state.user_id = row[0]
        return True
    return False

auth_tab, trail_tab, log_tab, board_tab = st.tabs(["Login/Register", "Trail Start", "My Trail", "Leaderboard"])

with auth_tab:
    st.title("Welcome to The Grazing Trail")
    option = st.radio("Select", ["Login", "Create Account"])
    username = st.text_input("Screen Name")
    password = st.text_input("Password", type="password")
    if st.button("Submit"):
        if option == "Create Account":
            if register(username, password):
                st.success("Account created. Please log in.")
            else:
                st.error("Username already taken.")
        else:
            if login(username, password):
                st.success(f"Welcome back, {username}!")
            else:
                st.error("Invalid login.")

def normalize(word):
    word = word.lower().strip()
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word

intent_map = {
    "pancake": ["pancake", "breakfast", "diner", "waffle", "ihop"],
    "steak": ["steak", "steakhouse", "bbq", "grill"],
    "pizza": ["pizza", "italian"],
    "sushi": ["sushi", "japanese", "ramen"],
    "burger": ["burger", "grill", "fast food"],
    "coffee": ["coffee", "cafe", "espresso"]
}

with trail_tab:
    if not st.session_state.user:
        st.info("👣 Please log in to begin your Grazing Trail.")
    else:
        zip_code = st.text_input("ZIP Code")
        keywords = st.text_input("Keywords (comma-separated)")
        if st.button("Find Me a Place"):
            st.markdown("### Bigfoot is scouting your trail...")
            time.sleep(3)

            geo = requests.get(f"https://api.opencagedata.com/geocode/v1/json?q={zip_code}&key=14334e30b2f64ed991640bbf6d1aacff").json()
            if not geo["results"]:
                st.error("Invalid ZIP")
                st.stop()
            lat = geo["results"][0]["geometry"]["lat"]
            lon = geo["results"][0]["geometry"]["lng"]

            cur.execute("SELECT place FROM visits WHERE user_id=?", (st.session_state.user_id,))
            visited = [row[0] for row in cur.fetchall()]

            raw = [normalize(x) for x in keywords.split(",") if x.strip()]
            terms = set()
            for kw in raw:
                terms.update(intent_map.get(kw, [kw]))

            query = f"""
[out:json][timeout:25];
(
  node["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
  way["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
  relation["amenity"~"restaurant|bar|pub"](around:5000,{lat},{lon});
);
out center;
"""
            r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
            places = r.json()["elements"]

            results = []
            for p in places:
                name = p.get("tags", {}).get("name", "")
                if not name or name in visited:
                    continue
                fields = " ".join(p.get("tags", {}).values()).lower()
                if any(t in fields for t in terms):
                    results.append({
                        "place": name,
                        "lat": p.get("lat") or p.get("center", {}).get("lat"),
                        "lon": p.get("lon") or p.get("center", {}).get("lon")
                    })

            if results:
                st.session_state.last_place = random.choice(results)
                st.success("Bigfoot found a spot! Check 'My Trail'")
            else:
                st.warning("No matching places found.")

with log_tab:
    if st.session_state.user and st.session_state.last_place:
        p = st.session_state.last_place
        st.subheader("Trail Recommendation")
        st.write(f"**{p['place']}** ({p['lat']}, {p['lon']})")
        if st.button("Mark as Visited"):
            cur.execute("INSERT INTO visits (user_id, place, lat, lon, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (st.session_state.user_id, p["place"], p["lat"], p["lon"], datetime.now().isoformat()))
            conn.commit()
            st.session_state.last_place = None
            st.success("Logged!")

        cur.execute("SELECT place, timestamp FROM visits WHERE user_id=? ORDER BY timestamp DESC", (st.session_state.user_id,))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=["Place", "Visited"])
            st.dataframe(df)

with board_tab:
    st.header("Trail Leaderboard")
    cur.execute("SELECT u.username, COUNT(v.id) as count FROM users u LEFT JOIN visits v ON u.id = v.user_id GROUP BY u.username ORDER BY count DESC")
    data = cur.fetchall()
    df = pd.DataFrame(data, columns=["User", "Total Visits"])
    df["Highlight"] = df["User"].apply(lambda x: "🌟" if x == st.session_state.user else "")
    st.dataframe(df[["Highlight", "User", "Total Visits"]])

# Chyron
cur.execute("SELECT u.username, v.place FROM visits v JOIN users u ON u.id = v.user_id ORDER BY v.timestamp DESC LIMIT 5")
ticker_data = cur.fetchall()
if ticker_data:
    chyron = " | ".join([f"{u} visited '{p}'" for u, p in ticker_data])
    st.markdown(f"<div style='position:fixed;bottom:0;width:100%;background:#333;color:white;padding:5px;font-size:14px'>{chyron}</div>", unsafe_allow_html=True)
