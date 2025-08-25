"""
Tools for the Third-Party Vendor Bot - Onboarding Flow
"""
import json
import time
import logging
from typing import Optional
from rag_tool import get_rag_system

# Global storage for session data (in a real app, this would be a database)
_onboarding_sessions = {}

# Global RAG instance - initialized once and reused
_company_rag_instance = None

def _check_and_mark_application_complete(session_id: str):
    """Check if all required information is collected and mark application as complete"""
    if session_id in _onboarding_sessions:
        session_data = _onboarding_sessions[session_id]
        required_keys = ["company_name", "compliance_certifications", "data_access_needs"]
        
        # Check if all required information is present
        if all(key in session_data for key in required_keys):
            session_data["application_complete"] = True
            print(f"[APPLICATION] Marked application as complete for session {session_id}")

def _get_company_rag_instance():
    """Get or create the company RAG instance with lazy loading"""
    global _company_rag_instance
    
    if _company_rag_instance is None:
        # Create RAG instance that connects to existing vectors in Pinecone
        # Documents should be pre-loaded using scripts/setup_pinecone.py
        # Always use the environment variable for index name
        _company_rag_instance = get_rag_system(
            index_name=None,  # Will use PINECONE_INDEX_NAME from environment
            namespace="company-directory",  # Updated to match setup script
            description="Company Database",
        )
    
    return _company_rag_instance

def _log_to_galileo(galileo_logger, tool_name: str, input_data: dict, output_data: dict, start_time: float) -> None:
    """
    Helper function to log tool execution to Galileo.
    
    Args:
        galileo_logger: Galileo logger for observability
        tool_name: Name of the tool being executed
        input_data: Input parameters to the tool
        output_data: Output from the tool
        start_time: The start time of the tool execution
    """
    if galileo_logger:
        galileo_logger.add_tool_span(
            input=json.dumps(input_data),
            output=json.dumps(output_data),
            name=tool_name,
            duration_ns=int((time.time() - start_time) * 1000000),
            metadata={str(k): str(v) for k, v in input_data.items()},
            tags=["vendor-onboarding", tool_name.lower().replace("_", "-")]
        )

def lookup_company_information(company_name: str, country: str = "", session_id: str = "", galileo_logger=None) -> str:
    """
    Look up information about a company in our vendor database using RAG search.
    This tool searches through our comprehensive company database to find legal information,
    compliance status, risk assessments, and other relevant details.
    
    Args:
        company_name: The legal name of the company to look up
        country: Optional country of incorporation to help narrow the search
        session_id: Session identifier to track progress
        
    Returns:
        Detailed company information including risk assessment and compliance status
    """
    start_time = time.time()
    input_data = {
        "company_name": company_name,
        "country": country,
        "session_id": session_id
    }
    
    try:
        # Create search query
        search_query = f"company information for {company_name}"
        if country:
            search_query += f" incorporated in {country}"
            
        print(f"[COMPANY LOOKUP] Searching for: {search_query}")
        
        # Get RAG instance (handles initialization and document loading internally)
        rag_instance = _get_company_rag_instance()
        
        # Search for company information with Galileo tracing
        result = rag_instance.search(search_query, galileo_logger=galileo_logger)
        
        # Mark company lookup as complete in session
        if session_id:
            if session_id not in _onboarding_sessions:
                _onboarding_sessions[session_id] = {}
            _onboarding_sessions[session_id]["company_name"] = company_name
            _onboarding_sessions[session_id]["company_lookup_complete"] = True
            
            # Check if application is now complete
            _check_and_mark_application_complete(session_id)
        
        # Log to Galileo
        output_data = {
            "result": result,
            "session_updated": session_id is not None,
            "status": "success"
        }
        _log_to_galileo(galileo_logger, "Company Lookup", input_data, output_data, start_time)
        
        return result
        
    except Exception as e:
        error_msg = f"Error looking up company information: {str(e)}"
        output_data = {
            "error": str(e),
            "status": "error"
        }
        _log_to_galileo(galileo_logger, "Company Lookup", input_data, output_data, start_time)
        return error_msg

def save_compliance_certifications(session_id: str, company_name: str, certifications: str, galileo_logger=None) -> str:
    """
    Save compliance certifications information for a vendor during onboarding.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        company_name: Name of the company being onboarded
        certifications: Description of compliance certifications (e.g., "SOC 2, ISO 27001, GDPR compliant")
        
    Returns:
        Confirmation message with saved information
    """
    start_time = time.time()
    input_data = {
        "session_id": session_id,
        "company_name": company_name,
        "certifications": certifications
    }
    
    try:
        # Initialize session if it doesn't exist
        if session_id not in _onboarding_sessions:
            _onboarding_sessions[session_id] = {}
            
        # Save certification information
        _onboarding_sessions[session_id].update({
            "company_name": company_name,
            "compliance_certifications": certifications,
            "certifications_saved_at": "2024-01-15"  # In real app, use actual timestamp
        })
        
        print(f"[COMPLIANCE] Saved certifications for {company_name}: {certifications}")
        
        # Check if application is now complete
        _check_and_mark_application_complete(session_id)
        
        result = f"✅ Compliance certifications saved for {company_name}:\n{certifications}\n\nThis information has been stored for the vendor risk assessment."
        
        # Log to Galileo
        output_data = {
            "result": result,
            "status": "success",
            "certifications_count": len(certifications.split(",")) if certifications else 0
        }
        _log_to_galileo(galileo_logger, "Save Compliance Certifications", input_data, output_data, start_time)
        
        return result
        
    except Exception as e:
        error_msg = f"Error saving compliance certifications: {str(e)}"
        output_data = {
            "error": str(e),
            "status": "error"
        }
        _log_to_galileo(galileo_logger, "Save Compliance Certifications", input_data, output_data, start_time)
        return error_msg

def save_data_access_requirements(session_id: str, company_name: str, data_access_needs: str, galileo_logger=None) -> str:
    """
    Save data access requirements for a vendor during onboarding.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        company_name: Name of the company being onboarded
        data_access_needs: Description of data access requirements
        
    Returns:
        Confirmation message
    """
    start_time = time.time()
    input_data = {
        "session_id": session_id,
        "company_name": company_name,
        "data_access_needs": data_access_needs
    }
    
    try:
        # Initialize session if it doesn't exist
        if session_id not in _onboarding_sessions:
            _onboarding_sessions[session_id] = {}
            
        # Save data access information
        _onboarding_sessions[session_id].update({
            "company_name": company_name,
            "data_access_needs": data_access_needs,
            "data_access_saved_at": "2024-01-15"  # In real app, use actual timestamp
        })
        
        print(f"[DATA ACCESS] Saved requirements for {company_name}: {data_access_needs}")
        
        # Check if application is now complete
        _check_and_mark_application_complete(session_id)
        
        result = f"✅ Data access requirements saved for {company_name}:\n{data_access_needs}\n\nThis information has been stored for review."
        
        # Log to Galileo
        output_data = {
            "result": result,
            "status": "success",
            "data_requirements_length": len(data_access_needs) if data_access_needs else 0
        }
        _log_to_galileo(galileo_logger, "Save Data Access Requirements", input_data, output_data, start_time)
        
        return result
        
    except Exception as e:
        error_msg = f"Error saving data access requirements: {str(e)}"
        output_data = {
            "error": str(e),
            "status": "error"
        }
        _log_to_galileo(galileo_logger, "Save Data Access Requirements", input_data, output_data, start_time)
        return error_msg

def get_onboarding_summary(session_id: str, galileo_logger=None) -> str:
    """
    Get a summary of the current onboarding session data.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        
    Returns:
        Summary of all collected onboarding information
    """
    start_time = time.time()
    input_data = {"session_id": session_id}
    
    try:
        if session_id not in _onboarding_sessions:
            result = "No application data found. Please start the vendor application process."
            output_data = {
                "result": result,
                "status": "no_data"
            }
            _log_to_galileo(galileo_logger, "Get Onboarding Summary", input_data, output_data, start_time)
            return result
            
        session_data = _onboarding_sessions[session_id]
        
        summary = "📋 VENDOR APPLICATION SUMMARY\n\n"
        
        if "company_name" in session_data:
            summary += f"**Company:** {session_data['company_name']}\n"
            
        if "compliance_certifications" in session_data:
            summary += f"**Compliance Certifications:** {session_data['compliance_certifications']}\n"
            
        if "data_access_needs" in session_data:
            summary += f"**Data Access Requirements:** {session_data['data_access_needs']}\n"
        
        # Count completed steps
        completed_items = sum(1 for key in ["company_name", "compliance_certifications", "data_access_needs"] if key in session_data)
        total_items = 3
        
        summary += f"\n**Application Status:** {completed_items}/{total_items} sections completed\n"
        
        if completed_items == total_items:
            # Mark application as complete if not already marked
            session_data["application_complete"] = True
            summary += "\n✅ **Application Complete** - All required information has been collected."
        else:
            remaining = []
            if "company_name" not in session_data:
                remaining.append("Company information")
            if "compliance_certifications" not in session_data:
                remaining.append("Compliance certifications") 
            if "data_access_needs" not in session_data:
                remaining.append("Data access requirements")
            summary += f"\n⏳ **Pending:** {', '.join(remaining)}"
        
        # Log to Galileo
        output_data = {
            "result": summary,
            "status": "success",
            "completed_items": completed_items,
            "total_items": total_items,
            "application_complete": completed_items == total_items
        }
        _log_to_galileo(galileo_logger, "Get Onboarding Summary", input_data, output_data, start_time)
        
        return summary
        
    except Exception as e:
        error_msg = f"Error retrieving application summary: {str(e)}"
        output_data = {
            "error": str(e),
            "status": "error"
        }
        _log_to_galileo(galileo_logger, "Get Onboarding Summary", input_data, output_data, start_time)
        return error_msg

# OpenAI tool definitions for function calling
VENDOR_TOOLS = {
    "lookupCompanyInformation": {
        "description": "Look up information about a company in the vendor database using RAG search. This searches through comprehensive company database to find legal information, compliance status, risk assessments, and other relevant details.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The legal name of the company to look up"
                },
                "country": {
                    "type": "string",
                    "description": "Optional country of incorporation to help narrow the search"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session identifier to track progress"
                }
            },
            "required": ["company_name", "session_id"]
        }
    },
    "saveComplianceCertifications": {
        "description": "Save compliance certifications information for a vendor during onboarding.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier for this onboarding process"
                },
                "company_name": {
                    "type": "string",
                    "description": "Name of the company being onboarded"
                },
                "certifications": {
                    "type": "string",
                    "description": "Description of compliance certifications (e.g., 'SOC 2, ISO 27001, GDPR compliant')"
                }
            },
            "required": ["session_id", "company_name", "certifications"]
        }
    },
    "saveDataAccessRequirements": {
        "description": "Save data access requirements for a vendor during onboarding.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier for this onboarding process"
                },
                "company_name": {
                    "type": "string",
                    "description": "Name of the company being onboarded"
                },
                "data_access_needs": {
                    "type": "string",
                    "description": "Description of data access requirements"
                }
            },
            "required": ["session_id", "company_name", "data_access_needs"]
        }
    },
    "getOnboardingSummary": {
        "description": "Get a summary of the current onboarding session data.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Unique session identifier for this onboarding process"
                }
            },
            "required": ["session_id"]
        }
    }
}

# Format tools for OpenAI API
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
    }
    for name, tool in VENDOR_TOOLS.items()
]

__all__ = [
    "lookup_company_information", 
    "save_compliance_certifications", 
    "save_data_access_requirements",
    "get_onboarding_summary",
    "VENDOR_TOOLS",
    "OPENAI_TOOLS"
]
