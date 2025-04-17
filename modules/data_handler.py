import streamlit as st
import pandas as pd
import json
import os
from fuzzywuzzy import process, fuzz

@st.cache_data
def load_food_database():
    """
    Load and process the AUSNUT food database
    Returns a pandas DataFrame with the processed food data
    """
    try:
        # Load the AUSNUT CSV file
        df = pd.read_csv("ausnut_database.csv")
        
        # Convert energy from kJ to calories (1 kJ = 0.239 kcal)
        df['Calories'] = df['Energy, with dietary fibre (kJ)'] * 0.239
        df['Calories'] = df['Calories'].round().astype(int)
        
        # Create a simplified dataframe with just the columns we need
        food_db = pd.DataFrame({
            'FoodID': df['Food ID'],
            'FoodName': df['Food Name'],
            'Calories': df['Calories'],  # Calories per 100g
            'Protein': df['Protein (g)'],  # per 100g
            'Fat': df['Total fat (g)'],  # per 100g
            'Carbs': df['Available carbohydrates, with sugar alcohols (g)']  # per 100g
        })
        
        return food_db
    except Exception as e:
        st.error(f"Failed to load AUSNUT database: {e}")
        return None

def load_food_logs():
    """
    Load food logs from the JSON file
    Returns a dictionary of food logs by date
    """
    try:
        if os.path.exists('food_logs.json') and os.path.getsize('food_logs.json') > 0:
            with open('food_logs.json', 'r') as f:
                logs = json.load(f)
                
                # Validate and clean logs
                valid_logs = {}
                for date, entries in logs.items():
                    valid_logs[date] = [entry for entry in entries if validate_food_entry(entry)]
                
                return valid_logs
        else:
            return {}
    except json.JSONDecodeError:
        st.warning("Food log file is corrupted. Starting with a new log.")
        return {}
    except Exception as e:
        st.warning(f"Couldn't load food logs: {e}. Starting with a new log.")
        return {}

def save_food_logs(logs):
    """
    Save food logs to the JSON file
    Returns True if successful, False otherwise
    """
    try:
        with open('food_logs.json', 'w') as f:
            json.dump(logs, f)
        return True
    except Exception as e:
        st.error(f"Failed to save food log: {e}")
        return False

def validate_food_entry(entry):
    """
    Validate that a food entry has all required fields
    Returns True if valid, False otherwise
    """
    required_fields = ['food_id', 'food_name', 'weight_g', 'total_calories']
    return all(field in entry for field in required_fields)

def search_foods(query, food_db, limit=20):
    """
    Fuzzy search for foods matching the query using fuzzywuzzy
    Returns a filtered DataFrame with foods that best match the query
    """
    if not query or len(query.strip()) < 2:
        return pd.DataFrame()
        
    query = query.lower().strip()
    
    # Step 1: Exact matches (highest priority)
    exact_matches = food_db[food_db['FoodName'].str.lower() == query]
    if not exact_matches.empty:
        return exact_matches
    
    # Step 2: Use fuzzywuzzy for fuzzy string matching
    # Get all food names
    food_names = food_db['FoodName'].tolist()
    
    # Use process.extract to find the best matches
    # This returns a list of tuples (match, score, index)
    matches = process.extract(
        query,
        food_names,
        limit=limit,
        scorer=fuzz.token_sort_ratio  # This handles word order differences
    )
    
    # Filter matches with a score above a threshold (e.g., 60)
    good_matches = [match for match in matches if match[1] >= 60]
    
    if good_matches:
        # Get the food names of good matches
        matched_names = [match[0] for match in good_matches]
        
        # Filter the food_db to include only these matches
        result = food_db[food_db['FoodName'].isin(matched_names)].copy()
        
        # Add the match score as a column for sorting
        result['match_score'] = 0
        for i, row in result.iterrows():
            for match in good_matches:
                if row['FoodName'] == match[0]:
                    result.at[i, 'match_score'] = match[1]
                    break
        
        # Sort by match score (descending)
        result = result.sort_values('match_score', ascending=False)
        
        # Remove the match_score column before returning
        return result.drop(columns=['match_score'])
    
    # If no good matches, try a more lenient approach with partial_ratio
    # This is good for finding substrings
    partial_matches = process.extract(
        query,
        food_names,
        limit=limit,
        scorer=fuzz.partial_ratio
    )
    
    # Filter matches with a higher threshold for partial matching
    good_partial_matches = [match for match in partial_matches if match[1] >= 75]
    
    if good_partial_matches:
        # Get the food names of good partial matches
        matched_names = [match[0] for match in good_partial_matches]
        
        # Filter the food_db to include only these matches
        result = food_db[food_db['FoodName'].isin(matched_names)].copy()
        
        # Add the match score as a column for sorting
        result['match_score'] = 0
        for i, row in result.iterrows():
            for match in good_partial_matches:
                if row['FoodName'] == match[0]:
                    result.at[i, 'match_score'] = match[1]
                    break
        
        # Sort by match score (descending)
        result = result.sort_values('match_score', ascending=False)
        
        # Remove the match_score column before returning
        return result.drop(columns=['match_score'])
    
    # If still no matches, return empty DataFrame
    return pd.DataFrame()

# This function is no longer needed as we're removing category filtering