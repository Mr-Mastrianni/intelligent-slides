"""
Simple test script to verify Streamlit is working correctly.
"""
import streamlit as st

st.title("Streamlit Test")
st.write("If you can see this, Streamlit is working correctly!")

# Display some interactive elements
st.button("Test Button")
st.slider("Test Slider", 0, 100, 50)
