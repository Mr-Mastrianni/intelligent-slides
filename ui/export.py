"""
Export UI component for the Content Workflow Automation Agent.
"""
import streamlit as st
import os
from datetime import datetime
from PIL import Image
import io
import base64

def render_export():
    """Render the export UI component."""
    st.header("4. Export")
    
    # Check if we have completed the slides step
    if "formatted_slides" not in st.session_state or not st.session_state.formatted_slides:
        st.info("Please complete the slides step first.")
        return
    
    st.subheader("Export Presentation and Generate Thumbnail")
    st.markdown("""
    This step exports your formatted slides to PowerPoint or Google Slides,
    and optionally generates a thumbnail image for your presentation.
    """)
    
    # Export options
    st.markdown("### Export Options")
    
    export_format = st.radio(
        "Export Format",
        options=["PowerPoint", "Google Slides"],
        index=0,
        help="Select the format to export your presentation"
    )
    
    export_format_key = "powerpoint" if export_format == "PowerPoint" else "google_slides"
    
    # Export button
    if st.button("Export Presentation"):
        with st.spinner(f"Exporting to {export_format}..."):
            try:
                # Call workflow engine to export slides
                result = st.session_state.workflow_engine.export_slides(
                    format=export_format_key
                )
                
                if result.get("status") == "success":
                    export_info = result.get("export", {})
                    
                    if "filepath" in export_info:
                        st.session_state.export_filepath = export_info["filepath"]
                        st.session_state.export_filename = export_info["filename"]
                        st.success(f"Presentation exported successfully as {export_info['filename']}!")
                        
                        # For PowerPoint, provide download link
                        if export_format == "PowerPoint" and os.path.exists(export_info["filepath"]):
                            with open(export_info["filepath"], "rb") as file:
                                file_bytes = file.read()
                                b64 = base64.b64encode(file_bytes).decode()
                                href = f'<a href="data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64,{b64}" download="{export_info["filename"]}">Download {export_info["filename"]}</a>'
                                st.markdown(href, unsafe_allow_html=True)
                    else:
                        st.warning("Export functionality not fully implemented for this format. In a production environment, this would create and share the presentation.")
                else:
                    st.error(f"Error exporting presentation: {result.get('message')}")
            except Exception as e:
                st.error(f"Error exporting presentation: {str(e)}")
    
    # Thumbnail generation
    st.markdown("### Thumbnail Generation")
    st.markdown("""
    Generate a professional thumbnail image for your presentation.
    This can be used for video thumbnails, social media, or as a presentation cover.
    """)
    
    # Custom prompt option
    custom_prompt = st.text_area(
        "Custom Image Prompt (Optional)",
        placeholder="Enter a detailed description for your thumbnail image, or leave blank to generate automatically",
        help="Describe what you want your thumbnail to look like. Be specific about style, elements, and mood."
    )
    
    # Generate thumbnail button
    if st.button("Generate Thumbnail"):
        with st.spinner("Generating thumbnail image..."):
            try:
                # Check if OpenAI API key is available
                if not os.environ.get("OPENAI_API_KEY"):
                    st.error("OpenAI API key is required for thumbnail generation. Please set it in the sidebar.")
                    return
                
                # Call workflow engine to generate thumbnail
                result = st.session_state.workflow_engine.generate_thumbnail(
                    prompt=custom_prompt if custom_prompt else None
                )
                
                if result.get("status") == "success":
                    thumbnail_info = result.get("thumbnail", {})
                    
                    if "url" in thumbnail_info:
                        st.session_state.thumbnail_url = thumbnail_info["url"]
                        st.session_state.thumbnail_prompt = thumbnail_info.get("revised_prompt", custom_prompt)
                        st.success("Thumbnail generated successfully!")
                    else:
                        st.error("Error generating thumbnail: No image URL returned.")
                else:
                    st.error(f"Error generating thumbnail: {result.get('message')}")
            except Exception as e:
                st.error(f"Error generating thumbnail: {str(e)}")
    
    # Display thumbnail if available
    if "thumbnail_url" in st.session_state and st.session_state.thumbnail_url:
        st.subheader("Thumbnail Preview")
        
        try:
            # Display the image
            st.image(
                st.session_state.thumbnail_url,
                caption="Generated Thumbnail",
                use_column_width=True
            )
            
            # Show the prompt used
            if "thumbnail_prompt" in st.session_state:
                with st.expander("Prompt Used"):
                    st.markdown(st.session_state.thumbnail_prompt)
            
            # Download button for the image
            st.markdown("Right-click the image and select 'Save image as...' to download the thumbnail.")
            
        except Exception as e:
            st.error(f"Error displaying thumbnail: {str(e)}")
    
    # Final steps and resources
    st.markdown("### Next Steps")
    st.markdown("""
    Now that you've exported your presentation, you can:
    
    1. **Record your presentation** - Use the slide deck to record your video
    2. **Edit as needed** - Make any final adjustments to your slides or thumbnail
    3. **Save your project** - Use the save option in the sidebar to save your work
    
    Remember to download your files before closing this application.
    """)
