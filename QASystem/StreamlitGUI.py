import streamlit as st
import requests
import pandas as pd

# Initialize session state variables if they don't exist
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""

if 'conversation' not in st.session_state:
    st.session_state.conversation = []

st.title("PDF Analyzer: OCR and Q/A System")

# Sidebar
st.sidebar.title("Navigation")
menu = ["Home", "Perform OCR", "Q/A System", "Document Summary", "About"]
choice = st.sidebar.selectbox("Choose a section", menu)

if st.sidebar.button("Reset Session"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()

def home_section():
    st.header("Welcome to the PDF Analyzer App 📄🔍")
    st.write("This application allows you to harness the power of OCR (Optical Character Recognition) and an AI-powered Q/A system.")

    # Using markdown for fancy formatting
    st.markdown("""
    #### How to Navigate:
    1. **Perform OCR**:
        - Provide a PDF via URL or direct upload.
        - Choose an OCR method.
        - See the extracted text and use it for subsequent operations.
    2. **Q/A System**:
        - After extracting text, ask any question regarding the content.
        - See the AI's response in real-time.
        - View your past questions and their answers.
    3. **Document Summary**:
        - Check out metrics related to your last OCR operation.
    4. **About**:
        - Learn more about the functionality and purpose of this app.
    
    Use the **sidebar** on the left to navigate between these sections. If you need to start over, simply hit the **Reset Session** button in the sidebar.
    """, unsafe_allow_html=True)

    st.write("🚀 Dive in and explore!")


def perform_ocr_section():
    st.header("Perform OCR")

    FASTAPI_ENDPOINT = "https://fastapi-assignment2-4fb0a78ad873.herokuapp.com"

    input_methods = ["Provide a PDF URL Link", "Upload a PDF file"]
    input_option = st.selectbox("Select input method", input_methods)

    ocr_methods = ["PyPDF", "Nougat"]
    option = st.selectbox("Select OCR method", ocr_methods)

    uploaded_file = None
    url = None
    ngrok = None  # Initialized here

    # To display instructions and take the auth_token from the user if Nougat is chosen
    if option == "Nougat":
        st.write("Please visit the following Google Colab Notebook and follow the instructions to generate the NGrok Link:")
        st.write("[Google Colab Notebook](https://colab.research.google.com/drive/1nIeJH-1fu20UUVXD_YvcyQG30NQ98u-b#scrollTo=iBWwqRnEbpUE)")  # Provide your Google Colab link here
        ngrok = st.text_input("Enter the generated NGrok Link here:")
    
    if input_option == "Upload a PDF file":
        uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    else:
        url = st.text_input('Provide the PDF URL Link')

    if st.button("Perform OCR"):
        with st.spinner('Performing OCR...'):
            data = {
                "ocr_method": option,
                "ngrok": ngrok  # Include the link in the request data
            }
            if uploaded_file:
                files = {"file": uploaded_file.getvalue()}
                response = requests.post(f"{FASTAPI_ENDPOINT}/perform-ocr/", files=files, data=data)
            else:
                data["url"] = url
                response = requests.post(f"{FASTAPI_ENDPOINT}/perform-ocr/", data=data)

            result = response.json()

            if "status" in result and result["status"] == "success":
                st.session_state.pdf_text = result["ocr_output"]
                st.write("OCR Output:")
                st.write(st.session_state.pdf_text)

                # Storing the summary data in st.session_state
                st.session_state.time_taken = result["summary"]["time_taken_s"]
                st.session_state.characters_sent = result["summary"]["input_length"]
                st.session_state.characters_received = result["summary"]["output_length"]
                # NOTE: Your backend doesn't seem to be returning a 'number_of_pages' key
                #st.session_state.number_of_pages = result["summary"]["number_of_pages"]  # Assuming you'll add this in the backend

def qa_section():
    st.header("Question/Answer System")

    # If no text has been extracted, inform the user
    if not st.session_state.get('pdf_text'):
        st.write("Please perform OCR on a PDF first to extract text.")
        return

    # Display previous conversation
    for item in st.session_state.get('conversation', []):
        if item["role"] == "user":
            st.markdown(f"<span style='color: red'>Question:</span> {item['content']}", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color: green'>Answer:</span> {item['content']}", unsafe_allow_html=True)


    FASTAPI_ENDPOINT = "https://fastapi-assignment2-4fb0a78ad873.herokuapp.com"
            
    # Start the form
    with st.form(key='qa_form', clear_on_submit=True):

        # Use st.session_state.question for the text_input
        question_input = st.text_input('Enter your question:', value=st.session_state.get('question', ""))

        # Submit button for the form
        if st.form_submit_button("Get Answer"):

            st.session_state.conversation.append({"role": "user", "content": question_input})

            with st.spinner('Finding answer...'):
                data = {
                    "question": question_input,
                    "context": st.session_state.pdf_text
                }
                response = requests.post(f"{FASTAPI_ENDPOINT}/get-answer/", data=data)
                answer_data = response.json()

                if "answer" in answer_data:
                    answer = answer_data['answer']
                    st.session_state.conversation.append({"role": "ai", "content": answer})

            # Update st.session_state.question AFTER processing the current question
            st.session_state.question = question_input

            # Clear the question to reset the text box
            st.session_state.question = ""

            # Refresh the page to reflect the changes
            st.experimental_rerun()

def document_summary_section():
    st.header("Document Summary")

    if 'time_taken' in st.session_state:
        summary_data = {
            "Metrics": [
                "Time taken for OCR (sec.)",
                "Characters sent for OCR",
                "Characters received after OCR",
                #"Number of pages obtained"  # Uncomment if you add this in the backend
            ],
            "Values": [
                st.session_state.time_taken,
                st.session_state.characters_sent,
                st.session_state.characters_received,
                #st.session_state.number_of_pages  # Uncomment if you add this in the backend
            ]
        }

        summary_df = pd.DataFrame(summary_data)

        # Use st.table() for better table formatting
        st.table(summary_df.set_index('Metrics'))

        # Optionally, add some additional descriptive text if necessary
        st.write("Note: Metrics and values are based on the most recent OCR operation.")

    else:
        st.write("Summary of the last document processed will appear here.")

def about_section():
    st.header("📘 About PDF Analyzer and Its Components 📘")

    # Divider
    st.markdown("---")

    # PDF Analyzer
    st.markdown("### 📄 **PDF Analyzer**", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #f0f0f0; padding: 10px 15px; border-radius: 5px;">
    PDF Analyzer is a comprehensive tool that integrates state-of-the-art OCR (Optical Character Recognition) with an AI-driven Q/A system. It enables users to extract text from PDFs and then ask specific questions related to the extracted content, providing an interactive way to engage with document contents.
    </div>
    """, unsafe_allow_html=True)

    st.write("")  # Spacer

    # Nougat
    st.markdown("### 🍫 **Nougat**", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #e8e8e8; padding: 10px 15px; border-radius: 5px;">
    Nougat is an advanced OCR system tailored for extracting text from various document formats with high accuracy. It is designed to handle complex document layouts, multiple languages, and can distinguish between various text styles and structures. By leveraging machine learning and computer vision techniques, Nougat ensures precise text extraction even from intricate documents. <br><br>
    <a href="https://github.com/facebookresearch/nougat" target="_blank">Learn more about Nougat on GitHub</a>.
    </div>
    """, unsafe_allow_html=True)

    st.write("")  # Spacer

    # PyPDF
    st.markdown("### 📖 **PyPDF**", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #f0f0f0; padding: 10px 15px; border-radius: 5px;">
    PyPDF is a widely-used library in the Python ecosystem for handling PDF files. It allows for tasks such as extracting text, splitting and merging PDFs, and managing metadata. While its text extraction capabilities are solid for basic PDFs, it may not handle complex layouts or images as efficiently as specialized OCR systems like Nougat.
    </div>
    """, unsafe_allow_html=True)

    st.write("")  # Spacer

    # OpenAI
    st.markdown("### 🧠 **OpenAI**", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #e8e8e8; padding: 10px 15px; border-radius: 5px;">
    OpenAI is a leading organization in the realm of artificial intelligence research and its application. Known for its cutting-edge models and platforms, OpenAI aims to ensure that artificial general intelligence (AGI) benefits all of humanity. The Q/A system incorporated in the PDF Analyzer leverages OpenAI's language models to provide accurate and contextually relevant answers based on the extracted text from PDFs.
    </div>
    """, unsafe_allow_html=True)

    # Divider
    st.markdown("---")

    st.markdown("Together, these components make the **PDF Analyzer** a powerful tool for extracting and understanding the content within PDFs.", unsafe_allow_html=True)

# Mapping sections to functions
sections = {
    "Home": home_section,
    "Perform OCR": perform_ocr_section,
    "Q/A System": qa_section,
    "Document Summary": document_summary_section,
    "About": about_section
}

# Running the appropriate section
sections[choice]()
