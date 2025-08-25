"""
Streamlit app for Third-Party Vendor Bot with Galileo integration
"""
import os
import time
import uuid
import logging
from typing import List, Dict, Any, Optional

import streamlit as st
from dotenv import load_dotenv
from galileo import galileo_context
from agent import VendorAgentRunner


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_galileo_logger(project_name: str, log_stream_name: str):
    """Initialize Galileo logger similar to your example app."""
    try:
        from galileo import GalileoLogger
        
        # Create the logger without passing parameters to __init__
        galileo_logger = GalileoLogger()
        
        # Set the attributes after creation
        galileo_logger.project_name = project_name
        galileo_logger.log_stream_name = log_stream_name
        
        logger.info(f"Galileo logger initialized for project: {project_name}, stream: {log_stream_name}")
        return galileo_logger
    except Exception as e:
        logger.error(f"Failed to initialize Galileo logger: {e}")
        return None

# Simple message classes for compatibility
class HumanMessage:
    def __init__(self, content: str):
        self.content = content
        self.type = "human"

class AIMessage:
    def __init__(self, content: str):
        self.content = content
        self.type = "ai"


def display_chat_history():
    """Display all messages in the chat history with agent attribution."""
    if not st.session_state.messages:
        return

    for message_data in st.session_state.messages:
        if isinstance(message_data, dict):
            message = message_data.get("message")
            agent = message_data.get("agent", "unknown")

            if isinstance(message, HumanMessage) or agent == "user":
                with st.chat_message("user"):
                    st.write(message.content if hasattr(message, 'content') else str(message))
            elif isinstance(message, AIMessage) or agent == "assistant":
                with st.chat_message("assistant"):
                    st.write(message.content if hasattr(message, 'content') else str(message))
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


def process_chat_message_sync(
    prompt: str,
    message_history: List[Dict[str, Any]], 
    model: str = "gpt-4.1", 
    system_prompt: str = None,
    galileo_logger=None,
    is_streamlit=True,
    session_id: str = None
) -> Dict[str, Any]:
    """Process a chat message similar to your example app."""
    start_time = time.time()
    logger.info(f"Processing chat message: {prompt}")
    
    # Start Galileo trace if available
    if galileo_logger and not galileo_logger.current_parent():
        logger.info("Starting new Galileo trace")
        trace = galileo_logger.start_trace(
            input=prompt,
            name="Vendor Onboarding Query",
            tags=["vendor-onboarding", "chat"],
        )
    
    try:
        # Copy message history to avoid modifying the original
        messages_to_use = message_history.copy()
        
        # Add user message to history
        messages_to_use.append({"role": "user", "content": prompt})
        
        rag_documents = []
        
        # Add system prompt if provided (RAG will now be handled by tools)
        if system_prompt:
            messages_to_use = [
                {"role": "system", "content": system_prompt},
                *messages_to_use
            ]
        
        # Use our agent to process the query
        if hasattr(st.session_state, 'runner') and st.session_state.runner:
            # Convert the messages to LangChain format for the agent
            conversation_messages = []
            for msg in messages_to_use:
                if msg['role'] == 'user':
                    conversation_messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    conversation_messages.append(AIMessage(content=msg['content']))
            
            response_text = st.session_state.runner.process_query(conversation_messages)
        else:
            response_text = "Agent not available - runner not initialized"
        
        # Create response message object
        response_message = type('obj', (object,), {
            'content': response_text,
            'role': 'assistant',
            'tool_calls': None
        })
        
        # Calculate token counts
        input_tokens = sum(len(msg.get("content", "").split()) for msg in messages_to_use if msg.get("content"))
        output_tokens = len(response_text.split()) if response_text else 0
        total_tokens = input_tokens + output_tokens
        
        # Add final assistant response to history
        if response_message.content:
            messages_to_use.append({"role": "assistant", "content": response_message.content})
        
        # Conclude the Galileo trace if available
        if galileo_logger and is_streamlit:
            logger.info("Concluding Galileo trace")
            galileo_logger.conclude(
                output=response_message.content,
                duration_ns=int((time.time() - start_time) * 1000000),
                status_code=200
            )
            galileo_logger.flush()
        
        # Return the results
        return {
            "response_message": response_message,
            "updated_history": messages_to_use,
            "rag_documents": rag_documents,
            "tool_results": [],
            "total_tokens": total_tokens
        }
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        
        # Log error to Galileo if available
        if galileo_logger and is_streamlit:
            logger.info("Logging error to Galileo")
            galileo_logger.conclude(
                output=f"Error: {str(e)}",
                duration_ns=int((time.time() - start_time) * 1000000),
                status_code=500
            )
        
        # Re-raise the exception
        raise

def process_input_for_simple_app(user_input: str | None):
    if user_input:
        # Add user message to chat history immediately
        user_message = HumanMessage(content=user_input)
        st.session_state.messages.append({"message": user_message, "agent": "user"})

        # Display the user message immediately
        with st.chat_message("user"):
            st.write(user_input)

        # Convert session state messages to the format expected by process_chat_message_sync
        message_history = []
        for msg_data in st.session_state.messages:
            if isinstance(msg_data, dict) and "message" in msg_data:
                msg = msg_data["message"]
                if hasattr(msg, 'type'):
                    if msg.type == "human":
                        message_history.append({"role": "user", "content": msg.content})
                    elif msg.type == "ai":
                        message_history.append({"role": "assistant", "content": msg.content})

        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    # Use the main process_chat_message_sync function like your example
                    chat_result = process_chat_message_sync(
                        prompt=user_input,
                        message_history=message_history[:-1],  # Exclude the current user message
                        model="gpt-4.1",
                        system_prompt=f"""You are a Third-Party Vendor Onboarding Assistant. Your role is to process vendor applications professionally.

REQUIRED ONBOARDING STEPS (collect in this order):
1. Company's legal name and country of incorporation (use lookupCompanyInformation tool with session_id="{st.session_state.session_id}")
2. Compliance certifications they hold (use saveComplianceCertifications tool)  
3. Data access requirements (use saveDataAccessRequirements tool)
4. Provide complete summary (use getOnboardingSummary tool)

CONVERSATION MANAGEMENT:
- When company name provided: look it up, then move user to next step
- When certifications provided: save them, then move user to next step
- When data access provided: assess risk, then move user to next step
- Always use session_id="{st.session_state.session_id}" when calling tools that require it

Please don't share what you have looked up for the user. We don't want vendors to know what we are looking up.

Be professional and treat this as a formal application process.""",
                        galileo_logger=getattr(st.session_state, 'galileo_logger', None),
                        is_streamlit=True,
                        session_id=st.session_state.session_id
                    )

                    # Get the response and display it
                    response_text = chat_result["response_message"].content
                    
                    # Create and add AI message to history
                    ai_message = AIMessage(content=response_text)
                    st.session_state.messages.append(
                        {"message": ai_message, "agent": "assistant"}
                    )

                    # Display response
                    st.write(response_text)
                
                except Exception as e:
                    error_msg = f"Error processing request: {str(e)}"
                    st.error(error_msg)
                    logger.error(f"Error in process_input_for_simple_app: {e}")

        # Don't rerun - let Streamlit handle the display naturally


def vendor_agent_app():
    # Initialize session state first
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        session_id = str(uuid.uuid4())[:10]
        st.session_state.session_id = session_id
        try:
            # Initialize Galileo logger like your example app
            project_name = os.getenv("GALILEO_PROJECT_NAME", "third-party-vendor-bot")
            log_stream_name = os.getenv("GALILEO_LOG_STREAM_NAME", "vendor-onboarding")
            st.session_state.galileo_logger = initialize_galileo_logger(project_name, log_stream_name)
            
            # Start a Galileo session for this Streamlit session
            if st.session_state.galileo_logger:
                st.session_state.galileo_logger.start_session(
                    name=f"Vendor Bot Session {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
            
            # Mark that we've started the session
            st.session_state.galileo_session_started = True
            
            logger.info(f"Started Galileo session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start Galileo session: {str(e)}")
            st.error(f"Failed to start Galileo session: {str(e)}")
            # Continue without Galileo logging
            st.session_state.galileo_logger = None
            st.session_state.galileo_session_started = False
        # Add welcome message with clear next steps
        welcome_message = AIMessage(content="""Welcome to the Third-Party Vendor Application Portal.

Please submit your vendor application by providing the following information:

1. **Company Information**: Your company's legal name and country of incorporation
2. **Compliance Certifications**: Any relevant certifications (SOC 2, ISO 27001, etc.)
3. **Data Access Requirements**: What data you need access to

I'll guide you through each step. Let's start with your company information.""")
        
        st.session_state.messages.append({"message": welcome_message, "agent": "assistant"})

    # Add progress tracker to sidebar
    with st.sidebar:
        st.header("📋 Application Progress")
        if "session_id" in st.session_state:
            completed, total = show_onboarding_progress(st.session_state.session_id)
            
            # Add some helpful information
            st.divider()
            st.subheader("Required Information:")
            st.write("1. 🏢 Company name & country")
            st.write("2. 📋 Compliance certifications") 
            st.write("3. 🔐 Data access requirements")
            
            if completed == total:
                st.success("🎉 Application Complete!")
        else:
            st.info("Start a session to see progress")
    
    # Initialize runner first, before getting user input
    if "runner" not in st.session_state:
        # Get Galileo logger from session state (may be None if initialization failed)
        galileo_logger = getattr(st.session_state, 'galileo_logger', None)
        
        st.session_state.runner = VendorAgentRunner(
            session_id=st.session_state.session_id,
            galileo_logger=galileo_logger
        )
        logger.info(f"Created agent runner for session: {st.session_state.session_id}")
    
    user_input = orchestrate_streamlit_and_get_user_input(
        "🤖 Third-Party Vendor Onboarding Assistant",
        "Tech Solutions Inc, incorporated in the United States",
        "Shadow Tech Enterprises, incorporated in the United States",
    )
    process_input_for_simple_app(user_input)


if __name__ == "__main__":
    vendor_agent_app()
