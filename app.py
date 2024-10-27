import streamlit as st
from datetime import date
import json

# app layout
st.set_page_config(
    layout="centered",
    page_title="Joyful Bytes",
    page_icon=":smile:",
    theme="light"
)

# App title
st.markdown("# Joyful Bytes")

# load in data
with open("./data/generated-map.json", "r") as f:
    data_dict = json.load(f)
    max_date = date.fromisoformat(max(data_dict.keys())) # convert to date object
    min_date = date.fromisoformat(min(data_dict.keys())) # convert to date object

# Create a date input widget with default value as today
selected_date = st.date_input(
    label="Select a date",
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

    # date
    st.markdown(f"## {story_date}")
    
    # Display the image
    st.image(image_path)
    st.markdown(f"### *[{story_name}]({story_url})*")
    
    # Display the story summary
    st.markdown(story_summary)

else:
    st.write("No data available for the selected date.")
