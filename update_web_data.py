import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import glob
import requests


def get_weather_condition(district=None):
    """Get current weather condition for Kathmandu, Nepal"""
    try:
        # OpenWeatherMap API for Kathmandu (you need to replace with your own API key)
        # Sign up at https://openweathermap.org/api to get a free API key
        api_key = "YOUR_API_KEY" # Replace with your actual API key
        city = "Kathmandu,np"
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        # If API key is not set, return sample data
        if api_key == "YOUR_API_KEY":
            print("Warning: Using sample weather data. Please set your OpenWeatherMap API key")
            return {
                "condition": "Partly Cloudy",
                "temperature": 25,
                "humidity": 65,
                "wind": 12,
                "city": "Kathmandu"
            }
            
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather = {
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "temperature": round(data["main"]["temp"]),
                "humidity": data["main"]["humidity"],
                "wind": round(data["wind"]["speed"]),
                "city": "Kathmandu"
            }
            return weather
        else:
            print(f"Error fetching weather data: {response.status_code}")
            # Fallback to sample data
            return {
                "condition": "Partly Cloudy",
                "temperature": 25,
                "humidity": 65,
                "wind": 12,
                "city": "Kathmandu"
            }
    except Exception as e:
        print(f"Error getting weather data: {e}")
        return {
            "condition": "Partly Cloudy",
            "temperature": 25,
            "humidity": 65,
            "wind": 12, 
            "city": "Kathmandu"
        }


def calculate_fire_trend():
    """Calculate fire trend by comparing with previous day"""
    try:
        # Get today's date and yesterday's date
        today = datetime.now().strftime('%Y%m%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        # Path to today's and yesterday's fire reports
        today_excel = f"fire_reports/nepal_daily_fire_report_{today}.xlsx"
        yesterday_excel = f"fire_reports/nepal_daily_fire_report_{yesterday}.xlsx"
        
        # If no report for yesterday, check for any previous reports
        if not os.path.exists(yesterday_excel):
            files = glob.glob("fire_reports/nepal_daily_fire_report_*.xlsx")
            files.sort(reverse=True)
            if len(files) > 1:  # If we have more than just today's file
                yesterday_excel = files[1]  # Second most recent file
            else:
                return {"change": 0, "direction": "same"}

        # Read the Excel files
        today_df = pd.read_excel(today_excel)
        yesterday_df = pd.read_excel(yesterday_excel)
        
        # Calculate total fires (excluding "Total" row)
        today_fires = today_df[today_df["District"] != "Total"]["Fire Count"].sum()
        yesterday_fires = yesterday_df[yesterday_df["District"] != "Total"]["Fire Count"].sum()
        
        # Calculate percentage change
        if yesterday_fires == 0:
            if today_fires > 0:
                return {"change": 100, "direction": "up"}
            else:
                return {"change": 0, "direction": "same"}
        
        change_pct = ((today_fires - yesterday_fires) / yesterday_fires) * 100
        
        direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "same"
        
        return {"change": abs(round(change_pct)), "direction": direction}
    
    except Exception as e:
        print(f"Error calculating fire trend: {e}")
        return {"change": 0, "direction": "same"}


def get_confidence_levels(excel_path):
    """Extract confidence from fire data JSON file"""
    try:
        # Get the date from the Excel file name
        date_str = os.path.basename(excel_path).replace("nepal_daily_fire_report_", "").replace(".xlsx", "")
        confidence_file = f"fire_reports/fire_confidence_{date_str}.json"
        
        # Check if confidence file exists
        if os.path.exists(confidence_file):
            with open(confidence_file, 'r') as f:
                confidence_data = json.load(f)
                return confidence_data
        else:
            print(f"Confidence file not found: {confidence_file}")
            # If the file doesn't exist, provide default values
            return {
                "average": 80,
                "median": 85,
                "high_confidence_pct": 70,
                "confidence_distribution": {
                    "low": 10,
                    "medium": 20, 
                    "high": 70
                }
            }
    except Exception as e:
        print(f"Error getting confidence levels: {e}")
        return {
            "average": 80,
            "median": 85,
            "high_confidence_pct": 70
        }


def update_today_json():
    """Update today.json with the latest fire report data"""
    today = datetime.now().strftime('%Y%m%d')
    
    # Paths to the latest report files
    map_path = f"fire_reports/nepal_daily_fire_map_{today}.jpg"
    excel_path = f"fire_reports/nepal_daily_fire_report_{today}.xlsx"
    pdf_path = f"fire_reports/nepal_daily_fire_report_{today}.pdf"
    
    # Check if files exist
    if not (os.path.exists(map_path) and os.path.exists(excel_path) and os.path.exists(pdf_path)):
        print("Error: Today's fire report files not found.")
        return False
        
    # Read Excel file to get fire statistics
    try:
        df = pd.read_excel(excel_path)
        
        # Get total fires (excluding "Total" row)
        total_fires = df[df["District"] != "Total"]["Fire Count"].sum()
        
        # Get top district
        district_rows = df[df["District"] != "Total"]
        if not district_rows.empty:
            top_district = district_rows.sort_values("Fire Count", ascending=False).iloc[0]
            top_district_name = f"{top_district['District']} ({top_district['Fire Count']} fires)"
        else:
            top_district_name = "None (0 fires)"
            
        # Format date
        today_date = datetime.now().strftime('%Y-%m-%d')
        formatted_date = datetime.now().strftime('%d %B %Y')
        last_updated = datetime.now().strftime('%d %b %Y, %H:%M:%S')
        
        # Get additional statistics
        fire_trend = calculate_fire_trend()
        weather = get_weather_condition()
        confidence = get_confidence_levels(excel_path)
        
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return False
    
    # Create today.json data
    today_data = {
        "date": formatted_date,
        "last_updated": last_updated,
        "map_url": map_path.replace("\\", "/"),
        "stats": {
            "total_fires": int(total_fires),
            "top_district": top_district_name,
            "protected_areas": "Data not available",
            "satellite": "MODIS 1km",
            "fire_trend": fire_trend,
            "weather": weather,
            "confidence": confidence
        },
        "reports": {
            "pdf": pdf_path.replace("\\", "/"),
            "xlsx": excel_path.replace("\\", "/")
        },
        "year": datetime.now().year,
        "archive": []
    }
    
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    
    # Save today.json
    with open("data/today.json", "w") as f:
        json.dump(today_data, f, indent=2)
    
    # Update archive.json
    update_archive_json(today_date, map_path, pdf_path, excel_path, top_district_name.split(" (")[0])
    
    print(f"Updated today.json with data from {today}")
    return True


def update_archive_json(date, map_path, pdf_path, excel_path, district):
    """Update archive.json with new entry"""
    archive_file = "data/archive.json"
    
    if os.path.exists(archive_file) and os.path.getsize(archive_file) > 0:
        with open(archive_file, "r") as f:
            try:
                archive = json.load(f)
            except json.JSONDecodeError:
                archive = []
    else:
        archive = []
    
    # Create new entry
    new_entry = {
        "date": date,
        "map_url": map_path.replace("\\", "/"),
        "pdf": pdf_path.replace("\\", "/"),
        "xlsx": excel_path.replace("\\", "/"),
        "district": district
    }
    
    # Check if entry for this date already exists
    for i, entry in enumerate(archive):
        if entry["date"] == date:
            archive[i] = new_entry
            break
    else:
        # Entry doesn't exist, add it
        archive.append(new_entry)
    
    # Sort archive by date (newest first)
    archive = sorted(archive, key=lambda x: x["date"], reverse=True)
    
    # Save archive.json
    with open(archive_file, "w") as f:
        json.dump(archive, f, indent=2)
    
    print(f"Updated archive.json with entry for {date}")


if __name__ == "__main__":
    update_today_json() 