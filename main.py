import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from opencage.geocoder import OpenCageGeocode
import folium
from dotenv import load_dotenv
import os
import json
import csv
from datetime import datetime
import webbrowser

# Load environment variables
load_dotenv()
key = os.getenv("OPENCAGE_API_KEY")
if not key:
    raise ValueError("OPENCAGE_API_KEY not found in .env file")

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

def save_history(number, location, detailed_location, service_provider, time_zone, lat, lng):
    history.append({
        "number": number,
        "country": location,
        "detailed_location": detailed_location if detailed_location else "Not available",
        "service_provider": service_provider if service_provider else "Unknown",
        "time_zone": str(time_zone) if time_zone else "Unknown",
        "latitude": lat,
        "longitude": lng,
        "timestamp": datetime.now().isoformat()
    })
    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)

def view_history():
    if not history:
        print("No history available.")
        return
    for entry in history:
        print(f"Number: {entry['number']}, Time: {entry['timestamp']}")
        print(f"Country: {entry['country']}, Location: {entry['detailed_location']}")
        print(f"Provider: {entry['service_provider']}, Time Zone: {entry['time_zone']}")
        print(f"Coordinates: ({entry['latitude']}, {entry['longitude']})\n")

def view_history_map():
    if not history:
        print("No history available to map.")
        return
    # Create a map centered on the first historical location
    first_entry = history[0]
    myMap = folium.Map(location=[first_entry["latitude"], first_entry["longitude"]], zoom_start=3)
    for entry in history:
        folium.Marker(
            [entry["latitude"], entry["longitude"]],
            popup=f"{entry['number']} ({entry['detailed_location']}, {entry['country']})",
            icon=folium.Icon(color="blue")
        ).add_to(myMap)
    myMap.save("history_map.html")
    print("History map saved as history_map.html")
    webbrowser.open("history_map.html")

def clear_history():
    global history
    history = []
    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)
    print("History cleared.")

def export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng):
    filename = "phone_lookup_export.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Phone Number", "Country", "Detailed Location", "Service Provider", "Time Zone", "Latitude", "Longitude", "Timestamp"])
        writer.writerow([number, location, detailed_location if detailed_location else "N/A", 
                        service_provider if service_provider else "N/A", str(time_zone) if time_zone else "N/A", 
                        lat, lng, datetime.now().isoformat()])

# Get phone number from user
while True:
    number = input("Enter phone number (with country code, e.g., +1234567890): ").strip()
    if not number.startswith("+"):
        print("Phone number must include country code (e.g., +1 for USA).")
        continue
    try:
        pepnumber = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(pepnumber):
            print("Invalid phone number. Please try again.")
            continue
        break
    except phonenumbers.NumberParseException:
        print("Error parsing phone number. Ensure it includes a valid country code.")
        continue

# Get location details
location = geocoder.country_name_for_number(pepnumber, "en")
detailed_location = geocoder.description_for_number(pepnumber, "en")
service_provider = carrier.name_for_number(pepnumber, "en")
time_zone = timezone.time_zones_for_number(pepnumber)

# Build geocoding query
query = detailed_location if detailed_location else location
if detailed_location and location:
    query = f"{detailed_location}, {location}"

# Check cache for geocoding result
if query in cache:
    lat, lng = cache[query]["lat"], cache[query]["lng"]
    confidence = cache[query].get("confidence", "N/A")
    print("Using cached coordinates.")
else:
    try:
        geocoder_api = OpenCageGeocode(key)
        results = geocoder_api.geocode(query)
        if results and len(results):
            lat = results[0]["geometry"]["lat"]
            lng = results[0]["geometry"]["lng"]
            confidence = results[0].get("confidence", "N/A")
            cache[query] = {"lat": lat, "lng": lng, "confidence": confidence}
            save_cache()
        else:
            print("Geocoding failed, no coordinates found.")
            exit()
    except Exception as e:
        print(f"Geocoding error: {str(e)}")
        exit()

# Save to history and export
save_history(number, location, detailed_location, service_provider, time_zone, lat, lng)
export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng)

# Print details
print(f"\nPhone Number: {number}")
print(f"Country and Location: {location} in {detailed_location if detailed_location else 'Not available'}")
print(f"Service Provider: {service_provider if service_provider else 'Unknown'}")
print(f"Time Zone: {time_zone if time_zone else 'Unknown'}")
print(f"Latitude and Longitude: {lat}, {lng}")
print(f"Geocoding Confidence: {confidence}")
print(f"Exact Location: https://www.google.com/maps/place/{lat},{lng}")

# Create and save map with style option
map_style = input("Choose map style (1: Standard, 2: Satellite, 3: Terrain): ").strip()
tiles = "OpenStreetMap"
if map_style == "2":
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
elif map_style == "3":
    tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"

zoom_level = 9 if detailed_location else 5
myMap = folium.Map(location=[lat, lng], zoom_start=zoom_level, tiles=tiles, attr="Map data © OpenStreetMap contributors, Esri")
folium.Marker([lat, lng], popup=query).add_to(myMap)
myMap.save("mylocation.html")
print("Map saved as mylocation.html")

# Open map in browser
webbrowser.open("mylocation.html")

# History options
while True:
    action = input("\nOptions: [v]iew history, [m]ap history, [c]lear history, [e]xit: ").lower()
    if action == "v":
        view_history()
    elif action == "m":
        view_history_map()
    elif action == "c":
        clear_history()
    elif action == "e":
        break
    else:
        print("Invalid option.")