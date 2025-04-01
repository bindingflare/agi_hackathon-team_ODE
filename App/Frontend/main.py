import streamlit as st
from langchain_upstage import ChatUpstage
from langchain.schema import HumanMessage
import PyPDF2
import os

# Use secret if available
upstage_api_key = st.secrets.get("UPSTAGE_API_KEY") or os.getenv("UPSTAGE_API_KEY")

st.title("Basic Chatbot (v1.0) using LangChain & Solar by Upstage")

# Input fields: text input and optional PDF upload
user_input = st.text_input("Enter your message:")
pdf_file = st.file_uploader("Or upload a PDF file (optional)", type=["pdf"])

if st.button("Send"):
    # If a PDF file is uploaded, extract its text
    if pdf_file is not None:
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pdf_text += page_text + "\n"
            prompt = f"{user_input}\n\nAdditional context from PDF:\n{pdf_text}"
        except Exception as e:
            st.error(f"Error processing PDF: {e}")
            prompt = user_input
    else:
        prompt = user_input

    # Initialize Solar (Upstage) chat model
    chat = ChatUpstage(upstage_api_key=upstage_api_key, model_name="solar-1-mini-chat", temperature=0.7)
    
    # Get the response
    response = chat([HumanMessage(content=prompt)])
    
    # Display the response
    st.write("**Solar (Upstage) Response:**")
    st.write(response.content)
