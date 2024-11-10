import streamlit as st
from datetime import date
import json
import random

# app layout
st.set_page_config(
    layout="centered",
    page_title="Joyful Bytes",
    page_icon=":smile:"
)

# Custom CSS to inject
st.markdown("""
    <style>
    /* Add some playful styling */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
    }
    .main-title {
        background: linear-gradient(120deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em !important;
        margin-bottom: 1em;
    }
    </style>
""", unsafe_allow_html=True)

# App title with more flair
st.markdown("<h1 class='main-title'>✨ Joyful Bytes ✨</h1>", unsafe_allow_html=True)

# Add an inspiring quote
quotes = [
    "Every pixel of positivity counts! 🎨",
    "Your daily dose of digital delight! 🌟",
    "Where AI meets optimism! 💫",
    "Making the world brighter, one byte at a time! 🌈"
]
st.markdown(f"*{random.choice(quotes)}*")

# load in data
with open("./data/generated-map.json", "r") as f:
    data_dict = json.load(f)
    max_date = date.fromisoformat(max(data_dict.keys())) # convert to date object
    min_date = date.fromisoformat(min(data_dict.keys())) # convert to date object

# Create a date input widget with default value as today
selected_date = st.date_input(
    label="📅 Pick a day to explore!",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

# divider
st.divider()

# Convert selected_date to string in YYYY-MM-DD format
selected_date_str = selected_date.strftime("%Y-%m-%d")

# Check if selected date is in data_dict
if selected_date_str in data_dict:
    entry = data_dict[selected_date_str]
    image_path = entry["image_path"]
    story_summary = entry["story_summary"]
    story_url = entry["story_url"]
    story_date = entry["date"]
    story_name = entry["name"]

    # Add a container for better organization
    with st.container():
        # Date with icon
        st.markdown(f"## 📆 {story_date}")
        
        with st.container():
            st.markdown('<div class="hover-zoom">', unsafe_allow_html=True)
            st.image(image_path)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Make the story title more prominent
        st.markdown(f"### 📰 *[{story_name}]({story_url})*")
        
        st.markdown(story_summary)

else:
    st.error("🔍 No bytes found for this date - try another day!")

# Add a footer
st.divider()
