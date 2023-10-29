import streamlit as st
import requests

# Dictionary of document names and their corresponding links
DOC_MAP = {
    "FOCUS Report Part IIC Instructions": "https://www.sec.gov/files/formx-17a-5_2c-instr.pdf",
    "Sec 1661": "https://www.sec.gov/files/sec1661.pdf",
    "Sec 1662": "https://www.sec.gov/files/sec1662.pdf",
    "Sec 2866": "https://www.sec.gov/files/sec2866.pdf",
    "Exam Brochure": "https://www.sec.gov/files/exam-brochure.pdf"
}

# Initial session state setup
if 'user_mode' not in st.session_state:
    st.session_state.user_mode = 'login'
if 'selected_doc_name' not in st.session_state:
    st.session_state.selected_doc_name = list(DOC_MAP.keys())[0]
if 'document_data' not in st.session_state:
    st.session_state.document_data = None
if 'question' not in st.session_state:
    st.session_state.question = ""
if 'answer' not in st.session_state:
    st.session_state.answer = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Document Data"
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
# if 'jwt_token' not in st.session_state:
#     st.session_state.jwt_token = None
# if 'logged_in' not in st.session_state:
#     st.session_state.logged_in = False

st.title("Document Query Interface")

# Optional: Add your logo or branding image
# st.sidebar.image("your_logo_path_here.png", width=200)

st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a Page:", ["Document Data", "Question & Answer"], index=0 if st.session_state.current_page == "Document Data" else 1)
st.session_state.current_page = page

# def registration_section():
#     st.header("User Registration")
#     username = st.text_input("Choose a Username")
#     password = st.text_input("Choose a Password", type="password")

#     if st.button("Register"):
#         FASTAPI_ENDPOINT = "http://127.0.0.1:8504"
#         registration_data = {"username": username, "password": password}
#         response = requests.post(f"{FASTAPI_ENDPOINT}/register", registration_data)
        
#         # Handle API responses
#         if response.status_code == 200:
#             st.session_state.jwt_token = response.json().get('token')
#             st.session_state.logged_in = True
#             st.success("Successfully registered and logged in!")
#             st.session_state.user_mode = 'login'
#         elif response.status_code == 400:
#             st.warning(response.json().get('detail', "Registration failed. Please choose another username."))
#         else:
#             st.error("An error occurred during registration. Please try again.")

#     if st.button("Switch to Login"):
#         st.session_state.user_mode = 'login'


# def login_section():
#     st.header("User Login")

#     username = st.text_input("Username")
#     password = st.text_input("Password", type="password")

#     if st.button("Login"):
#         FASTAPI_ENDPOINT = "http://127.0.0.1:8504"
#         login_data = {
#             "username": username,
#             "password": password
#         }
#         response = requests.post(f"{FASTAPI_ENDPOINT}/login", login_data)

#         if response.status_code == 200:
#             st.session_state.jwt_token = response.json().get('token')
#             st.session_state.logged_in = True
#             st.success("Logged in successfully!")
#         else:
#             st.warning("Incorrect username or password. Please try again.")

#     if st.button("Switch to Register"):
#         st.session_state.user_mode = 'register'

def qa_section():
    st.header("Question/Answer System")

    if not st.session_state.get('document_data'):
        st.write("Please fetch a document data first to ask questions.")
        return

    for item in st.session_state.get('conversation', []):
        if item["role"] == "user":
            st.markdown(f"<span style='color: red'>Question:</span> {item['content']}", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color: green'>Answer:</span> {item['content']}", unsafe_allow_html=True)

    FASTAPI_ENDPOINT = "http://127.0.0.1:8504"

    with st.form(key='qa_form', clear_on_submit=True):
        question_input = st.text_input('Enter your question:', value=st.session_state.get('question', ""))

        if st.form_submit_button("Get Answer"):
            st.session_state.conversation.append({"role": "user", "content": question_input})

            with st.spinner('Finding answer...'):
                data = {
                    "question": question_input,
                    "context": st.session_state.document_data['text']
                }
                response = requests.post(f"{FASTAPI_ENDPOINT}/get-answer/", data=data)
                answer_data = response.json()

                if "answer" in answer_data:
                    answer = answer_data['answer']
                    st.session_state.conversation.append({"role": "ai", "content": answer})

            st.session_state.question = question_input
            st.session_state.question = ""

# if not st.session_state.logged_in:
#     if st.session_state.user_mode == 'register':
#         registration_section()
#     else:
#         login_section()
# else:
    # sidebar_column, main_content = st.columns([1, 4])

    # sidebar_column.title("Navigation")
    # page = sidebar_column.selectbox("Choose a Page:", ["Document Data", "Question & Answer"], index=0 if st.session_state.current_page == "Document Data" else 1)
    # st.session_state.current_page = page

if page == "Document Data":
    st.session_state.selected_doc_name = st.selectbox("Choose a Document:", list(DOC_MAP.keys()), index=list(DOC_MAP.keys()).index(st.session_state.selected_doc_name))
    FASTAPI_ENDPOINT = "http://127.0.0.1:8504"

    if st.button("Fetch Document Data"):
        selected_link = DOC_MAP[st.session_state.selected_doc_name]
        response = requests.get(f"{FASTAPI_ENDPOINT}/get_document_data?doc_name={selected_link}")
        if response.status_code == 200:
            st.session_state.document_data = response.json()
        else:
            st.warning("Failed to fetch document data. Please try again.")

    if st.session_state.document_data:
        st.subheader("Extracted Text:")
        st.write(st.session_state.document_data['text'])

        st.subheader("Metadata:")
        st.write("Name of the form/file:", st.session_state.document_data['metadata']['form_name'])
        st.write("Number of pages:", st.session_state.document_data['metadata']['page_count'])
        st.write("Number of characters:", st.session_state.document_data['metadata']['char_count'])
        st.write("Time taken to extract:", st.session_state.document_data['metadata']['extraction_time'])

elif page == "Question & Answer":
    qa_section()

# Note: The FastAPI backend endpoints `/get_document_data` and `/get-answer/` are placeholders and 
# should be replaced with the actual endpoints and their expected request format.
