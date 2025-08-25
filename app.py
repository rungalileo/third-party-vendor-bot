"""
Streamlit app for Third-Party Vendor Bot with Galileo integration
"""
import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv
from galileo import galileo_context
from galileo.handlers.langchain import GalileoCallback
from agent import VendorAgentRunner
from langchain_core.messages import AIMessage, HumanMessage


# Load environment variables
# For local development, use .env file
# For Streamlit Cloud deployment, use secrets.toml
load_dotenv()

# Set environment variables from Streamlit secrets if running on Streamlit Cloud
if hasattr(st, 'secrets'):
    try:
        for key, value in st.secrets["secrets"].items():
            os.environ[key] = str(value)
    except KeyError:
        # No secrets section found, continue with .env file
        pass


def display_chat_history():
    """Display all messages in the chat history with agent attribution."""
    if not st.session_state.messages:
        return

    for message_data in st.session_state.messages:
        if isinstance(message_data, dict):
            message = message_data.get("message")

            if isinstance(message, HumanMessage):
                with st.chat_message("user"):
                    st.write(message.content)
            elif isinstance(message, AIMessage):
                with st.chat_message("assistant"):
                    st.write(message.content)
        else:
            # Fallback for old message format
            if isinstance(message_data, HumanMessage):
                with st.chat_message("user"):
                    st.write(message_data.content)
            elif isinstance(message_data, AIMessage):
                with st.chat_message("assistant"):
                    st.write(message_data.content)


def show_example_queries(query_1: str, query_2: str):
    """Show example queries demonstrating the vendor system"""
    st.subheader("Example queries")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(query_1, key="query_1"):
            return query_1

    with col2:
        if st.button(query_2, key="query_2"):
            return query_2
    return None


def show_onboarding_progress(session_id: str):
    """Show onboarding progress based on current session state"""
    from tools import _onboarding_sessions
    
    # Define the onboarding steps (3 main steps)
    steps = [
        {"name": "Company Info", "key": "company_lookup_complete", "icon": "🏢"},
        {"name": "Compliance", "key": "compliance_certifications", "icon": "📋"},
        {"name": "Data Access", "key": "data_access_needs", "icon": "🔐"}
    ]
    
    # Get current session data
    session_data = _onboarding_sessions.get(session_id, {})
    
    # Create a simple 3-tile layout
    for i, step in enumerate(steps):
        # Check if this step is completed
        if step["key"] == "company_lookup_complete":
            is_completed = "company_name" in session_data
        else:
            is_completed = step["key"] in session_data
        
        if is_completed:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; background-color: #d4edda; border-radius: 10px; border: 2px solid #28a745; margin-bottom: 10px;">
                <div style="font-size: 24px;">{step["icon"]}</div>
                <div style="font-size: 12px; font-weight: bold; color: #155724;">{step["name"]}</div>
                <div style="font-size: 10px; color: #155724;">✅ Complete</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 10px; border: 2px solid #dee2e6; margin-bottom: 10px;">
                <div style="font-size: 24px; opacity: 0.5;">{step["icon"]}</div>
                <div style="font-size: 12px; color: #6c757d;">{step["name"]}</div>
                <div style="font-size: 10px; color: #6c757d;">⏳ Pending</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Calculate completed steps
    completed_steps = sum(1 for step in steps if (
        step["key"] in session_data or 
        (step["key"] == "company_lookup_complete" and "company_name" in session_data)
    ))
    
    # Show overall progress bar
    progress_percentage = completed_steps / len(steps)
    st.progress(progress_percentage)
    st.caption(f"{completed_steps}/{len(steps)} steps completed ({int(progress_percentage * 100)}%)")
    
    return completed_steps, len(steps)


def orchestrate_streamlit_and_get_user_input(
    agent_title: str, example_query_1: str, example_query_2: str
):
    # App title and description
    st.title(agent_title)
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state.session_id = session_id
        try:
            galileo_context.start_session(name="Third-Party Vendor Bot", external_id=session_id)
        except Exception as e:
            st.error(f"Failed to start Galileo session: {str(e)}")
            st.stop()
        # Add welcome message with clear next steps
        welcome_message = AIMessage(content="""Welcome to the Third-Party Vendor Application Portal.

Please submit your vendor application by providing the following information:

1. **Company's legal name** and **country of incorporation** 
2. **Compliance certifications** held (e.g., SOC 2, ISO 27001, GDPR, etc.)
3. **Data access requirements** (customer data, financial systems, etc.)

Please begin by providing your company's legal name and country of incorporation. Your application will be processed immediately upon submission.""")
        st.session_state.messages.append(
            {"message": welcome_message, "agent": "system"}
        )

    # Progress tracker is now shown in sidebar
    
    # Show example queries
    example_query = show_example_queries(example_query_1, example_query_2)

    # Display chat history
    display_chat_history()

    # Get user input
    user_input = st.chat_input("How can I help you?...")
    # Use example query if button was clicked
    if example_query:
        user_input = example_query
    return user_input


def process_input_for_simple_app(user_input: str | None):
    if user_input:
        # Add user message to chat history
        user_message = HumanMessage(content=user_input)
        st.session_state.messages.append({"message": user_message, "agent": "user"})

        # Display the user message immediately
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                # Convert session state messages to LangChain message format
                conversation_messages = []
                for msg_data in st.session_state.messages:
                    if isinstance(msg_data, dict) and "message" in msg_data:
                        conversation_messages.append(msg_data["message"])

                # Get the actual response from the agent with full conversation
                response = st.session_state.runner.process_query(conversation_messages)

                # Create and display AI message
                ai_message = AIMessage(content=response)
                st.session_state.messages.append(
                    {"message": ai_message, "agent": "assistant"}
                )

                # Display response
                st.write(response)

        # Rerun to update chat history
        st.rerun()


def vendor_agent_app():
    # Add progress tracker to sidebar
    with st.sidebar:
        st.header("📋 Application Progress")
        
        # Always show progress (use session_id if available, empty string if not)
        session_id = st.session_state.get("session_id", "")
        completed, total = show_onboarding_progress(session_id)
        
        # Add some helpful information
        st.divider()
        st.subheader("Required Information:")
        st.write("1. 🏢 Company name & country")
        st.write("2. 📋 Compliance certifications") 
        st.write("3. 🔐 Data access requirements")
        
        if completed == total:
            st.success("🎉 Application Complete!")
    
    user_input = orchestrate_streamlit_and_get_user_input(
        "🤖 Third-Party Vendor Onboarding Assistant",
        "Tech Solutions Inc, incorporated in the United States",
        "Shadow Tech Enterprises, incorporated in the United States",
    )
    if "runner" not in st.session_state:
        st.session_state.runner = VendorAgentRunner(
            callbacks=[GalileoCallback()],
            session_id=st.session_state.session_id
        )
    process_input_for_simple_app(user_input)


if __name__ == "__main__":
    vendor_agent_app()
