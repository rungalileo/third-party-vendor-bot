# Third-Party Vendor Onboarding Bot

A comprehensive demo showcasing AI agent monitoring and observability in a real-world vendor onboarding scenario. Built with LangGraph and Streamlit, this application demonstrates how to monitor complex AI workflows with RAG capabilities using Galileo's observability platform.

## Demo Highlights

- 🤖 **Multi-Step AI Workflow**: LangGraph-powered agent with structured vendor onboarding process
- 📊 **Complete Observability**: Full conversation and tool usage monitoring with Galileo
- 🏢 **RAG Integration**: Vector database search with Pinecone for company risk assessment
- 📋 **Progress Visualization**: Real-time tracking of multi-step application workflows
- 💬 **Interactive Interface**: Production-ready Streamlit chat interface
- 🛠️ **Custom Tool Usage**: Demonstrates tool calling patterns and state management

## Architecture Overview

This demo showcases a production-ready AI agent architecture with:

### Custom Tools
1. **lookup_company_information**: Demonstrates RAG search with Pinecone vector database
2. **save_compliance_certifications**: Shows structured data collection and validation  
3. **save_data_access_requirements**: Captures and processes vendor requirements
4. **get_onboarding_summary**: Provides session state summarization

### Monitoring & Observability
- **Complete trace visibility** of multi-step agent workflows
- **Tool usage analytics** showing RAG search patterns and data collection
- **Session tracking** across complex onboarding processes
- **Performance metrics** for response times and completion rates

## Setup

### 1. Clone the repository
```bash
git clone <repository-url>
cd third-party-vendor-bot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Copy the example environment file and add your API keys:
```bash
cp env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
GALILEO_API_KEY=your_galileo_api_key_here
GALILEO_PROJECT=your_galileo_project_here
GALILEO_LOG_STREAM=your_galileo_log_stream_here
GALILEO_CONSOLE_URL=your_galileo_console_url_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=your_pinecone_index_name_here
```

### 5. Set up the company database
Before running the application, you need to set up the Pinecone vector database with company information:

```bash
cd scripts
python setup_pinecone.py
```

This will load the company directory documents into Pinecone for RAG search functionality.

### 6. Run the application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Deployment

### Streamlit Cloud Deployment

This application is ready for deployment on Streamlit Cloud. The secrets are configured to work seamlessly in both local development and cloud environments.

#### Local Development
- Uses `.env` file for environment variables
- Run with `streamlit run app.py`

#### Streamlit Cloud Deployment
1. **Push to GitHub**: Ensure your code is in a GitHub repository
2. **Connect to Streamlit Cloud**: 
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
3. **Configure Secrets**: In the Streamlit Cloud dashboard, add your secrets:
   ```toml
   [secrets]
   OPENAI_API_KEY = "your_openai_api_key_here"
   GALILEO_API_KEY = "your_galileo_api_key_here"
   GALILEO_PROJECT = "your_galileo_project_here"
   GALILEO_LOG_STREAM = "your_galileo_log_stream_here"
   GALILEO_CONSOLE_URL = "your_galileo_console_url_here"
   PINECONE_API_KEY = "your_pinecone_api_key_here"
   PINECONE_INDEX_NAME = "your_pinecone_index_name_here"
   ```
4. **Deploy**: Streamlit Cloud will automatically deploy your app

**Note**: The `.streamlit/secrets.toml` file is for local reference only and is excluded from git via `.gitignore`. Use the Streamlit Cloud secrets manager for production deployment.

## Running the Demo

### For Demo Audiences
1. **Launch Application**: Start with the vendor onboarding assistant's welcome message
2. **Showcase Workflow**: Use example companies to demonstrate the structured 3-step process
3. **Highlight Monitoring**: Show real-time progress tracking and session management
4. **Demonstrate RAG**: Watch company database searches in action
5. **Review Analytics**: Check Galileo dashboard for complete workflow visibility

### Demo Flow Examples
**Company Lookup Demo:**
- "Tech Solutions Inc, incorporated in the United States"
- "Shadow Tech Enterprises, incorporated in the United States"

**Compliance Collection Demo:**
- "We have SOC 2 Type II, ISO 27001, and GDPR compliance certifications"

**Data Access Demo:**
- "We need access to customer contact information and billing data for our CRM integration"

Each step demonstrates different aspects of agent workflow monitoring and tool usage analytics.

## Observability with Galileo

This demo showcases comprehensive AI agent monitoring capabilities through [Galileo's observability platform](https://v2docs.galileo.ai/sdk-api/third-party-integrations/openai-agents/openai-agents):

### What You'll See in Galileo
- **Complete conversation flows** with step-by-step agent decision making
- **Tool usage patterns** showing RAG searches, data validation, and state updates
- **Multi-turn conversation tracking** across complex vendor onboarding sessions
- **Performance analytics** including response times, token usage, and completion rates
- **Error tracking and debugging** for failed tool calls or workflow issues

### Demo Value
- Demonstrates production-ready monitoring for complex AI workflows
- Shows how to track business process completion (vendor onboarding steps)
- Illustrates observability for RAG systems and vector database interactions
- Provides visibility into session state management and data persistence

## Project Structure

```
third-party-vendor-bot/
├── app.py                      # Main Streamlit application
├── agent.py                    # LangGraph agent with vendor onboarding workflow
├── tools.py                    # Vendor-specific tools (company lookup, data saving)
├── rag_tool.py                # RAG system for company database search
├── requirements.txt           # Python dependencies
├── env.example               # Example environment variables
├── .streamlit/               # Streamlit configuration (git-ignored)
│   └── secrets.toml          # Local secrets for development
├── company_directory/        # Company information files for RAG
│   ├── data_miners_unlimited.md
│   ├── global_consulting_ltd.md
│   ├── offshore_solutions_bv.md
│   ├── quickfix_consulting.md
│   ├── secure_data_systems.md
│   ├── shadow_tech_enterprises.md
│   └── tech_solutions_inc.md
├── scripts/
│   ├── setup_pinecone.py     # Script to initialize Pinecone with company data
│   └── README.md            # Setup instructions
└── README.md               # This file
```

## Requirements

- Python 3.8+
- OpenAI API key (required)
- Pinecone API key (required for company database)
- Galileo API key and project configuration (optional for monitoring)

## Dependencies

- `streamlit`: Web application framework
- `langchain`: LangChain framework for LLM applications
- `langchain-openai`: OpenAI integration for LangChain
- `langgraph`: State machine framework for agent workflows
- `langchain-pinecone`: Pinecone vector database integration
- `pinecone-client`: Pinecone Python client
- `galileo`: Galileo monitoring SDK
- `python-dotenv`: Environment variable management

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.
