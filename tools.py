"""
Tools for the Third-Party Vendor Bot - Onboarding Flow
"""
from langchain_core.tools import tool
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

@tool
def lookup_company_information(company_name: str, country: str = "", session_id: str = "") -> str:
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
    try:
        # Create search query
        search_query = f"company information for {company_name}"
        if country:
            search_query += f" incorporated in {country}"
            
        print(f"[COMPANY LOOKUP] Searching for: {search_query}")
        
        # Get RAG instance (handles initialization and document loading internally)
        rag_instance = _get_company_rag_instance()
        
        # Search for company information
        result = rag_instance.search(search_query)
        
        # Mark company lookup as complete in session
        if session_id:
            if session_id not in _onboarding_sessions:
                _onboarding_sessions[session_id] = {}
            _onboarding_sessions[session_id]["company_name"] = company_name
            _onboarding_sessions[session_id]["company_lookup_complete"] = True
            
            # Check if application is now complete
            _check_and_mark_application_complete(session_id)
        
        return result
        
    except Exception as e:
        return f"Error looking up company information: {str(e)}"

@tool
def save_compliance_certifications(session_id: str, company_name: str, certifications: str) -> str:
    """
    Save compliance certifications information for a vendor during onboarding.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        company_name: Name of the company being onboarded
        certifications: Description of compliance certifications (e.g., "SOC 2, ISO 27001, GDPR compliant")
        
    Returns:
        Confirmation message with saved information
    """
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
        
        return f"✅ Compliance certifications saved for {company_name}:\n{certifications}\n\nThis information has been stored for the vendor risk assessment."
        
    except Exception as e:
        return f"Error saving compliance certifications: {str(e)}"

@tool
def save_data_access_requirements(session_id: str, company_name: str, data_access_needs: str) -> str:
    """
    Save data access requirements for a vendor during onboarding.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        company_name: Name of the company being onboarded
        data_access_needs: Description of data access requirements
        
    Returns:
        Confirmation message
    """
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
        
        return f"✅ Data access requirements saved for {company_name}:\n{data_access_needs}\n\nThis information has been stored for review."
        
    except Exception as e:
        return f"Error saving data access requirements: {str(e)}"

@tool
def get_onboarding_summary(session_id: str) -> str:
    """
    Get a summary of the current onboarding session data.
    
    Args:
        session_id: Unique session identifier for this onboarding process
        
    Returns:
        Summary of all collected onboarding information
    """
    try:
        if session_id not in _onboarding_sessions:
            return "No application data found. Please start the vendor application process."
            
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
                
        return summary
        
    except Exception as e:
        return f"Error retrieving application summary: {str(e)}"

__all__ = [
    "lookup_company_information", 
    "save_compliance_certifications", 
    "save_data_access_requirements",
    "get_onboarding_summary"
]
