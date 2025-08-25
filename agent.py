"""
Third-Party Vendor Agent with OpenAI function calling and Galileo integration
"""
import json
import time
import logging
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from tools import (
    lookup_company_information,
    save_compliance_certifications, 
    save_data_access_requirements,
    get_onboarding_summary,
    OPENAI_TOOLS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce noisy logs from third-party libraries
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

def format_message(role: str, content: str = None, tool_calls=None, tool_call_id=None) -> dict:
    """Format a message for the chat.
    
    Args:
        role: The role of the message (system, user, assistant, tool)
        content: The content of the message
        tool_calls: Tool calls for assistant messages
        tool_call_id: Tool call ID for tool messages
        
    Returns:
        A properly formatted message dictionary
    """
    message = {"role": role}
    
    if content is not None:
        message["content"] = content
        
    if role == "assistant" and tool_calls is not None:
        message["tool_calls"] = [{
            "id": tool_call.get("id", f"toolcall-{i}"),
            "type": tool_call.get("type", "function"),
            "function": {
                "name": tool_call.get("function", {}).get("name", ""),
                "arguments": tool_call.get("function", {}).get("arguments", "{}")
            }
        } for i, tool_call in enumerate(tool_calls)]
        
    if role == "tool" and tool_call_id is not None:
        message["tool_call_id"] = tool_call_id
        
    return message

def execute_tool_call(tool_call, session_id: str, galileo_logger=None) -> str:
    """Execute a tool call and return the result."""
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    # Add galileo_logger to arguments for all tools
    arguments["galileo_logger"] = galileo_logger
    
    # Ensure session_id is included
    if "session_id" not in arguments and session_id:
        arguments["session_id"] = session_id
    
    logger.info(f"Executing tool: {function_name} with arguments: {arguments}")
    
    try:
        if function_name == "lookupCompanyInformation":
            return lookup_company_information(**arguments)
        elif function_name == "saveComplianceCertifications":
            return save_compliance_certifications(**arguments)
        elif function_name == "saveDataAccessRequirements":
            return save_data_access_requirements(**arguments)
        elif function_name == "getOnboardingSummary":
            return get_onboarding_summary(**arguments)
        else:
            return f"Unknown tool: {function_name}"
    except Exception as e:
        logger.error(f"Error executing tool {function_name}: {str(e)}")
        return f"Error executing {function_name}: {str(e)}"

class VendorAgentRunner:
    def __init__(self, callbacks=None, system_prompt: str = None, session_id: str = None, galileo_logger=None):
        try:
            self.session_id = session_id or "vendor-agent"
            self.galileo_logger = galileo_logger
            
            # Initialize OpenAI client
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self.openai_client = OpenAI(api_key=openai_api_key)
            
            # Add system prompt for vendor onboarding context
            default_system_prompt = f"""You are a Third-Party Vendor Onboarding Assistant. Your role is to process vendor applications professionally.

REQUIRED ONBOARDING STEPS (collect in this order):
1. Company's legal name and country of incorporation (use lookupCompanyInformation tool with session_id="{self.session_id}")
2. Compliance certifications they hold (use saveComplianceCertifications tool)  
3. Data access requirements (use saveDataAccessRequirements tool)
4. Provide complete summary (use getOnboardingSummary tool)

CONVERSATION MANAGEMENT:
- When company name provided: look it up, then move user to next step
- When certifications provided: save them, then move user to next step
- When data access provided: assess risk, then move user to next step
- Always use session_id="{self.session_id}" when calling tools that require it

IMPORTANT: After using any tool, always provide a helpful response to guide the user to the next step. Never leave the user hanging without a response. Always acknowledge what was completed and clearly state what needs to happen next.

Please don't share what you have looked up for the user. We don't want vendors to know what we are looking up.

Be professional and treat this as a formal application process."""

            self.system_prompt = system_prompt or default_system_prompt
            
            logger.info(f"Initialized VendorAgentRunner with session_id: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to initialize vendor agent: {e}")
            raise

    def process_query(self, conversation_messages: list) -> str:
        """Process a query with full conversation history using OpenAI function calling"""
        start_time = time.time()
        
        try:
            # Note: We don't start a new session here - the app manages the session
            # We only add spans to the existing session
            # Convert conversation messages to OpenAI format and add system prompt
            messages_to_use = []
            
            # Add system prompt
            messages_to_use.append({"role": "system", "content": self.system_prompt})
            
            # Add conversation history
            for msg in conversation_messages:
                if hasattr(msg, 'content') and hasattr(msg, 'type'):
                    # LangChain message format
                    if msg.type == "human":
                        messages_to_use.append({"role": "user", "content": msg.content})
                    elif msg.type == "ai":
                        messages_to_use.append({"role": "assistant", "content": msg.content})
                elif isinstance(msg, dict):
                    # Already in OpenAI format
                    messages_to_use.append(msg)
            
            logger.info(f"Processing query with {len(messages_to_use)} messages")
            
            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=messages_to_use,
                tools=OPENAI_TOOLS,
                tool_choice="auto"
            )
            
            response_message = response.choices[0].message
            
            # Calculate token counts
            input_tokens = sum(len(msg.get("content", "").split()) for msg in messages_to_use if msg.get("content"))
            output_tokens = len(response_message.content.split()) if response_message.content else 0
            total_tokens = input_tokens + output_tokens
            
            # Log the API call to Galileo if available
            if self.galileo_logger:
                try:
                    self.galileo_logger.add_llm_span(
                        input=messages_to_use,
                        output={
                            "role": response_message.role,
                            "content": response_message.content,
                            "tool_calls": [
                                {
                                    "id": call.id,
                                    "type": call.type,
                                    "function": {
                                        "name": call.function.name,
                                        "arguments": call.function.arguments
                                    }
                                } for call in (response_message.tool_calls or [])
                            ] if response_message.tool_calls else None
                        },
                        model="gpt-4.1",
                        name="Vendor Agent LLM Call",
                        duration_ns=int((time.time() - start_time) * 1000000),
                        metadata={"session_id": self.session_id},
                        tags=["vendor-onboarding", "llm-call"],
                        num_input_tokens=input_tokens,
                        num_output_tokens=output_tokens,
                        total_tokens=total_tokens
                    )
                except Exception as e:
                    logger.warning(f"Failed to log to Galileo: {e}")
            
            # Handle tool calls if present
            if response_message.tool_calls:
                logger.info(f"Processing {len(response_message.tool_calls)} tool calls")
                
                # Add assistant message with tool calls
                messages_to_use.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": call.type,
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments
                            }
                        } for call in response_message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in response_message.tool_calls:
                    tool_result = execute_tool_call(tool_call, self.session_id, self.galileo_logger)
                    
                    # Add tool result to messages
                    messages_to_use.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result
                    })
                
                # Get follow-up response (discourage further tool calls unless needed)
                follow_up_response = self.openai_client.chat.completions.create(
                    model="gpt-4.1",
                    messages=messages_to_use,
                    tools=OPENAI_TOOLS,
                    tool_choice="auto"
                )
                
                final_message = follow_up_response.choices[0].message
                logger.info(f"Follow-up response content: '{final_message.content}'")
                logger.info(f"Follow-up response has tool_calls: {final_message.tool_calls is not None}")
                
                # Log follow-up call to Galileo if available
                if self.galileo_logger:
                    try:
                        follow_up_input_tokens = sum(len(msg.get("content", "").split()) for msg in messages_to_use if msg.get("content"))
                        follow_up_output_tokens = len(final_message.content.split()) if final_message.content else 0
                        follow_up_total_tokens = follow_up_input_tokens + follow_up_output_tokens
                        
                        self.galileo_logger.add_llm_span(
                            input=messages_to_use,
                            output={
                                "role": final_message.role,
                                "content": final_message.content,
                                "tool_calls": None
                            },
                            model="gpt-4.1",
                            name="Vendor Agent Follow-up LLM Call",
                            duration_ns=int((time.time() - start_time) * 1000000),
                            metadata={"session_id": self.session_id},
                            tags=["vendor-onboarding", "llm-call", "follow-up"],
                            num_input_tokens=follow_up_input_tokens,
                            num_output_tokens=follow_up_output_tokens,
                            total_tokens=follow_up_total_tokens
                        )
                    except Exception as e:
                        logger.warning(f"Failed to log follow-up call to Galileo: {e}")
                
                return final_message.content or "No response generated"
            
            return response_message.content or "No response generated"
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Error processing your request: {str(e)}"
