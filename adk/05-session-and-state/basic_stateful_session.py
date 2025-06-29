import asyncio
import uuid
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from question_answering_agent import question_answering_agent

load_dotenv()

async def main():
    initial_state = {
        "user_name": "Brandon Hancock",
        "user_preferences": """
            I like to play Pickleball, Disc Golf, and Tennis.
            My favorite food is Mexican.
            My favorite TV show is Game of Thrones.
            Loves it when people like and subscribe to his YouTube channel.
        """,
    }

    APP_NAME = "Dino bot"
    USER_ID = "Dino"
    SESSION_ID = str(uuid.uuid4())

    session_service_stateful = InMemorySessionService()

    await session_service_stateful.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )

    print("Create new session")
    print(f"\t Session id: {SESSION_ID}")

    runner = Runner(
        agent=question_answering_agent,
        app_name=APP_NAME,
        session_service=session_service_stateful
    )

    new_message = types.Content(
        role="user", parts=[types.Part(text="What is Brandon's favorite TV show?")]
    )

    for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=new_message):
        if event.is_final_response:
            if event.content and event.content.parts:
                print(f"Final Response: {event.content.parts[0].text}")

    print("==== Session Event Exploration ====")
    session = await session_service_stateful.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    for key, value in session.state.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())