# OpenAI Agent with Galileo Integration

A Streamlit application that demonstrates the integration of OpenAI Agents SDK with Galileo for monitoring and evaluation.

## Features

- 🤖 **OpenAI Agent**: Powered by GPT-4 with tool usage capabilities
- 📊 **Galileo Integration**: Monitor agent performance and behavior
- 🛠️ **Custom Tools**: Time, calculation, and text formatting tools
- 💬 **Chat Interface**: User-friendly Streamlit chat interface
- 🔒 **Secure**: API keys handled securely with environment variables

## Available Tools

The agent comes with three basic tools:

1. **get_current_time**: Returns the current date and time
2. **calculate**: Performs mathematical calculations safely
3. **format_text**: Formats text in uppercase, lowercase, or title case

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
GALILEO_API_KEY=your_galileo_api_key_here  # Optional
```

### 5. Run the application
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Usage

1. **Enter API Keys**: In the sidebar, enter your OpenAI API key (required) and Galileo API key (optional)
2. **Start Chatting**: Type your message in the chat input
3. **Watch the Agent Work**: The agent will respond and use tools when needed
4. **Monitor with Galileo**: If you provided a Galileo API key, you can monitor the agent's performance in the Galileo dashboard

## Example Conversations

Try these example prompts:

- "What time is it right now?"
- "Can you calculate 15 * 23 + 7?"
- "Format the text 'hello world' in uppercase"
- "What's the current time and can you calculate 2^10?"

## Galileo Integration

This app integrates with [Galileo](https://v2docs.galileo.ai/sdk-api/third-party-integrations/openai-agents/openai-agents) for monitoring OpenAI Agents. When you provide a Galileo API key:

- All agent events are logged to Galileo
- You can view traces, spans, and metrics in the Galileo dashboard
- Monitor agent performance and behavior patterns
- Set up alerts and guardrails

## Project Structure

```
third-party-vendor-bot/
├── app.py              # Main Streamlit application
├── agent.py            # OpenAI Agent with Galileo integration
├── tools.py            # Custom tools for the agent
├── requirements.txt    # Python dependencies
├── env.example         # Example environment variables
└── README.md          # This file
```

## Requirements

- Python 3.8+
- OpenAI API key
- Galileo API key (optional)

## Dependencies

- `streamlit`: Web application framework
- `openai`: OpenAI API client
- `galileo-sdk`: Galileo monitoring SDK
- `python-dotenv`: Environment variable management

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.
