import streamlit as st
import phonenumbers
from phonenumbers import geocoder, carrier, timezone, number_type
from opencage.geocoder import OpenCageGeocode
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
import os
import json
import csv
from datetime import datetime
import requests
import pandas as pd

# Global variables
global history

# Load environment variables
load_dotenv()
key = os.getenv("OPENCAGE_API_KEY")
if not key:
    st.error("OPENCAGE_API_KEY not found in .env file")
    st.stop()

# Load or initialize cache
cache_file = "geocode_cache.json"
try:
    with open(cache_file, "r") as f:
        content = f.read().strip()
        cache = json.loads(content) if content else {}
except (FileNotFoundError, json.JSONDecodeError):
    cache = {}

def save_cache():
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=4)

# Load or initialize history
history_file = "history.json"
try:
    with open(history_file, "r") as f:
        content = f.read().strip()
        history = json.loads(content) if content else []
except (FileNotFoundError, json.JSONDecodeError):
    history = []

def save_history(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location=None, confidence=None):
    entry = {
        "number": number,
        "country": location,
        "detailed_location": detailed_location if detailed_location else "Not available",
        "service_provider": service_provider if service_provider else "Unknown",
        "time_zone": str(time_zone) if time_zone else "Unknown",
        "latitude": lat,
        "longitude": lng,
        "number_type": number_type_str,
        "ip_location": ip_location if ip_location else "Not retrieved",
        "confidence": confidence if confidence else "N/A",
        "timestamp": datetime.now().isoformat()
    }
    history.append(entry)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)

def export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location=None, confidence=None):
    filename = "phone_lookup_export.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Phone Number", "Country", "Detailed Location", "Service Provider", "Time Zone", "Latitude", "Longitude", "Number Type", "IP Location", "Confidence", "Timestamp"])
        writer.writerow([number, location, detailed_location if detailed_location else "N/A", 
                        service_provider if service_provider else "N/A", str(time_zone) if time_zone else "N/A", 
                        lat, lng, number_type_str, ip_location if ip_location else "N/A", confidence if confidence else "N/A", datetime.now().isoformat()])
    return filename

def get_ip_location():
    try:
        response = requests.get("http://ip-api.com/json/", timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            city = data.get("city", "Unknown")
            region = data.get("regionName", "Unknown")
            country = data.get("country", "Unknown")
            return f"{city}, {region}, {country}"
        else:
            return "Unknown (IP-API failed)"
    except Exception as e:
        return f"Unknown (error: {str(e)})"

# Streamlit App
st.set_page_config(page_title="Phone Number Location Tracker", layout="wide")
st.title("📍 Phone Number Location Tracker")
st.markdown("Enter a phone number to view its registered location on an interactive map.")

# Input and Options
with st.container():
    st.subheader("Input")
    number = st.text_input("Enter Phone Number (e.g., +1234567890):", value="", key="phone_input")
    col1, col2 = st.columns([1, 1])
    with col1:
        map_style = st.radio("Map Style", ["Standard", "Satellite", "Terrain"], index=0)
    with col2:
        include_ip = st.checkbox("Include IP-Based Location", value=False)

# Track Number
if st.button("Track Number", type="primary"):
    if not number.startswith("+"):
        st.error("Phone number must include country code (e.g., +1 for USA).")
    else:
        with st.spinner("Processing..."):
            try:
                pepnumber = phonenumbers.parse(number)
                if not phonenumbers.is_valid_number(pepnumber):
                    st.error("Invalid phone number.")
                else:
                    # Get location details
                    location = geocoder.country_name_for_number(pepnumber, "en")
                    detailed_location = geocoder.description_for_number(pepnumber, "en")
                    service_provider = carrier.name_for_number(pepnumber, "en")
                    time_zone = timezone.time_zones_for_number(pepnumber)
                    number_type_id = number_type(pepnumber)
                    number_type_str = {0: "Unknown", 1: "Fixed line", 2: "Mobile", 3: "Fixed line or mobile"}.get(number_type_id, "Other")

                    # Build query
                    query = detailed_location if detailed_location else location
                    if detailed_location and location:
                        query = f"{detailed_location}, {location}"

                    # Cache or geocode
                    if query in cache:
                        lat, lng = cache[query]["lat"], cache[query]["lng"]
                        confidence = cache[query].get("confidence", "N/A")
                        bounds = cache[query].get("bounds", None)
                    else:
                        try:
                            geocoder_api = OpenCageGeocode(key)
                            results = geocoder_api.geocode(query)
                            if results and len(results):
                                lat = results[0]["geometry"]["lat"]
                                lng = results[0]["geometry"]["lng"]
                                confidence = results[0].get("confidence", "N/A")
                                bounds = results[0].get("bounds", None)
                                cache[query] = {"lat": lat, "lng": lng, "confidence": confidence, "bounds": bounds}
                                save_cache()
                            else:
                                st.error("Geocoding failed, no coordinates found.")
                                st.stop()
                        except Exception as e:
                            st.error(f"Geocoding error: {str(e)}")
                            st.stop()

                    # IP location
                    ip_location = None
                    if include_ip:
                        ip_location = get_ip_location()

                    # Save
                    save_history(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location, confidence)
                    csv_file = export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location, confidence)

                    # Display results
                    st.subheader("Results")
                    st.markdown(f"**Phone Number:** {number}")
                    st.markdown(f"**Type:** {number_type_str}")
                    st.markdown(f"**Country and Location:** {location} in {detailed_location if detailed_location else 'Not available'}")
                    st.markdown(f"**Service Provider:** {service_provider if service_provider else 'Unknown'}")
                    st.markdown(f"**Time Zone:** {time_zone if time_zone else 'Unknown'}")
                    st.markdown(f"**Latitude and Longitude:** {lat}, {lng}")
                    st.markdown(f"**Geocoding Confidence:** {confidence} (1-10, lower is better)")
                    if ip_location:
                        st.markdown(f"**IP Location:** {ip_location}")
                    st.markdown(f"**Map URL:** [Google Maps](https://www.google.com/maps/place/{lat},{lng})")

                    # Embed map
                    tiles = "OpenStreetMap"
                    if map_style == "Satellite":
                        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    elif map_style == "Terrain":
                        tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"

                    zoom_level = 9 if detailed_location else 5
                    my_map = folium.Map(location=[lat, lng], zoom_start=zoom_level, tiles=tiles, attr="Map data © OpenStreetMap contributors, Esri")
                    folium.Marker([lat, lng], popup=query, icon=folium.Icon(color="blue")).add_to(my_map)
                    # Add confidence radius if bounds available
                    if bounds:
                        ne = [bounds["northeast"]["lat"], bounds["northeast"]["lng"]]
                        sw = [bounds["southwest"]["lat"], bounds["southwest"]["lng"]]
                        folium.Rectangle(bounds=[sw, ne], color="blue", fill=True, fill_opacity=0.2, popup="Confidence Area").add_to(my_map)
                    if ip_location and ip_location != "Unknown (error fetching IP location)":
                        try:
                            geocoder_api = OpenCageGeocode(key)
                            ip_results = geocoder_api.geocode(ip_location)
                            if ip_results and len(ip_results):
                                ip_lat = ip_results[0]["geometry"]["lat"]
                                ip_lng = ip_results[0]["geometry"]["lng"]
                                folium.Marker([ip_lat, ip_lng], popup=f"IP Location: {ip_location}", icon=folium.Icon(color="green")).add_to(my_map)
                        except:
                            pass
                    st_folium(my_map, width=700, height=500)

                    st.download_button("Download CSV Export", data=open(csv_file, "r").read(), file_name=csv_file, type="primary")

            except phonenumbers.NumberParseException:
                st.error("Error parsing phone number. Ensure it starts with '+' and contains only digits.")

# History section
st.subheader("History")
filter_text = st.text_input("Filter by Number or Country:", value="", key="history_filter")
filtered_history = history
if filter_text:
    filtered_history = [
        entry for entry in history
        if filter_text.lower() in entry["number"].lower() or filter_text.lower() in entry["country"].lower()
    ]

if not filtered_history:
    st.write("No history available or no matches.")
else:
    df = pd.DataFrame(filtered_history)
    st.dataframe(
        df[["number", "number_type", "country", "detailed_location", "service_provider", "time_zone", "latitude", "longitude", "ip_location", "confidence", "timestamp"]],
        use_container_width=True
    )

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("View History Map", type="secondary"):
        if not history:
            st.info("No history available to map.")
        else:
            first_entry = history[0]
            hist_map = folium.Map(location=[first_entry["latitude"], first_entry["longitude"]], zoom_start=3)
            for entry in history:
                folium.Marker(
                    [entry["latitude"], entry["longitude"]],
                    popup=f"{entry['number']} ({entry['detailed_location']}, {entry['country']}), IP: {entry['ip_location']}",
                    icon=folium.Icon(color="blue")
                ).add_to(hist_map)
    if st.button("Clear History", type="secondary"):
        history = []
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
        st.success("History cleared.")
        st.rerun()
with col3:
    if st.button("Download Full History CSV", type="secondary"):
        history_csv = "full_history.csv"
        with open(history_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Phone Number", "Country", "Detailed Location", "Service Provider", "Time Zone", "Latitude", "Longitude", "Number Type", "IP Location", "Confidence", "Timestamp"])
            for entry in history:
                writer.writerow([entry["number"], entry["country"], entry["detailed_location"], 
                                 entry["service_provider"], entry["time_zone"], entry["latitude"], entry["longitude"], 
                                 entry["number_type"], entry["ip_location"], entry["confidence"], entry["timestamp"]])
        st.download_button("Download", data=open(history_csv, "r").read(), file_name=history_csv, type="primary")