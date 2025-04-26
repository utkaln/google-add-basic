# Import required libraries
import os
import asyncio
import logging
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types 

print(f"Loading Environment ...")
import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.ERROR)

# Configure API keys
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv())

MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"
MODEL_GPT_4O = "openai/gpt-4o"
MODEL_CLAUDE_SONNET = "anthropic/claude-3-sonnet-20240229"
print(f"Environment setup complete")

# @title Define the get_weather Tool
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---") # Log tool execution
    city_normalized = city.lower().replace(" ", "") # Basic normalization

    # Mock weather data
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have weather information for '{city}'."}

# Example tool usage (optional test)
print(get_weather("New York"))
print(get_weather("Paris"))

# @title Define the Weather Agent
# Use one of the model constants defined earlier
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH # Starting with Gemini

weather_agent = Agent(
    name="weather_agent_v1",
    model=AGENT_MODEL, # Can be a string for Gemini or a LiteLlm object
    description="Provides weather information for specific cities.",
    instruction="You are a helpful weather assistant. "
                "When the user asks for the weather in a specific city, "
                "use the 'get_weather' tool to find the information. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the weather report clearly.",
    tools=[get_weather], # Pass the function directly
)

print(f"Agent '{weather_agent.name}' created using model '{AGENT_MODEL}'.")

# @title Setup Session Service and Runner
# --- Session Management ---
# Key Concept: SessionService stores conversation history & state.
# InMemorySessionService is simple, non-persistent storage for this tutorial.
session_service = InMemorySessionService()

# Define constants for identifying the interaction context
APP_NAME = "weather_tutorial_app"
USER_ID = "unayak"
SESSION_ID = "session_001" # Using a fixed ID for simplicity


session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
)
print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

# Define Runner that orchestrates agent execution loop with tool
runner = Runner(
    agent = weather_agent,
    app_name=APP_NAME,
    session_service=session_service,
)
print(f"Runner created for agent '{runner.agent.name}'.")


# @title Define Agent Interaction Function
async def call_agent_async(user_input: str, runner: Runner, user_id: str, session_id: str):
    """ Sends query to the agent and prints the response.  """
    print(f"\n>>> User Input: {user_input}")
    final_response_text = "Agent failed to respond."

    # Convert user input to ADK formatted content
    content = types.Content(role='user', parts= [types.Part(text=user_input)])

    # Called runner to process the input
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
        if event.is_final_response():
            # If valid response comes from LLM read it as text
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            # Handle error scenario
            elif event.actions and event.actions.escalate:
                final_response_text = f"Event escalation: {event.error_code} - {event.error_message}"
            break
    
    print(f"<<< Agent Response: {final_response_text}")



# Call Agent to begin conversation
if __name__ == "__main__":
    try:
        user_input = input("Enter your city name (e.g., 'New York'): ")
        asyncio.run(call_agent_async(user_input, runner=runner, user_id=USER_ID, session_id=SESSION_ID))
    except Exception as e:
        print(f"Error: {e}")
