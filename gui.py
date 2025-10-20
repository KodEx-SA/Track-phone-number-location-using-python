import phonenumbers
from phonenumbers import geocoder, carrier, timezone, number_type
from opencage.geocoder import OpenCageGeocode
import folium
from dotenv import load_dotenv
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import webbrowser
import json
import csv
from datetime import datetime
import re
import pyperclip
import requests

response = requests.get("https://api.ipgeolocation.io/ipgeo?apiKey=YOUR_API_KEY&ip=8.8.8.8")

# Load environment variables
load_dotenv()
key = os.getenv("OPENCAGE_API_KEY")
if not key:
    messagebox.showerror("Error", "OPENCAGE_API_KEY not found in .env file")
    exit()

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

def save_history(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location=None):
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
        "timestamp": datetime.now().isoformat()
    }
    history.append(entry)
    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)

def view_history(filter_text=""):
    history_text.delete(1.0, tk.END)
    if not history:
        history_text.insert(tk.END, "No history available.")
        return
    filtered_history = history
    if filter_text:
        filtered_history = [
            entry for entry in history
            if filter_text.lower() in entry["number"].lower() or filter_text.lower() in entry["country"].lower()
        ]
    if not filtered_history:
        history_text.insert(tk.END, f"No history entries match '{filter_text}'.")
        return
    for entry in filtered_history:
        history_text.insert(tk.END, f"Number: {entry['number']} ({entry['number_type']}), Time: {entry['timestamp']}\n")
        history_text.insert(tk.END, f"Country: {entry['country']}, Location: {entry['detailed_location']}\n")
        history_text.insert(tk.END, f"Provider: {entry['service_provider']}, Time Zone: {entry['time_zone']}\n")
        history_text.insert(tk.END, f"Coordinates: ({entry['latitude']}, {entry['longitude']})\n")
        history_text.insert(tk.END, f"IP Location: {entry['ip_location']}\n\n")

def view_history_map():
    if not history:
        messagebox.showinfo("Info", "No history available to map.")
        return
    first_entry = history[0]
    myMap = folium.Map(location=[first_entry["latitude"], first_entry["longitude"]], zoom_start=3)
    for entry in history:
        folium.Marker(
            [entry["latitude"], entry["longitude"]],
            popup=f"{entry['number']} ({entry['detailed_location']}, {entry['country']}), IP: {entry['ip_location']}",
            icon=folium.Icon(color="blue")
        ).add_to(myMap)
    myMap.save("history_map.html")
    status_var.set("History map saved as history_map.html")
    webbrowser.open("history_map.html")

def clear_history():
    global history
    history = []
    with open(history_file, "w") as f:
        json.dump(history, f, indent=4)
    status_var.set("History cleared.")
    view_history()

def export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location=None):
    filename = "phone_lookup_export.csv"
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Phone Number", "Country", "Detailed Location", "Service Provider", "Time Zone", "Latitude", "Longitude", "Number Type", "IP Location", "Timestamp"])
        writer.writerow([number, location, detailed_location if detailed_location else "N/A", 
                        service_provider if service_provider else "N/A", str(time_zone) if time_zone else "N/A", 
                        lat, lng, number_type_str, ip_location if ip_location else "N/A", datetime.now().isoformat()])
    status_var.set(f"Results exported to {filename}")

def clear_results():
    result_text.delete(1.0, tk.END)
    status_var.set("Results cleared.")
    map_url_var.set("")

def copy_map_url():
    if map_url_var.get():
        pyperclip.copy(map_url_var.get())
        status_var.set("Map URL copied to clipboard.")
    else:
        status_var.set("No map URL available to copy.")

def validate_phone_number(*args):
    number = entry.get().strip()
    if not number:
        entry.configure(bootstyle="default")
        status_var.set("")
        return
    if not number.startswith("+") or not re.match(r"^\+\d+$", number):
        entry.configure(bootstyle="danger")
        status_var.set("Phone number must start with '+' and contain only digits.")
    else:
        entry.configure(bootstyle="success")
        status_var.set("Phone number format looks good.")

def get_ip_location(): # IP Address location
    try:
        status_var.set("Fetching IP location...")
        root.update()
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
        status_var.set(f"IP location error: {str(e)}")
        return "Unknown (error fetching IP location)"

def track_number():
    number = entry.get().strip()
    if not number.startswith("+"):
        messagebox.showerror("Error", "Phone number must include country code (e.g., +1 for USA).")
        return
    try:
        pepnumber = phonenumbers.parse(number)
        if not phonenumbers.is_valid_number(pepnumber):
            messagebox.showerror("Error", "Invalid phone number.")
            return

        status_var.set("Processing phone number...")
        root.update()

        # Get location details
        location = geocoder.country_name_for_number(pepnumber, "en")
        detailed_location = geocoder.description_for_number(pepnumber, "en")
        service_provider = carrier.name_for_number(pepnumber, "en")
        time_zone = timezone.time_zones_for_number(pepnumber)
        number_type_id = number_type(pepnumber)
        number_type_str = {0: "Unknown", 1: "Fixed line", 2: "Mobile", 3: "Fixed line or mobile"}.get(number_type_id, "Other")

        # Build geocoding query
        query = detailed_location if detailed_location else location
        if detailed_location and location:
            query = f"{detailed_location}, {location}"

        # Check cache
        if query in cache:
            lat, lng = cache[query]["lat"], cache[query]["lng"]
            confidence = cache[query].get("confidence", "N/A")
            status_var.set("Using cached coordinates.")
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
                    messagebox.showerror("Error", "Geocoding failed, no coordinates found.")
                    status_var.set("")
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Geocoding error: {str(e)}")
                status_var.set("")
                return

        # Get IP location if enabled
        ip_location = None
        if ip_location_var.get():
            ip_location = get_ip_location()

        # Save to history and export
        save_history(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location)
        export_to_csv(number, location, detailed_location, service_provider, time_zone, lat, lng, number_type_str, ip_location)

        # Update result text
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Phone Number: {number}\n", "bold")
        result_text.insert(tk.END, f"Type: {number_type_str}\n")
        result_text.insert(tk.END, f"Country and Location: {location} in {detailed_location if detailed_location else 'Not available'}\n")
        result_text.insert(tk.END, f"Service Provider: {service_provider if service_provider else 'Unknown'}\n")
        result_text.insert(tk.END, f"Time Zone: {time_zone if time_zone else 'Unknown'}\n")
        result_text.insert(tk.END, f"Latitude and Longitude: {lat}, {lng}\n")
        result_text.insert(tk.END, f"Geocoding Confidence: {confidence}\n")
        if ip_location:
            result_text.insert(tk.END, f"IP Location: {ip_location}\n")
        result_text.insert(tk.END, f"Map URL: https://www.google.com/maps/place/{lat},{lng}\n", "link")
        map_url_var.set(f"https://www.google.com/maps/place/{lat},{lng}")

        # Configure text tags
        result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))
        result_text.tag_configure("link", foreground="blue", underline=1)
        result_text.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(map_url_var.get()))

        # Create and save map
        tiles = "OpenStreetMap"
        if map_style.get() == "satellite":
            tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        elif map_style.get() == "terrain":
            tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"

        zoom_level = 9 if detailed_location else 5
        myMap = folium.Map(location=[lat, lng], zoom_start=zoom_level, tiles=tiles, attr="Map data © OpenStreetMap contributors, Esri")
        folium.Marker([lat, lng], popup=query).add_to(myMap)
        if ip_location and ip_location != "Unknown (error fetching IP location)":
            try:
                ip_results = geocoder_api.geocode(ip_location)
                if ip_results and len(ip_results):
                    ip_lat = ip_results[0]["geometry"]["lat"]
                    ip_lng = ip_results[0]["geometry"]["lng"]
                    folium.Marker([ip_lat, ip_lng], popup=f"IP Location: {ip_location}", icon=folium.Icon(color="green")).add_to(myMap)
            except:
                pass  # Skip IP marker if geocoding fails
        myMap.save("mylocation.html")
        webbrowser.open("mylocation.html")
        status_var.set("Map saved as mylocation.html")

    except phonenumbers.NumberParseException:
        messagebox.showerror("Error", "Error parsing phone number. Ensure it starts with '+' and contains only digits.")
        status_var.set("")

# Set up GUI
root = ttk.Window(themename="flatly")
root.title("Phone Number Location Tracker")
root.geometry("500x850")
root.resizable(True, True)

# Main frame
main_frame = ttk.Frame(root, padding=10)
main_frame.pack(fill="both", expand=True)

# Input frame
input_frame = ttk.LabelFrame(main_frame, text="Phone Number Input", padding=10)
input_frame.pack(fill="x", pady=5)
ttk.Label(input_frame, text="Enter Phone Number with country code (e.g. +27):").pack(anchor="w")
entry = ttk.Entry(input_frame, width=40)
entry.pack(pady=5)
entry.bind("<KeyRelease>", validate_phone_number)

# Options frame
options_frame = ttk.LabelFrame(main_frame, text="Options", padding=10)
options_frame.pack(fill="x", pady=5)
map_style = tk.StringVar(value="standard")
ttk.Radiobutton(options_frame, text="Standard Map", variable=map_style, value="standard", bootstyle="primary").pack(anchor="w")
ttk.Radiobutton(options_frame, text="Satellite View", variable=map_style, value="satellite", bootstyle="primary").pack(anchor="w")
ttk.Radiobutton(options_frame, text="Terrain View", variable=map_style, value="terrain", bootstyle="primary").pack(anchor="w")
# IP Address location
ip_location_var = tk.BooleanVar(value=False)
ttk.Checkbutton(options_frame, text="Include IP-Based Location", variable=ip_location_var, bootstyle="info").pack(anchor="w", pady=5)

# Buttons frame
buttons_frame = ttk.Frame(main_frame)
buttons_frame.pack(fill="x", pady=10)
ttk.Button(buttons_frame, text="Track Number", command=track_number, bootstyle="success").pack(side="left", padx=5)
ttk.Button(buttons_frame, text="Clear Results", command=clear_results, bootstyle="warning").pack(side="left", padx=5)
ttk.Button(buttons_frame, text="Copy Map URL", command=copy_map_url, bootstyle="info").pack(side="left", padx=5)

# Results frame
results_frame = ttk.LabelFrame(main_frame, text="Results", padding=10)
results_frame.pack(fill="both", expand=True, pady=5)
result_text = tk.Text(results_frame, height=12, width=50, font=("Helvetica", 10))
result_text.pack(fill="both", expand=True)

# History filter frame
history_filter_frame = ttk.LabelFrame(main_frame, text="History Filter", padding=10)
history_filter_frame.pack(fill="x", pady=5)
ttk.Label(history_filter_frame, text="Filter by Number or Country:").pack(anchor="w")
filter_entry = ttk.Entry(history_filter_frame, width=40)
filter_entry.pack(pady=5)
filter_entry.bind("<KeyRelease>", lambda e: view_history(filter_entry.get()))

# History frame
history_frame = ttk.LabelFrame(main_frame, text="History", padding=10)
history_frame.pack(fill="both", expand=True, pady=5)
history_text = scrolledtext.ScrolledText(history_frame, height=10, width=50, font=("Helvetica", 10))
history_text.pack(fill="both", expand=True)

# History buttons frame
history_buttons_frame = ttk.Frame(main_frame)
history_buttons_frame.pack(fill="x", pady=5)
ttk.Button(history_buttons_frame, text="View History", command=lambda: view_history(filter_entry.get()), bootstyle="primary").pack(side="left", padx=5)
ttk.Button(history_buttons_frame, text="View History Map", command=view_history_map, bootstyle="primary").pack(side="left", padx=5)
ttk.Button(history_buttons_frame, text="Clear History", command=clear_history, bootstyle="danger").pack(side="left", padx=5)

# Status bar
status_var = tk.StringVar(value="Ready")
map_url_var = tk.StringVar(value="")
status_bar = ttk.Label(main_frame, textvariable=status_var, relief="sunken", anchor="w", padding=5)
status_bar.pack(fill="x", side="bottom")

root.mainloop()