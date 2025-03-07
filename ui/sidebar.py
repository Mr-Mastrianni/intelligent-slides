"""
Sidebar UI component for the Content Workflow Automation Agent.
"""
import streamlit as st
import os
from datetime import datetime

def render_sidebar():
    """Render the sidebar with settings and project management options."""
    with st.sidebar:
        st.header("Settings & Tools")
        
        # API Keys section
        with st.expander("🔑 API Keys", expanded=not st.session_state.api_keys_set):
            # OpenAI API Key
            openai_key = st.text_input(
                "OpenAI API Key", 
                type="password",
                value=os.environ.get("OPENAI_API_KEY", ""),
                help="Required for GPT-4 and DALL-E image generation"
            )
            
            # Anthropic API Key
            anthropic_key = st.text_input(
                "Anthropic API Key", 
                type="password",
                value=os.environ.get("ANTHROPIC_API_KEY", ""),
                help="Required for Claude integration"
            )
            
            # Google API Key (optional)
            google_key = st.text_input(
                "Google API Key (Optional)",
                type="password",
                value=os.environ.get("GOOGLE_API_KEY", ""),
                help="Optional: Required only for Google Slides export"
            )
            
            # Save API keys button
            if st.button("Save API Keys"):
                # Update environment variables
                os.environ["OPENAI_API_KEY"] = openai_key
                os.environ["ANTHROPIC_API_KEY"] = anthropic_key
                if google_key:
                    os.environ["GOOGLE_API_KEY"] = google_key
                
                # Update session state
                if openai_key and anthropic_key:
                    st.session_state.api_keys_set = True
                    st.success("API keys saved successfully!")
                else:
                    st.error("OpenAI and Anthropic API keys are required.")
        
        # Project management section
        st.subheader("Project")
        
        # Project title input
        new_project_title = st.text_input(
            "Project Title",
            value=st.session_state.get("project_title", ""),
            help="Enter a title for your project"
        )
        
        # Update project title if changed
        if new_project_title != st.session_state.get("project_title", ""):
            st.session_state.project_title = new_project_title
        
        # Create new project button
        if st.button("Create New Project"):
            if st.session_state.project_title:
                # Create new project in workflow engine
                if "workflow_engine" in st.session_state:
                    st.session_state.workflow_engine.create_new_project(st.session_state.project_title)
                    st.success(f"Created new project: {st.session_state.project_title}")
                    
                    # Reset to first step
                    st.session_state.current_step = "brainstorming"
                    
                    # Force rerun to update UI
                    st.rerun()
            else:
                st.error("Please enter a project title first.")
        
        # Load/Save Project section (if a project exists)
        if "workflow_engine" in st.session_state and st.session_state.workflow_engine.current_project:
            with st.expander("💾 Save/Load Project"):
                # Save project
                save_path = st.text_input(
                    "Save Path",
                    value=f"./projects/{st.session_state.project_title.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.json",
                    help="Path to save the project file"
                )
                
                if st.button("Save Project"):
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    
                    # Save project
                    result = st.session_state.workflow_engine.save_project(save_path)
                    if result.get("status") == "success":
                        st.success(f"Project saved to {result.get('filepath')}")
                    else:
                        st.error(f"Error saving project: {result.get('message')}")
                
                # Load project
                st.file_uploader(
                    "Load Project",
                    type="json",
                    help="Upload a previously saved project file",
                    on_change=lambda file: load_project(file) if file else None
                )
        
        # Workflow steps indicator
        st.subheader("Workflow Progress")
        steps = ["brainstorming", "outline", "slides", "export"]
        current_step_idx = steps.index(st.session_state.current_step) if st.session_state.current_step in steps else 0
        
        for i, step in enumerate(steps):
            if i < current_step_idx:
                st.success(f"✅ {step.capitalize()}")
            elif i == current_step_idx:
                st.info(f"🔄 {step.capitalize()}")
            else:
                st.text(f"⏸️ {step.capitalize()}")
        
        # Help/About section
        with st.expander("ℹ️ About"):
            st.markdown("""
            This tool automates the content creation workflow for presentations:
            
            1. **Brainstorming**: Generate and compare ideas using multiple AI models
            2. **Outline**: Create a structured outline for your content
            3. **Slides**: Generate and format slide content
            4. **Export**: Export to PowerPoint or Google Slides
            
            For more information, check the [README](https://github.com/yourusername/content-workflow-agent).
            """)

def load_project(file):
    """Load a project from an uploaded file."""
    if file is None:
        return
    
    # Create a temporary file
    temp_path = f"./temp_project_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        # Write uploaded file to disk
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        
        # Load project
        result = st.session_state.workflow_engine.load_project(temp_path)
        
        if result.get("status") == "success":
            st.session_state.project_title = result.get("project", {}).get("title", "Loaded Project")
            st.success(f"Project '{st.session_state.project_title}' loaded successfully!")
            
            # Set current step based on project status
            project_status = result.get("project", {}).get("status", "")
            if "outline" in project_status:
                st.session_state.current_step = "outline"
            elif "slides" in project_status:
                st.session_state.current_step = "slides"
            elif "export" in project_status:
                st.session_state.current_step = "export"
            else:
                st.session_state.current_step = "brainstorming"
                
            # Force rerun to update UI
            st.rerun()
        else:
            st.error(f"Error loading project: {result.get('message')}")
    
    except Exception as e:
        st.error(f"Error loading project: {str(e)}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
