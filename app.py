import streamlit as st
from dotenv import load_dotenv
load_dotenv()
import speech_recognition as sr
import asyncio
from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer
from graph import graph



st.set_page_config(page_title="🎙️ AI English Interview Coach", layout="centered")

# OpenAI client
openai = AsyncOpenAI()
messages = []

# Exit keywords
EXIT_KEYWORDS = {"stop", "exit", "quit", "bye"}

# Session state
if "history" not in st.session_state:
    st.session_state.history = []

# TTS only for assistant
async def tts(text: str):
    async with openai.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="echo",
        input=text,
        instructions="Speak in a polite and helpful tone.",
        response_format="pcm"
    ) as response:
        await LocalAudioPlayer().play(response)

# Listen from mic and return text
def listen_and_recognize():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎧 Listening... Please speak.")
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source)
        try:
            stt = r.recognize_google(audio)
            return stt
        except sr.UnknownValueError:
            st.warning("⚠️ Sorry, I could not understand that.")
        except sr.RequestError as e:
            st.error(f"Google Speech API error: {e}")
    return None

# Handle one complete conversation turn
async def handle_conversation():
    user_input = listen_and_recognize()
    if not user_input:
        return

    # Add user input to history and context
    st.session_state.history.append(("user", user_input))
    messages.append({"role": "user", "content": user_input})

    # Exit condition
    if user_input.strip().lower() in EXIT_KEYWORDS:
        bye_message = "Okay, exiting now. Have a great day!"
        st.session_state.history.append(("assistant", bye_message))
        await tts(bye_message)
        st.rerun()  # ⬅️ rerun immediately to show chat
        return

    # Stream assistant response
    for event in graph.stream({"messages": messages}, stream_mode="values"):
        if "messages" in event:
            assistant_msg = event["messages"][-1].content.strip()
            last_user_msg = messages[-1]["content"].strip()

            # Skip echo replies
            if assistant_msg.lower() != last_user_msg.lower():
                messages.append({"role": "assistant", "content": assistant_msg})
                st.session_state.history.append(("assistant", assistant_msg))
                await tts(assistant_msg)
                st.rerun()  # ⬅️ force UI update after assistant reply
                return

# ---- UI ----
st.title("🗣️ AI English Interview Coach")
st.markdown("""
Speak naturally. The AI will help you improve your answers for interviews by correcting mistakes and improving fluency.
""")

# Chat display with markdown chat bubbles
for sender, msg in st.session_state.history:
    if sender == "user":
        st.markdown(f"""
        <div style="background-color:#000000; padding:10px; border-radius:10px; margin-bottom:5px">
        <b>👤 You:</b> {msg}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background-color:#000000; padding:10px; border-radius:10px; margin-bottom:5px">
        <b>🤖 Assistant:</b> {msg}
        </div>
        """, unsafe_allow_html=True)

st.divider()

# Buttons
if st.button("🎙️ Start Speaking"):
    asyncio.run(handle_conversation())

if st.button("🗑️ Clear Chat"):
    st.session_state.history = []
    messages.clear()
    st.rerun()
