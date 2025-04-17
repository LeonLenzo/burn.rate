import streamlit as st
import pandas as pd
from datetime import date
import json

from modules.data_handler import save_food_logs, search_foods
from modules.utils import NutritionCalculator, calculate_daily_totals, format_date, export_logs_as_download_link, import_logs_from_uploaded_file

def render_overview_section(food_db):
    """Render the overview section with daily summary and goal tracking"""
    # Date selection with better formatting
    selected_date = st.date_input(
        "Date", 
        date.today(), 
        key="date_selector", 
        help="Select date to view or add food entries"
    )
    date_str = format_date(selected_date)
    
    # Initialize food log for selected date if it doesn't exist
    if date_str not in st.session_state.food_logs:
        st.session_state.food_logs[date_str] = []

    # Set default calorie goal if not set
    if 'daily_goal' not in st.session_state:
        st.session_state.daily_goal = 2000

    # Get the log entries for the selected date
    log_entries = st.session_state.food_logs.get(date_str, [])

    # Calculate daily nutrition totals
    daily_totals = calculate_daily_totals(log_entries)
    
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
                background-color: #0E1117;
                border-radius: 5px;
                padding: 10px;
                text-align: center;
            }
            .metric-label {
                font-size: 1rem;
                color: #FFFFFF;
                margin-bottom: 5px;
            }
            .metric-value {
                font-size: 1.5rem;
                font-weight: bold;
                color: #FFFFFF;
            }
        </style>
        """, unsafe_allow_html=True)

        # Then replace your metrics section with:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-box">
                <div class="metric-label">Calories</div>
                <div class="metric-value">{int(daily_totals["calories"])}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Protein</div>
                <div class="metric-value">{daily_totals["protein"]:.1f}g</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Fat</div>
                <div class="metric-value">{daily_totals["fat"]:.1f}g</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">Carbs</div>
                <div class="metric-value">{daily_totals["carbs"]:.1f}g</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Daily calorie target progress
    daily_goal = st.session_state.daily_goal
    st.progress(min(daily_totals["calories"] / daily_goal, 1.0))
    st.divider()

def render_search_section(food_db):
    """Render the search section with food search and selection"""
    # Track that this expander has been opened
    if not st.session_state.get("search_expanded", False):
        st.session_state.search_expanded = True

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
        st.write(f"{st.session_state.current_selection}")
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
            # Immediately update selection and rerun to show the different food button
            st.session_state.current_selection = search_query
            st.rerun()
    
    if search_query or st.session_state.current_selection:
        # Determine which food to display
        selected_food_name = st.session_state.current_selection if st.session_state.current_selection else search_query
        
        # Find the selected food
        selected_food = food_db[food_db['FoodName'] == selected_food_name]
        
        if not selected_food.empty:
            selected_food = selected_food.iloc[0]
            
            # Display food info and add form
            st.subheader(f"{selected_food['FoodName']}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"Nutrition per 100g:")
                st.write(f"• Calories: {selected_food['Calories']} kcal")
                st.write(f"• Protein: {selected_food['Protein']}g")
                st.write(f"• Fat: {selected_food['Fat']}g")
                st.write(f"• Carbs: {selected_food['Carbs']}g")
            
            with col2:
                weight = st.number_input("Mass (g)", min_value=1, max_value=1000, value=100, step=10, key="selected_food_weight")
                
                calculator = NutritionCalculator()
                nutrition = calculator.calculate_nutrition({
                    'calories': float(selected_food['Calories']),
                    'protein': float(selected_food['Protein']),
                    'fat': float(selected_food['Fat']), 
                    'carbs': float(selected_food['Carbs'])
                }, weight)
                
                st.metric("Total:", f"{int(nutrition['calories'])} kcal")
                
                if st.button("Add to Log", key="add_selected_food"):
                    add_food_to_log(selected_food, weight)
        else:
            st.info("No food selected. Use the search box to find and select a food.")

def render_food_log_section(food_db):
    """Render the food log section with entries for the selected date"""
    st.markdown(f"---")
    
    # Get the selected date
    selected_date = st.session_state.get("date_selector", date.today())
    date_str = format_date(selected_date)
    
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
                        update_food_entry(date_str, i, new_weight)
            
            with col2:
                if st.button("Remove", key=f"remove_{i}"):
                    remove_food_entry(date_str, i)
            
            st.divider()
    else:
        st.info("No foods logged for this date. Use the search box above to add foods.")

def render_settings_section():
    """Render the settings section with import/export functionality"""
    st.subheader("Export/Import Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Food Logs"):
            href = export_logs_as_download_link(st.session_state.food_logs)
            st.markdown(href, unsafe_allow_html=True)
    
    with col2:
        uploaded_file = st.file_uploader("Import Food Logs", type="json")
        if uploaded_file is not None:
            success, message, merged_logs = import_logs_from_uploaded_file(
                uploaded_file, 
                st.session_state.food_logs
            )
            
            if success:
                st.session_state.food_logs = merged_logs
                save_food_logs(st.session_state.food_logs)
                st.success(message)
                st.rerun()
            else:
                st.error(message)

# Helper functions for UI components

def add_food_to_log(food, weight):
    """Add a food item to the log for the selected date"""
    # Get the selected date
    selected_date = st.session_state.get("date_selector", date.today())
    date_str = format_date(selected_date)
    
    # Calculate nutrition based on weight
    calculator = NutritionCalculator()
    nutrition = calculator.calculate_nutrition({
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
    if save_food_logs(st.session_state.food_logs):
        st.success(f"Added {food['FoodName']} ({weight}g) to your log")
        st.rerun()
    else:
        st.error("Failed to save food log")

def update_food_entry(date_str, index, new_weight):
    """Update a food entry with a new weight"""
    try:
        # Get the entry
        entry = st.session_state.food_logs[date_str][index]
        
        # Recalculate nutrition
        calculator = NutritionCalculator()
        nutrition = calculator.calculate_nutrition({
            'calories': float(entry['calories']),
            'protein': float(entry['protein']),
            'fat': float(entry['fat']), 
            'carbs': float(entry['carbs'])
        }, new_weight)
        
        # Update entry
        entry['weight_g'] = int(new_weight)
        entry['total_calories'] = int(nutrition['calories'])
        entry['total_protein'] = round(float(nutrition['protein']), 1)
        entry['total_fat'] = round(float(nutrition['fat']), 1)
        entry['total_carbs'] = round(float(nutrition['carbs']), 1)
        
        # Save logs to file
        if save_food_logs(st.session_state.food_logs):
            st.success(f"Updated {entry['food_name']} to {new_weight}g")
            st.rerun()
        else:
            st.error("Failed to save food log")
    except Exception as e:
        st.error(f"Error updating entry: {e}")

def remove_food_entry(date_str, index):
    """Remove a food entry from the log"""
    try:
        # Get the entry name for the success message
        entry_name = st.session_state.food_logs[date_str][index]['food_name']
        
        # Remove the entry
        st.session_state.food_logs[date_str].pop(index)
        
        # Save logs to file
        if save_food_logs(st.session_state.food_logs):
            st.success(f"Removed {entry_name} from your log")
            st.rerun()
        else:
            st.error("Failed to save food log")
    except Exception as e:
        st.error(f"Error removing entry: {e}")