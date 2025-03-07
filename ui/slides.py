"""
Slides UI component for the Content Workflow Automation Agent.
"""
import streamlit as st
import pandas as pd
from datetime import datetime

def render_slides():
    """Render the slides UI component."""
    st.header("3. Slides")
    
    # Check if we have completed the outline step
    if "outline" not in st.session_state or not st.session_state.outline:
        st.info("Please complete the outline step first.")
        return
    
    st.subheader("Generate and Format Slides")
    st.markdown("""
    This step will convert your outline into fully formatted slides.
    You can customize the style and formatting options before generating.
    """)
    
    # Style template selection
    style_template = st.selectbox(
        "Select style template",
        options=["default", "dark"],
        index=0,
        format_func=lambda x: x.capitalize()
    )
    
    # Formatting options
    with st.expander("Formatting Options", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            bold_key_terms = st.checkbox(
                "Bold key terms", 
                value=True,
                help="Automatically highlight key terms in bold"
            )
        
        with col2:
            highlight_color = st.color_picker(
                "Highlight color",
                value="#3366FF",
                help="Color for highlighting important points"
            )
    
    # Generate slides button
    if st.button("Generate Slides"):
        with st.spinner("Generating slides..."):
            try:
                # Call workflow engine to generate slides
                result = st.session_state.workflow_engine.generate_slide_deck(
                    style_template=style_template
                )
                
                if result.get("status") == "success":
                    st.session_state.slides = result.get("slides", [])
                    
                    # Format slides immediately
                    format_result = st.session_state.workflow_engine.format_slide_deck(
                        bold_key_terms=bold_key_terms,
                        highlight_color=highlight_color
                    )
                    
                    if format_result.get("status") == "success":
                        st.session_state.formatted_slides = format_result.get("slides", [])
                        st.session_state.current_step = "export"
                        st.success("Slides generated and formatted successfully!")
                    else:
                        st.error(f"Error formatting slides: {format_result.get('message')}")
                else:
                    st.error(f"Error generating slides: {result.get('message')}")
            except Exception as e:
                st.error(f"Error generating slides: {str(e)}")
    
    # Display slides if available
    if "formatted_slides" in st.session_state and st.session_state.formatted_slides:
        st.subheader("Preview Slides")
        
        # Number of slides
        st.info(f"Generated {len(st.session_state.formatted_slides)} slides")
        
        # Display slides in an expandable area
        for i, slide in enumerate(st.session_state.formatted_slides):
            with st.expander(f"Slide {i+1}: {slide.get('title', 'Untitled Slide')}"):
                # Title
                st.markdown(f"# {slide.get('title', 'Untitled Slide')}")
                
                # Content
                if "content" in slide and slide["content"]:
                    st.markdown(slide["content"])
                
                # Points
                if "points" in slide and slide["points"]:
                    for point in slide["points"]:
                        st.markdown(f"- {point}")
        
        # Create editable view of slides
        with st.expander("Edit Slides", expanded=False):
            st.markdown("Edit your slides in a tabular format:")
            
            # Create a dataframe for editing
            slides_data = []
            for i, slide in enumerate(st.session_state.formatted_slides):
                slides_data.append({
                    "Slide": i+1,
                    "Title": slide.get("title", ""),
                    "Content": slide.get("content", ""),
                    "Points": "\n".join(slide.get("points", []))
                })
            
            # Convert to dataframe
            slides_df = pd.DataFrame(slides_data)
            
            # Display as editable dataframe
            edited_df = st.data_editor(
                slides_df,
                use_container_width=True,
                num_rows="fixed",
                hide_index=True,
                column_config={
                    "Slide": st.column_config.NumberColumn(
                        "Slide",
                        help="Slide number",
                        width="small",
                        disabled=True
                    ),
                    "Title": st.column_config.TextColumn(
                        "Title",
                        help="Slide title",
                        width="medium"
                    ),
                    "Content": st.column_config.TextColumn(
                        "Content",
                        help="Main slide content",
                        width="large"
                    ),
                    "Points": st.column_config.TextAreaColumn(
                        "Points",
                        help="Bullet points (one per line)",
                        width="large"
                    )
                }
            )
            
            # Save edits button
            if st.button("Save Slide Edits"):
                try:
                    # Update slides with edited content
                    updated_slides = []
                    for i, row in edited_df.iterrows():
                        slide = st.session_state.formatted_slides[i].copy()
                        slide["title"] = row["Title"]
                        slide["content"] = row["Content"]
                        slide["points"] = row["Points"].split("\n") if row["Points"] else []
                        updated_slides.append(slide)
                    
                    # Update session state
                    st.session_state.formatted_slides = updated_slides
                    
                    # Update workflow engine
                    st.session_state.workflow_engine.current_project["slides"] = updated_slides
                    st.session_state.workflow_engine.current_project["updated_at"] = datetime.now().isoformat()
                    
                    st.success("Slide edits saved successfully!")
                except Exception as e:
                    st.error(f"Error saving slide edits: {str(e)}")
        
        # Continue to export button
        st.button(
            "Continue to Export", 
            on_click=lambda: setattr(st.session_state, "current_step", "export")
        )
