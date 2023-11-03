import streamlit as st
import requests
import os

FASTAPI_ENDPOINT = os.getenv("FASTAPI_ENDPOINT", "http://localhost:8504")

# Dictionary of document names and their corresponding links
DOC_MAP = {
    "FOCUS Report Part IIC Instructions": "https://www.sec.gov/files/formx-17a-5_2c-instr.pdf",
    "Sec 1661": "https://www.sec.gov/files/sec1661.pdf",
    "Sec 1662": "https://www.sec.gov/files/sec1662.pdf",
    "Sec 2866": "https://www.sec.gov/files/sec2866.pdf",
    "Exam Brochure": "https://www.sec.gov/files/exam-brochure.pdf"
}

# Initialize session state variables
if 'jwt_token' not in st.session_state:
    st.session_state['jwt_token'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'selected_docs' not in st.session_state:
    st.session_state['selected_docs'] = []
if 'submit_reg_clicked' not in st.session_state:
    st.session_state['submit_reg_clicked'] = False
if 'submit_login_clicked' not in st.session_state:
    st.session_state['submit_login_clicked'] = False
if 'get_answer_clicked' not in st.session_state:
    st.session_state['get_answer_clicked'] = False
if 'selected_option' not in st.session_state:  # This line was missing
    st.session_state['selected_option'] = None

def display_initial_page():
    st.title("User Authentication")
    selected_option = st.radio("Select an option:", ["Log in", "Register a new user"])
    if selected_option == "Log in":
        st.session_state['selected_option'] = "login"
    else:
        st.session_state['selected_option'] = "register"

def jwt_auth():
    st.title("User Authentication")
    
    # Register User
    if st.button("Register a New User"):
        st.session_state['selected_option'] = "register"
    
    # Login User
    if st.button("Log in"):
        st.session_state['selected_option'] = "login"

    # Display the appropriate form based on the user's choice
    if st.session_state.get('selected_option') == "register":
        with st.form("Register Form"):
            reg_username = st.text_input("Choose a Username")
            reg_password = st.text_input("Choose a Password", type="password")
            submit_reg = st.form_submit_button("Register")
            
            if submit_reg:
                registration_data = {"username": reg_username, "password": reg_password}
                try:
                    response = requests.post(f"{FASTAPI_ENDPOINT}/register", json=registration_data)
                    if response.status_code == 200:
                        st.session_state['jwt_token'] = response.json().get('access_token')
                        st.session_state['logged_in'] = True
                        st.success("Successfully registered and logged in!")
                        # Reset the selected option to prevent form resubmission
                        st.session_state['selected_option'] = None
                    else:
                        st.error(response.json().get('detail', "Registration failed. Please try again."))
                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred while connecting to the server: {e}")

    elif st.session_state.get('selected_option') == "login":
        with st.form("Login Form"):
            login_username = st.text_input("Username")
            login_password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")

            if submit_login:
                login_data = {"username": login_username, "password": login_password}
                try:
                    response = requests.post(f"{FASTAPI_ENDPOINT}/token", data=login_data)
                    if response.status_code == 200:
                        st.session_state['jwt_token'] = response.json().get('access_token')
                        st.session_state['logged_in'] = True
                        st.success("Logged in successfully!")
                        # Reset the selected option to prevent form resubmission
                        st.session_state['selected_option'] = None
                    else:
                        st.error("Incorrect username or password. Please try again.")
                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred while connecting to the server: {e}")

    # Allow user to reset the choice and go back to the main menu
    if st.session_state.get('selected_option'):
        if st.button("Back"):
            st.session_state['selected_option'] = None



# Main page layout after authentication
def main_layout():
    st.title("Document Query Interface")

    # Create a placeholder for the warning message
    warning_placeholder = st.empty()

    # Retrieve previously selected documents from session state or use an empty list
    previously_selected_docs = st.session_state.get('selected_docs', [])

    # Document selection
    selected_docs = st.multiselect(
        "Choose Documents:",
        list(DOC_MAP.keys()),
        default=previously_selected_docs,
        key='doc_selection_key'
    )

    # Update session state with the selected docs
    st.session_state['selected_docs'] = selected_docs

    # If no document is selected, show the warning in the previously created empty slot
    if not selected_docs:
        warning_placeholder.warning("No documents selected. Please select at least one document to proceed.")
    else:
        warning_placeholder.empty()  # clear the warning message

    # Question/Answer Section
    question_input = st.text_input('Enter your question here:', key='question_input')
    
    if st.button("Get Answer"):
        with st.spinner(f'Fetching answers for selected documents...'):
            data = {
                "question": question_input,
                "context": selected_docs
            }
            headers = {"Authorization": f"Bearer {st.session_state['jwt_token']}"}
            response = requests.post(f"{FASTAPI_ENDPOINT}/get-answer/", json=data, headers=headers)
            if response.status_code == 200:
                answer_data = response.json()
                for doc_name, answer in answer_data.items():
                    st.write(f"Answer for {doc_name}: {answer}")
            else:
                st.error("Failed to fetch the answers. Please try again.")

    if st.button("Log Out"):
        st.session_state['logged_in'] = False
        st.session_state['jwt_token'] = None
        st.info("You have successfully logged out.")

# Show the JWT authentication form or the main layout based on login status
if not st.session_state['logged_in']:
    jwt_auth()
else:
    main_layout()