import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import numpy as np
import joblib
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
import hashlib

ps = PorterStemmer()

# Load ML model and columns
model = joblib.load('C:\\streamlit_project\\finalized_model.pkl')
columns = joblib.load('C:\\streamlit_project\\model_columns.pkl')

# Hashing function for passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize connection to the database
def init_db(host_name, user_name, user_password, db_name):
    try:
        connection = mysql.connector.connect(host=host_name, user=user_name, passwd=user_password, database=db_name)
        st.success("MySQL Database connection successful")
    except Error as err:
        st.error(f"Error: '{err}'")
        return None
    return connection

# Execute SQL queries
def execute_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        connection.commit()
        st.success("Query successful")
    except Error as err:
        st.error(f"Error: '{err}'")
    finally:
        cursor.close()

# Fetch data and return as DataFrame
def read_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        result = cursor.fetchall()
        return pd.DataFrame(result, columns=[i[0] for i in cursor.description])
    except Error as err:
        st.error(f"Error: '{err}'")
    finally:
        cursor.close()

# Fetch a single value (like a count) with improved error handling
def read_single_value_query(connection, query, params=None):
    cursor = connection.cursor()
    try:
        cursor.execute(query, params or ())
        result = cursor.fetchone()
        if result and result[0] is not None:
            return result[0]
        else:
            st.warning("Query returned no results.")
            return 0
    except Error as err:
        st.error(f"Database query error: '{err}'")
        return 0
    finally:
        cursor.close()

# Prediction function
def predict_price(location, sqft, bath, bhk):
    x = np.zeros(len(columns))
    x[0] = sqft
    x[1] = bath
    x[2] = bhk
    if location in columns[3:]:  # Adjust the index according to your columns order
        loc_index = np.where(columns == location)[0][0]
        x[loc_index] = 1
    prediction = model.predict([x])[0]
    return prediction

# User Authentication functions
def login(connection, username, password):
    hashed_password = hash_password(password)
    query = "SELECT * FROM users WHERE username = %s AND password = %s;"
    cursor = connection.cursor()
    cursor.execute(query, (username, hashed_password))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

def signup(connection, username, password):
    hashed_password = hash_password(password)
    try:
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (username, hashed_password))
        connection.commit()
        cursor.close()
        return True
    except Error as err:
        st.error(f"Error: '{err}'")
        return False

# UI Enhancements using CSS
# Enhanced CSS with background image and additional styling


# CSS to set a full-page background image
st.markdown(
    """
    <style>
        /* Background image for the entire app */
        .stApp {
            background: linear-gradient(rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.5)), 
                        url("https://images.unsplash.com/photo-1598346762296-f4a72d7a7ef7");
            background-size: cover;
            background-attachment: fixed;
            background-repeat: no-repeat;
            background-position: center;
        }

        /* Centered overlay box for content */
        .overlay {
            background-color: rgba(255, 255, 255, 0.85); /* White overlay with slight opacity */
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
            margin: 0 auto;
            max-width: 800px;
        }

        /* Title styling */
        .title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #4e73df;
            text-align: center;
            padding-bottom: 10px;
        }

        /* Button styling */
        .button {
            background-color: #4e73df;
            color: #ffffff;
            border: none;
            padding: 10px;
            font-size: 1rem;
            border-radius: 5px;
            margin-top: 10px;
            transition: background-color 0.3s ease;
        }

        .button:hover {
            background-color: #3b5db1;
            cursor: pointer;
        }
    </style>
    """,
    unsafe_allow_html=True
)



# Main content wrapper with overlay for readability
st.markdown("<div class='overlay'><h2 class='title'>Apartment Management System</h2></div>", unsafe_allow_html=True)

# Main app function with session state for login persistence
def main():
    # Initialize session state for login if it doesn't exist
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    
    db = init_db("localhost", "root", "root", "apartment_management")

    # Display the login/signup options if not logged in
    if not st.session_state.logged_in:
        auth_choice = st.sidebar.radio("Login/Sign up", ["Login", "Sign up"], key="auth_choice")
        if auth_choice == "Login":
            username = st.sidebar.text_input("Username")
            password = st.sidebar.text_input("Password", type="password")
            if st.sidebar.button("Login"):
                if login(db, username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.sidebar.success("Logged in successfully")
                else:
                    st.sidebar.error("Invalid credentials")
        elif auth_choice == "Sign up":
            username = st.sidebar.text_input("New Username")
            password = st.sidebar.text_input("New Password", type="password")
            if st.sidebar.button("Sign up"):
                if signup(db, username, password):
                    st.sidebar.success("Account created successfully")
                else:
                    st.sidebar.error("Sign up failed")

    # Show the main application interface if logged in
    if st.session_state.logged_in:
        st.sidebar.write(f"Welcome, {st.session_state.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.sidebar.success("Logged out successfully")

        menu = ["Home", "Predict Price", "Manage Tenants", "Manage Apartments", "Manage Maintenance", "About"]
        choice = st.sidebar.selectbox("Menu", menu)

        # Show different pages based on the selected menu option
        if choice == "Home":
            display_dashboard(db)
        elif choice == "Predict Price":
            predict_price_section()
        elif choice == "Manage Tenants":
            manage_tenants(db)
        elif choice == "Manage Apartments":
            manage_apartments(db)
        elif choice == "Manage Maintenance":
            manage_maintenance(db)
        elif choice == "About":
            st.subheader("About This App")
            st.write("This application is designed to manage apartments efficiently using a MySQL database backend.")

# Display Dashboard function with improved error handling
def display_dashboard(db):
    st.subheader("Dashboard")
    st.write("Welcome to the Apartment Management System Dashboard. Manage all your apartment needs in one place.")

    try:
        occupied_apartments_count = read_single_value_query(db, "SELECT COUNT(*) FROM apartments WHERE status = 'Occupied';")
        total_tenants_count = read_single_value_query(db, "SELECT COUNT(*) FROM tenants;")
        maintenance_due_count = read_single_value_query(db, "SELECT COUNT(*) FROM maintenance WHERE status = 'Due';")
        high_priority_maintenance_count = read_single_value_query(db, "SELECT COUNT(*) FROM maintenance WHERE priority = 'High Priority' AND status = 'Due';")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Occupied Apartments", value=occupied_apartments_count)
        with col2:
            st.metric(label="Total Tenants", value=total_tenants_count)
        with col3:
            st.metric(label="Maintenance Due", value=maintenance_due_count)
        with col4:
            st.metric(label="High Priority Maintenance", value=high_priority_maintenance_count)
    except Exception as e:
        st.error(f"An error occurred: {e}")

def predict_price_section():
    st.subheader("Apartment Price Prediction")
    location = st.text_input("Location")
    sqft = st.number_input("Square Feet", min_value=300, value=500)
    bath = st.slider("Bathrooms", 1, 5, 1)
    bhk = st.slider("Bedrooms", 1, 5, 1)
    if st.button("Predict Price"):
        prediction = predict_price(location, sqft, bath, bhk)
        st.success(f"Estimated Apartment Price: {prediction:,.2f} lakhs")

def manage_tenants(db):
    st.subheader("Tenants")
    tenant_action = st.radio("Action", ["View Tenants", "Add Tenant", "Update Tenant", "Delete Tenant"])
    if tenant_action == "View Tenants":
        result = read_query(db, "SELECT * FROM tenants;")
        if not result.empty:
            st.dataframe(result)
        else:
            st.info("No tenants found")
    elif tenant_action == "Add Tenant":
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        phone_number = st.text_input("Phone Number")
        email = st.text_input("Email")
        if st.button("Add Tenant"):
            execute_query(db, "INSERT INTO tenants (first_name, last_name, phone_number, email) VALUES (%s, %s, %s, %s);", (first_name, last_name, phone_number, email))
    elif tenant_action == "Update Tenant":
        tenant_id = st.number_input("Tenant ID", format="%d")
        new_email = st.text_input("New Email")
        if st.button("Update Email"):
            execute_query(db, "UPDATE tenants SET email = %s WHERE id = %s;", (new_email, tenant_id))
    elif tenant_action == "Delete Tenant":
        tenant_id = st.number_input("Tenant ID to delete", format="%d")
        if st.button("Delete Tenant"):
            execute_query(db, "DELETE FROM tenants WHERE id = %s;", (tenant_id,))

def manage_apartments(db):
    st.subheader("Apartments")
    apartment_action = st.radio("Action", ["View Apartments", "Add Apartment", "Update Apartment Status", "Delete Apartment"])
    if apartment_action == "View Apartments":
        result = read_query(db, "SELECT * FROM apartments;")
        if not result.empty:
            st.dataframe(result)
        else:
            st.info("No apartments found")
    elif apartment_action == "Add Apartment":
        number = st.text_input("Apartment Number")
        building = st.text_input("Building")
        floor = st.number_input("Floor", format="%d")
        room_count = st.number_input("Room Count", format="%d")
        status = st.selectbox("Status", ["Available", "Occupied", "Maintenance"])
        if st.button("Add Apartment"):
            execute_query(db, "INSERT INTO apartments (apartment_number, building, floor, room_count, status) VALUES (%s, %s, %s, %s, %s);", (number, building, floor, room_count, status))
    elif apartment_action == "Update Apartment Status":
        apartment_id = st.number_input("Apartment ID", format="%d")
        new_status = st.selectbox("New Status", ["Available", "Occupied", "Maintenance"])
        if st.button("Update Status"):
            execute_query(db, "UPDATE apartments SET status = %s WHERE id = %s;", (new_status, apartment_id))
    elif apartment_action == "Delete Apartment":
        apartment_id = st.number_input("Apartment ID to delete", format="%d")
        if st.button("Delete Apartment"):
            execute_query(db, "DELETE FROM apartments WHERE id = %s;", (apartment_id,))

def manage_maintenance(db):
    st.subheader("Maintenance Management")
    maintenance_action = st.radio("Action", ["View Maintenance Records", "Add Maintenance Record", "Update Maintenance Record", "Delete Maintenance Record"])

    if maintenance_action == "View Maintenance Records":
        result = read_query(db, "SELECT * FROM maintenance;")
        if not result.empty:
            result['priority_color'] = result['priority'].apply(lambda x: '🔴 High' if x == 'High Priority' else '🟢 Normal')  # Add color indicator
            result_display = result[['id', 'apartment_id', 'description', 'status', 'priority', 'priority_color']]
            result_display = result_display.rename(columns={"priority_color": ""})  # Display color indicator without header
            st.dataframe(result_display)
        else:
            st.info("No maintenance records found")

    elif maintenance_action == "Add Maintenance Record":
        apartment_id = st.number_input("Apartment ID", format="%d")
        description = st.text_area("Maintenance Description")
        status = st.selectbox("Status", ["Due", "Completed"])

        # Function to analyze priority based on text content
        def analyze_request_priority(request_text):
            urgent_keywords = [ "urgent", "leak", "broken", "flood", "power outage", "emergency", "fire", "gas leak",
                               "no water", "no electricity","electrcity", "burst pipe", "damaged", "crack", "repair needed", 
                               "water damage", "lockout", "blocked drain", "mold", "heating issue", "air conditioning",
                               "roof damage", "pest", "infestation", "malfunction", "hazard", "security", "alarm", 
                               "structural damage", "water heater", "smoke", "odor", "sewage", "toilet issue", 
                               "electrical fault", "sparking", "foul smell", "noise complaint", "temperature control"
                               ]

            tokenized_text = word_tokenize(request_text.lower())
            stemmed_text = [ps.stem(word) for word in tokenized_text]
            if any(ps.stem(keyword) in stemmed_text for keyword in urgent_keywords):
                return "High Priority"
            return "Normal Priority"

        # Determine priority based on analysis
        priority = analyze_request_priority(description)
        st.write(f"Assigned Priority: {priority}")

        # Insert maintenance record
        if st.button("Add Record"):
            execute_query(db, "INSERT INTO maintenance (apartment_id, description, status, priority) VALUES (%s, %s, %s, %s);", 
                          (apartment_id, description, status, priority))

    elif maintenance_action == "Update Maintenance Record":
        record_id = st.number_input("Record ID", format="%d")
        new_status = st.selectbox("New Status", ["Due", "Completed"])
        if st.button("Update Record"):
            execute_query(db, "UPDATE maintenance SET status = %s WHERE id = %s;", (new_status, record_id))

    elif maintenance_action == "Delete Maintenance Record":
        record_id = st.number_input("Record ID to delete", format="%d")
        if st.button("Delete Record"):
            execute_query(db, "DELETE FROM maintenance WHERE id = %s;", (record_id,))


if __name__ == "__main__":
    main()
