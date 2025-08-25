"""
Third-Party Vendor Agent with LangGraph and Galileo integration
"""
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from tools import (
    lookup_company_information,
    save_compliance_certifications, 
    save_data_access_requirements,
    get_onboarding_summary
)

# Define the state for our graph
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Our vendor onboarding tools
VENDOR_TOOLS = [
    lookup_company_information,
    save_compliance_certifications, 
    save_data_access_requirements,
    get_onboarding_summary
]

def get_vendor_agent(system_prompt: str = None) -> CompiledStateGraph:
    """Create the vendor agent with tools"""
    
    # Create the LLM with vendor tools
    llm_with_vendor_tools = ChatOpenAI(
        model="gpt-4o-mini",
        name="Vendor Assistant"
    ).bind_tools(VENDOR_TOOLS)

    def invoke_vendor_chatbot(state):
        # Only add system message if one is provided
        if system_prompt:
            system_message = SystemMessage(content=system_prompt)
            messages = [system_message] + state["messages"]
        else:
            # No system prompt - just use the conversation messages as-is
            messages = state["messages"]
        message = llm_with_vendor_tools.invoke(messages)
        return {"messages": [message]}

    # Build the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("vendor_chatbot", invoke_vendor_chatbot)

    tool_node = ToolNode(tools=VENDOR_TOOLS)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges("vendor_chatbot", tools_condition)
    graph_builder.add_edge("tools", "vendor_chatbot")
    graph_builder.add_edge(START, "vendor_chatbot")

    return graph_builder.compile()

class VendorAgentRunner:
    def __init__(self, callbacks=None, system_prompt: str = None, session_id: str = None):
        try:
            self.session_id = session_id or "vendor-agent"
            
            # Add system prompt for vendor onboarding context
            default_system_prompt = f"""You are a Third-Party Vendor Onboarding Assistant. Your role is to process vendor applications professionally.

REQUIRED ONBOARDING STEPS (collect in this order):
1. Company's legal name and country of incorporation (use lookup_company_information tool with session_id="{self.session_id}")
2. Compliance certifications they hold (use save_compliance_certifications tool)  
3. Data access requirements (use save_data_access_requirements tool)
4. Provide complete summary (use get_onboarding_summary tool)


CONVERSATION MANAGEMENT:
- When company name provided: look it up, then move user to next step
- When certifications provided: save them, then move user to next step
- When data access provided: assess risk, then move user to next step
- Always use session_id="{self.session_id}" when calling tools that require it

Please don't share what you have looked up for the user. We don't want vendors to know what we are looking up.

Be professional and treat this as a formal application process."""

            final_system_prompt = system_prompt or default_system_prompt
            self.graph = get_vendor_agent(system_prompt=final_system_prompt)
            self.config = {"configurable": {"thread_id": self.session_id}}

            if callbacks:
                self.config["callbacks"] = callbacks
        except Exception as e:
            print(f"[ERROR] Failed to initialize vendor agent: {e}")
            raise

    def process_query(self, conversation_messages: list[BaseMessage]) -> str:
        """Process a query with full conversation history"""
        try:
            initial_state = {"messages": conversation_messages}
            result = self.graph.invoke(initial_state, self.config)

            # Return the last message content
            if result["messages"]:
                return result["messages"][-1].content
            return "No response generated"
        except Exception as e:
            print(f"[ERROR] Error processing query: {e}")
            return f"Error processing your request: {str(e)}"
