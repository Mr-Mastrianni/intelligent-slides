"""
Brainstorming UI component for the Content Workflow Automation Agent.
"""
import streamlit as st
import json
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def render_brainstorming():
    """Render the brainstorming UI component."""
    st.header("1. Brainstorming")
    
    # Check if we have API keys set
    if not st.session_state.api_keys_set:
        st.warning("Please set your API keys in the sidebar first.")
        return
    
    # Check if we have a project title
    if not st.session_state.get("project_title"):
        st.warning("Please set a project title in the sidebar first.")
        return
    
    # Initialize error and loading states
    if "brainstorming_error" not in st.session_state:
        st.session_state.brainstorming_error = None
    
    if "brainstorming_in_progress" not in st.session_state:
        st.session_state.brainstorming_in_progress = False
        
    # Display any existing errors
    if st.session_state.brainstorming_error:
        st.error(st.session_state.brainstorming_error)
        if st.button("Clear Error"):
            st.session_state.brainstorming_error = None
            st.rerun()
    
    # Topic input
    topic = st.text_area(
        "Topic or Question",
        value="",
        placeholder="Enter your topic or question here (e.g., 'How to create an effective AI product strategy')",
        help="Be specific but open-ended. This is the core idea to explore."
    )
    
    # Assumptions input
    with st.expander("Add Assumptions (Optional)", expanded=False):
        # Initialize assumptions in session state
        if "custom_assumptions" not in st.session_state:
            st.session_state.custom_assumptions = ["", ""]
        
        updated_assumptions = []
        for i, assumption in enumerate(st.session_state.custom_assumptions):
            assumption_text = st.text_input(
                f"Assumption {i+1}",
                value=assumption,
                key=f"custom_assumption_{i}"
            )
            if assumption_text.strip():  # Only add non-empty assumptions
                updated_assumptions.append(assumption_text)
        
        # Add/remove assumption buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add Assumption"):
                updated_assumptions.append("")
        with col2:
            if st.button("Remove Assumption") and len(updated_assumptions) > 0:
                updated_assumptions.pop()
        
        st.session_state.custom_assumptions = updated_assumptions
    
    # AI model selection
    st.subheader("Select AI Models")
    st.markdown("Choose which AI models to use for brainstorming. You can compare results side by side.")
    
    col1, col2 = st.columns(2)
    with col1:
        use_claude = st.checkbox("Claude", value=True, help="Anthropic's Claude model")
    with col2:
        use_gpt4 = st.checkbox("GPT-4", value=True, help="OpenAI's GPT-4 model")
    
    # Show the brainstorming button
    if not st.session_state.brainstorming_in_progress:
        if st.button("Start Brainstorming", disabled=not (topic and (use_claude or use_gpt4))):
            # Reset any previous results
            if "brainstorming_results" in st.session_state:
                del st.session_state.brainstorming_results
            
            # Set the loading state
            st.session_state.brainstorming_in_progress = True
            
            # Get assumptions
            all_assumptions = [a for a in st.session_state.custom_assumptions if a.strip()]
            
            # Create models list
            models = []
            if use_claude:
                models.append("claude")
            if use_gpt4:
                models.append("gpt4")
            
            try:
                # Run brainstorming directly
                results = {}
                errors_by_model = {}
                
                for model_id in models:
                    try:
                        logger.info(f"Starting brainstorming with {model_id} for topic: {topic}")
                        result = st.session_state.workflow_engine.run_brainstorming(
                            topic=topic,
                            model_id=model_id,
                            assumptions=all_assumptions,
                            timeout=30  # Fixed timeout
                        )
                        
                        logger.info(f"Brainstorming result from {model_id}: status={result.get('status')}")
                        
                        if result.get("status") == "success":
                            response_text = result.get("result", "")
                            if response_text:
                                logger.info(f"Got valid response from {model_id}, length: {len(response_text)}")
                                results[model_id] = response_text
                                logger.info(f"Successfully added result from {model_id} to results dictionary")
                            else:
                                error_msg = f"Received empty response from {model_id}"
                                logger.error(error_msg)
                                errors_by_model[model_id] = error_msg
                        else:
                            # Store error message for this model
                            error_msg = result.get("message", f"Unknown error with {model_id}")
                            logger.error(error_msg)
                            errors_by_model[model_id] = error_msg
                    except Exception as e:
                        error_msg = f"Error with {model_id}: {str(e)}"
                        errors_by_model[model_id] = error_msg
                        logger.error(error_msg)
                
                # Store results - use more explicit logging
                if results:
                    model_keys = list(results.keys())
                    logger.info(f"Storing brainstorming results with models: {model_keys}")
                    
                    # Double check the results dictionary has data
                    for model_name, content in results.items():
                        if not content or len(content) < 10:  # Sanity check for content
                            logger.warning(f"Model {model_name} has suspicious content: '{content}'")
                    
                    # Store the results and update the UI state
                    st.session_state.brainstorming_results = results.copy()  # Make a copy to avoid reference issues
                    st.session_state.current_step = "outline"
                    logger.info(f"Current step set to outline, results stored for {len(results)} models")
                    
                    # Store any errors for display
                    if errors_by_model:
                        error_models = list(errors_by_model.keys())
                        error_msg = f"Some models failed: {', '.join(error_models)}"
                        st.session_state.partial_brainstorming_error = error_msg
                        logger.warning(error_msg)
                else:
                    error_msgs = [f"{model}: {error}" for model, error in errors_by_model.items()]
                    error_msg = "Failed to generate brainstorming results. Please try again. Errors:\n" + "\n".join(error_msgs)
                    st.session_state.brainstorming_error = error_msg
                    logger.error(error_msg)
            except Exception as e:
                # Catch any other exceptions
                error_msg = f"An unexpected error occurred: {str(e)}"
                st.session_state.brainstorming_error = error_msg
                logger.error(error_msg)
            finally:
                # Always clear loading state, even if exceptions occur
                logger.info("Clearing brainstorming_in_progress state")
                st.session_state.brainstorming_in_progress = False
                
                # Force refresh
                st.rerun()
    
    # Show progress indicator
    if st.session_state.brainstorming_in_progress:
        st.info("Brainstorming in progress... Please wait.")
        st.progress(0)
            
    # Display results if available
    if "brainstorming_results" in st.session_state and st.session_state.brainstorming_results:
        st.subheader("Brainstorming Results")
        logger.info(f"Displaying brainstorming results with {len(st.session_state.brainstorming_results)} models")
        
        # Show partial errors if any
        if "partial_brainstorming_error" in st.session_state:
            st.warning(st.session_state.partial_brainstorming_error)
        
        # If we have multiple models, display them side by side
        results = st.session_state.brainstorming_results
        
        if len(results) > 1:
            cols = st.columns(len(results))
            for i, (model_id, result_text) in enumerate(results.items()):
                with cols[i]:
                    st.markdown(f"### {model_id.capitalize()}")
                    st.markdown(result_text)
                    
                    # Select model button
                    if st.button(f"Select {model_id.capitalize()}", key=f"select_{model_id}"):
                        st.session_state.selected_model = model_id
                        st.success(f"Selected {model_id.capitalize()} for outline creation")
                        st.rerun()
        else:
            # Single model display
            model_id = list(results.keys())[0]
            st.markdown(f"### {model_id.capitalize()}")
            st.markdown(results[model_id])
            
            # Set as selected model
            st.session_state.selected_model = model_id
            logger.info(f"Auto-selected model: {model_id}")
        
        # "Continue to Outline" button
        if st.button("Continue to Outline"):
            st.session_state.current_step = "outline"
            st.session_state.brainstorming_completed = True
            # Display success message and instructions
            st.success("✅ Brainstorming completed! Click the **Outline tab** above to continue.")
