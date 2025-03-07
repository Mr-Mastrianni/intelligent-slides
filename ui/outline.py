"""
Outline UI component for the Content Workflow Automation Agent.
"""
import streamlit as st
import json
import logging

def render_outline():
    """Render the outline UI component."""
    st.header("2. Outline")
    
    # Add debugging to check session state variables
    logger = logging.getLogger(__name__)
    
    # Log the current state for debugging
    logger.info(f"Current step: {st.session_state.get('current_step')}")
    logger.info(f"Brainstorming results exist: {'brainstorming_results' in st.session_state}")
    if 'brainstorming_results' in st.session_state:
        logger.info(f"Brainstorming results keys: {list(st.session_state.brainstorming_results.keys())}")
    
    # Improved check for completed brainstorming
    brainstorming_complete = (
        ('brainstorming_results' in st.session_state and st.session_state.brainstorming_results) or
        ('current_step' in st.session_state and st.session_state.current_step in ['outline', 'slides', 'export'])
    )
    
    if not brainstorming_complete:
        st.info("Please complete the brainstorming step first.")
        logger.warning("Brainstorming not complete, showing info message")
        return
    
    st.subheader("Create Presentation Outline")
    st.markdown("""
    The outline will structure your presentation into slides with clear titles and key points.
    You can either use AI to generate an outline from your brainstorming or create your own.
    """)
    
    # Model selection for outline generation
    if "selected_model" not in st.session_state and "brainstorming_results" in st.session_state:
        # Default to the first model used in brainstorming
        st.session_state.selected_model = list(st.session_state.brainstorming_results.keys())[0]
    
    selected_model = st.selectbox(
        "Select model for outline generation",
        options=list(st.session_state.brainstorming_results.keys()),
        index=list(st.session_state.brainstorming_results.keys()).index(st.session_state.selected_model)
            if "selected_model" in st.session_state else 0,
        format_func=lambda x: x.capitalize()
    )
    
    # Update selected model in session state
    st.session_state.selected_model = selected_model
    
    # Tabs for AI-generated vs. manual outline
    outline_tab, manual_tab = st.tabs(["AI-Generated Outline", "Manual Outline"])
    
    with outline_tab:
        if st.button("Generate Outline"):
            with st.spinner("Generating outline..."):
                try:
                    # Call workflow engine to create outline
                    result = st.session_state.workflow_engine.create_outline(
                        selected_model_id=selected_model
                    )
                    
                    if result.get("status") == "success":
                        st.session_state.outline = result.get("outline", "")
                        st.session_state.outline_source = "ai"
                        st.session_state.current_step = "slides"
                        st.success("Outline generated successfully!")
                    else:
                        st.error(f"Error generating outline: {result.get('message')}")
                except Exception as e:
                    st.error(f"Error generating outline: {str(e)}")
    
    with manual_tab:
        # Template to help users structure their manual outline
        template = """
# Introduction
-- Explain the topic
-- Outline key assumptions

# Main Point 1
-- Detail first key idea
-- Supporting evidence or examples

# Main Point 2
-- Detail second key idea
-- Supporting evidence or examples

# Main Point 3
-- Detail third key idea
-- Supporting evidence or examples

# Conclusion
-- Summarize key points
-- Final thoughts or call to action
"""
        
        manual_outline = st.text_area(
            "Create your own outline",
            value=template if "manual_outline" not in st.session_state else st.session_state.manual_outline,
            height=400,
            help="Create your outline using markdown. Use # for slide titles and - for bullet points."
        )
        
        st.session_state.manual_outline = manual_outline
        
        if st.button("Save Manual Outline"):
            try:
                # Call workflow engine to create outline from manual input
                result = st.session_state.workflow_engine.create_outline(
                    manual_outline=manual_outline
                )
                
                if result.get("status") == "success":
                    st.session_state.outline = manual_outline
                    st.session_state.outline_source = "manual"
                    st.session_state.current_step = "slides"
                    st.success("Manual outline saved successfully!")
                else:
                    st.error(f"Error saving outline: {result.get('message')}")
            except Exception as e:
                st.error(f"Error saving outline: {str(e)}")
    
    # Display outline if available
    if "outline" in st.session_state and st.session_state.outline:
        st.subheader("Current Outline")
        
        # Display the outline
        st.markdown(st.session_state.outline)
        
        # Edit outline button
        if st.button("Edit Outline"):
            # Move back to manual tab with current outline
            st.session_state.manual_outline = st.session_state.outline
            st.rerun()
        
        # Continue to slides button
        st.button(
            "Continue to Slides", 
            on_click=lambda: setattr(st.session_state, "current_step", "slides")
        )
