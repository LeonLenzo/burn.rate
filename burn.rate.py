import streamlit as st
import pandas as pd
from datetime import date
import json
import os
import re

# Set page configuration
st.set_page_config(
    page_title="burn.rate",
    page_icon="🔥",
    layout="centered"
)

# App title and description
st.markdown("<h1 style='text-align: center;'>🔥 burn.rate 🔥</h1>", unsafe_allow_html=True)
st.markdown("---")


# Initialize or load session state for food logs
if 'food_logs' not in st.session_state:
    try:
        if os.path.exists('food_logs.json') and os.path.getsize('food_logs.json') > 0:
            with open('food_logs.json', 'r') as f:
                st.session_state.food_logs = json.load(f)
        else:
            st.session_state.food_logs = {}
    except json.JSONDecodeError:
        st.warning("Food log file is corrupted. Starting with a new log.")
        st.session_state.food_logs = {}
    except Exception as e:
        st.warning(f"Couldn't load food logs: {e}. Starting with a new log.")
        st.session_state.food_logs = {}

# Function to load AUSNUT data
@st.cache_data
def load_food_database():
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

# Load food database
try:
    food_db = load_food_database()
except Exception as e:
    st.error(f"Failed to load AUSNUT database: {e}")
    st.stop()

# Date selection
selected_date = st.date_input("Select date", date.today(), key="date_selector")
date_str = selected_date.strftime("%Y-%m-%d")

# Initialize food log for selected date if it doesn't exist
if date_str not in st.session_state.food_logs:
    st.session_state.food_logs[date_str] = []

# Set default calorie goal
if 'daily_goal' not in st.session_state:
    st.session_state.daily_goal = 2000

# Display summary at the top of the app
st.subheader(f"{selected_date.strftime('%A, %B %d')}")

# Get the log entries for the selected date
log_entries = st.session_state.food_logs.get(date_str, [])

# Calculate daily nutrition totals
total_daily_calories = sum(entry['total_calories'] for entry in log_entries) if log_entries else 0
total_daily_protein = sum(entry['total_protein'] for entry in log_entries) if log_entries else 0
total_daily_fat = sum(entry['total_fat'] for entry in log_entries) if log_entries else 0
total_daily_carbs = sum(entry['total_carbs'] for entry in log_entries) if log_entries else 0

# Layout for daily goal adjustment and summary
col1, col2 = st.columns([1, 3])

with col1:
    st.session_state.daily_goal = st.number_input(
        "Goal",
        min_value=500,
        max_value=5000,
        value=st.session_state.daily_goal,
        step=100,
        key="daily_goal_input"
    )

with col2:
    # Display daily summary with custom CSS for better mobile layout
    st.markdown("""
    <style>
        .metric-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .metric-box {
            background-color: #f0f2f6;
            border-radius: 5px;
            padding: 10px;
            text-align: center;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #555;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.2rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    # Then replace your metrics section with:
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-box">
            <div class="metric-label">Calories</div>
            <div class="metric-value">{int(total_daily_calories)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Protein</div>
            <div class="metric-value">{total_daily_protein:.1f}g</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Fat</div>
            <div class="metric-value">{total_daily_fat:.1f}g</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">Carbs</div>
            <div class="metric-value">{total_daily_carbs:.1f}g</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Daily calorie target progress
daily_goal = st.session_state.daily_goal
st.progress(min(total_daily_calories / daily_goal, 1.0))
st.divider()

# Function to calculate nutritional values based on weight
def calculate_nutrition(base_values, weight_in_grams):
    # Base values are per 100g, so multiply by weight/100
    factor = weight_in_grams / 100
    return {k: v * factor for k, v in base_values.items()}

# Function to add food to log
def add_food_to_log(food, weight):
    # Calculate nutrition based on weight
    nutrition = calculate_nutrition({
        'calories': float(food['Calories']),
        'protein': float(food['Protein']),
        'fat': float(food['Fat']), 
        'carbs': float(food['Carbs'])
    }, weight)
    
    # Add food to log
    log_entry = {
        'food_id': str(food['FoodID']),
        'food_name': str(food['FoodName']),
        'weight_g': int(weight),
        'calories': int(food['Calories']),  # Per 100g
        'protein': float(food['Protein']),    # Per 100g
        'fat': float(food['Fat']),            # Per 100g
        'carbs': float(food['Carbs']),        # Per 100g
        'total_calories': int(nutrition['calories']),
        'total_protein': round(float(nutrition['protein']), 1),
        'total_fat': round(float(nutrition['fat']), 1),
        'total_carbs': round(float(nutrition['carbs']), 1),
        'time_added': pd.Timestamp.now().strftime("%H:%M")
    }
    
    st.session_state.food_logs[date_str].append(log_entry)
    
    # Save logs to file
    with open('food_logs.json', 'w') as f:
        json.dump(st.session_state.food_logs, f)
    
    st.success(f"Added {food['FoodName']} ({weight}g) to your log")
    st.rerun()

# Function to normalize text for better matching
def normalize_text(text):
    if pd.isna(text):
        return ""
    # Convert to lowercase, remove punctuation    
    return re.sub(r'[^\w\s]', '', str(text).lower())

# Create normalized food names for better searching
food_db['NormalizedName'] = food_db['FoodName'].apply(normalize_text)

# SECTION 1: Search functionality with autocomplete
with st.expander("🔎 Search", expanded=False):
    # Add a button to clear selection and search again
    if 'current_selection' not in st.session_state:
        st.session_state.current_selection = ""
    
    def clear_selection():
        st.session_state.current_selection = ""
        st.session_state.food_search = ""
    
    # Create a list of all food names for autocomplete
    food_names = food_db['FoodName'].tolist()
    
    # Initialize search_query
    search_query = ""
    
    # Get search input with autocomplete
    if st.session_state.current_selection:
        st.write(f"Currently selected: {st.session_state.current_selection}")
        if st.button("Search for a different food", key="clear_button"):
            clear_selection()
            st.rerun()
    else:
        search_query = st.selectbox(
            "Enter meal or ingredients:",
            options=[""] + food_names,
            key="food_search",
            help="Type to search or browse foods"
        )
        
        if search_query:
            st.session_state.current_selection = search_query
    
    if search_query or st.session_state.current_selection:
        # Determine which food to display
        selected_food_name = st.session_state.current_selection if st.session_state.current_selection else search_query
        
        # Find the selected food
        selected_food = food_db[food_db['FoodName'] == selected_food_name]
        
        if not selected_food.empty:
            selected_food = selected_food.iloc[0]
            
            # Display food info and add form
            st.subheader(f"Selected Food: {selected_food['FoodName']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"Nutrition per 100g:")
                st.write(f"• Calories: {selected_food['Calories']} kcal")
                st.write(f"• Protein: {selected_food['Protein']}g")
                st.write(f"• Fat: {selected_food['Fat']}g")
                st.write(f"• Carbs: {selected_food['Carbs']}g")
            
            with col2:
                weight = st.number_input("Mass (g)", min_value=1, max_value=1000, value=100, step=10, key="selected_food_weight")
                nutrition = calculate_nutrition({
                    'calories': float(selected_food['Calories']),
                    'protein': float(selected_food['Protein']),
                    'fat': float(selected_food['Fat']), 
                    'carbs': float(selected_food['Carbs'])
                }, weight)
                
                st.metric("Calories for selected amount", f"{int(nutrition['calories'])} kcal")
                
                if st.button("Add to Log", key="add_selected_food"):
                    add_food_to_log(selected_food, weight)
        else:
            st.info("No food selected. Use the search box to find and select a food.")

# SECTION 2: Display food log for selected date
with st.expander("Food Log", expanded=False):
    st.subheader(f"Food log details")
    
    if date_str in st.session_state.food_logs and st.session_state.food_logs[date_str]:
        log_entries = st.session_state.food_logs[date_str]
        
        # Display individual entries in a mobile-friendly format
        for i, entry in enumerate(log_entries):
            st.write(f"**{entry['food_name']}** ({entry['weight_g']}g)")
            st.caption(f"{entry['total_calories']} cal, {entry['total_protein']}g protein, {entry['total_fat']}g fat, {entry['total_carbs']}g carbs")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                new_weight = st.number_input(
                    "g", 
                    min_value=1, 
                    max_value=1000, 
                    value=entry['weight_g'],
                    step=10,
                    key=f"adjust_{i}"
                )
                
                if new_weight != entry['weight_g']:
                    if st.button("Update", key=f"update_{i}"):
                        # Recalculate nutrition
                        if 'calories' in entry and 'protein' in entry and 'fat' in entry and 'carbs' in entry:
                            nutrition = calculate_nutrition({
                                'calories': float(entry['calories']),
                                'protein': float(entry['protein']),
                                'fat': float(entry['fat']), 
                                'carbs': float(entry['carbs'])
                            }, new_weight)
                        else:
                            st.error("Missing nutritional information for this entry")
                            continue
                        
                        # Update entry safely
                        try:
                            log_entries[i]['weight_g'] = int(new_weight)
                            log_entries[i]['total_calories'] = int(nutrition['calories'])
                            log_entries[i]['total_protein'] = round(float(nutrition['protein']), 1)
                            log_entries[i]['total_fat'] = round(float(nutrition['fat']), 1)
                            log_entries[i]['total_carbs'] = round(float(nutrition['carbs']), 1)
                            
                            # Save logs to file
                            with open('food_logs.json', 'w') as f:
                                json.dump(st.session_state.food_logs, f)
                            
                            st.success(f"Updated {entry['food_name']} to {new_weight}g")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating entry: {e}")
            
            with col2:
                if st.button("Remove", key=f"remove_{i}"):
                    log_entries.pop(i)
                    
                    # Save logs to file
                    with open('food_logs.json', 'w') as f:
                        json.dump(st.session_state.food_logs, f)
                    
                    st.rerun()
            
            st.divider()
    else:
        st.info("No foods logged for this date. Use the search box above to add foods.")