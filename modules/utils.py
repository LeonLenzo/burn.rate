import pandas as pd
import base64
import json
import streamlit as st
from datetime import date

class NutritionCalculator:
    @staticmethod
    def calculate_nutrition(base_values, weight_in_grams):
        """
        Calculate nutrition values based on weight
        Base values are per 100g, so multiply by weight/100
        """
        factor = weight_in_grams / 100
        return {k: v * factor for k, v in base_values.items()}

def format_date(date_obj):
    """Format a date object to string format YYYY-MM-DD"""
    return date_obj.strftime("%Y-%m-%d")

def get_current_date_str():
    """Get the current date as a string in YYYY-MM-DD format"""
    return format_date(date.today())

def export_logs_as_download_link(logs):
    """
    Create a download link for exporting food logs
    Returns HTML for a download link
    """
    logs_json = json.dumps(logs)
    b64 = base64.b64encode(logs_json.encode()).decode()
    href = f'<a href="data:file/json;base64,{b64}" download="food_logs_export.json">Download Food Logs</a>'
    return href

def import_logs_from_uploaded_file(uploaded_file, existing_logs):
    """
    Import logs from an uploaded JSON file and merge with existing logs
    Returns (success, message, merged_logs)
    """
    try:
        imported_logs = json.load(uploaded_file)
        
        # Validate imported logs
        if not isinstance(imported_logs, dict):
            return False, "Invalid format: logs must be a dictionary", existing_logs
        
        # Merge with existing logs
        merged_logs = existing_logs.copy()
        for date, entries in imported_logs.items():
            if date in merged_logs:
                # Append new entries to existing date
                merged_logs[date].extend(entries)
            else:
                # Add new date entries
                merged_logs[date] = entries
        
        return True, "Food logs imported successfully!", merged_logs
    except Exception as e:
        return False, f"Error importing logs: {e}", existing_logs

def calculate_daily_totals(log_entries):
    """
    Calculate daily nutrition totals from log entries
    Returns a dictionary with total values
    """
    if not log_entries:
        return {
            "calories": 0,
            "protein": 0,
            "fat": 0,
            "carbs": 0
        }
    
    return {
        "calories": sum(entry['total_calories'] for entry in log_entries),
        "protein": sum(entry['total_protein'] for entry in log_entries),
        "fat": sum(entry['total_fat'] for entry in log_entries),
        "carbs": sum(entry['total_carbs'] for entry in log_entries)
    }