"""
Main application file for the Content Workflow Automation Agent.
"""
import streamlit as st
import os
import logging
from datetime import datetime

# Import UI components
from ui.sidebar import render_sidebar
from ui.brainstorming import render_brainstorming
from ui.outline import render_outline
from ui.slides import render_slides
from ui.export import render_export

# Import workflow engine
from workflow_engine import WorkflowEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize session state
def init_session_state():
    """Initialize the session state variables."""
    if "workflow_engine" not in st.session_state:
        st.session_state.workflow_engine = WorkflowEngine()
    
    if "current_step" not in st.session_state:
        st.session_state.current_step = "brainstorming"
    
    if "project_title" not in st.session_state:
        st.session_state.project_title = ""
    
    if "api_keys_set" not in st.session_state:
        st.session_state.api_keys_set = False

def main():
    """Main application function."""
    st.set_page_config(
        page_title="Content Workflow Automation",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    init_session_state()
    
    # Title and description
    st.title("Content Workflow Automation Agent")
    st.markdown(
        """
        This tool automates the process of creating presentation slide decks from initial ideas,
        following the workflow described in the transcript. It guides you through brainstorming,
        outline creation, slide generation, formatting, and export.
        """
    )
    
    # Render sidebar
    render_sidebar()
    
    # Check if API keys are set
    if not st.session_state.api_keys_set:
        st.warning("⚠️ Please set your API keys in the sidebar to continue.")
        return
    
    # Main workflow tabs
    tabs = st.tabs([
        "1️⃣ Brainstorming", 
        "2️⃣ Outline", 
        "3️⃣ Slides", 
        "4️⃣ Export"
    ])
    
    # Render each step in its corresponding tab
    with tabs[0]:
        render_brainstorming()
    
    with tabs[1]:
        render_outline()
    
    with tabs[2]:
        render_slides()
    
    with tabs[3]:
        render_export()
    
    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ by Content Workflow Automation Agent")

if __name__ == "__main__":
    main()
