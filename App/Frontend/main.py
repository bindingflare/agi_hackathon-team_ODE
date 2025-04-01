import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
import PyPDF2

# Set up your OpenAI API key (alternatively, set this in your environment)
# st.secrets["OPENAI_API_KEY"] = "your-openai-api-key"  # Optionally use Streamlit secrets

st.title("Basic Chatbot (v1.0) using LangChain & OpenAI")

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
            # Append PDF content to the user's prompt
            prompt = f"{user_input}\n\nAdditional context from PDF:\n{pdf_text}"
        except Exception as e:
            st.error(f"Error processing PDF: {e}")
            prompt = user_input
    else:
        prompt = user_input

    # Initialize the ChatOpenAI model from LangChain
    chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
    
    # Send the prompt to ChatGPT and get the response
    response = chat([HumanMessage(content=prompt)])
    
    # Display the response
    st.write("**ChatGPT Response:**")
    st.write(response.content)
