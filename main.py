import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from phone import number
from opencage.geocoder import OpenCageGeocode
import folium
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the API key from .env
key = os.getenv("OPENCAGE_API_KEY")
if not key:
    raise ValueError("OPENCAGE_API_KEY not found in .env file")

# Parse the phone number
pepnumber = phonenumbers.parse(number)

# Get country name and detailed location (e.g., city or region)
location = geocoder.country_name_for_number(pepnumber, "en")
detailed_location = geocoder.description_for_number(pepnumber, "en")

# Get service provider and time zone
service_provider = carrier.name_for_number(pepnumber, "en")
time_zone = timezone.time_zones_for_number(pepnumber)

# Set up OpenCage Geocoder
geocoder_api = OpenCageGeocode(key)

# Build query: prefer detailed location with country for accuracy
query = detailed_location if detailed_location else location
if detailed_location and location:
    query = f"{detailed_location}, {location}"

# Geocode the location
results = geocoder_api.geocode(query)

if results and len(results):
    lat = results[0]['geometry']['lat']
    lng = results[0]['geometry']['lng']
    
    # Print details
    print(f"Phone Number: {number}")
    print(f"Country and Location: {location} in {detailed_location if detailed_location else 'Not available'}")
    print(f"Service Provider: {service_provider}")
    print(f"Time Zone: {time_zone}")
    print(f"Latitude and Longitude: {lat}, {lng}")
    print(f"Exact Location: https://www.google.com/maps/place/{lat},{lng}")

    # Create map centered on coordinates and adjust zoom
    myMap = folium.Map(location=[lat, lng], zoom_start=9)
    folium.Marker([lat, lng], popup=query).add_to(myMap)  # Add marker for location

    # Save map to HTML file
    myMap.save("mylocation.html")
    print("Map saved!")
else:
    print("Geocoding failed, No coordinates")