"""
Gradio interface for the Content Workflow Automation Agent.
"""
import os
import gradio as gr
import logging
from datetime import datetime

# Import workflow engine
from workflow_engine import WorkflowEngine
from config import ANTHROPIC_API_KEY, OPENAI_API_KEY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the workflow engine
workflow_engine = WorkflowEngine()

# Define state
state = {
    "project_title": "",
    "brainstorming_results": {},
    "selected_model": None,
    "outline": None,
    "slides": [],
    "current_step": "brainstorming",
    "style_template": None,
    "export_result": None,
    "export_path": None
}

def check_api_keys():
    """Check if API keys are set."""
    api_keys_set = bool(ANTHROPIC_API_KEY) and bool(OPENAI_API_KEY)
    return api_keys_set

def set_project_title(title):
    """Set the project title and create a new project."""
    if not title:
        return gr.Warning("Please enter a project title"), None
    
    state["project_title"] = title
    workflow_engine.create_new_project(title)
    return f"Project '{title}' created successfully!", get_step_info()

def run_brainstorming(topic, use_claude, use_claude_sonnet, use_gpt4, assumptions_text):
    """Run the brainstorming process using selected AI models."""
    if not topic:
        return gr.Warning("Please enter a topic"), None, None, state["current_step"], None
    
    if not (use_claude_sonnet or use_gpt4):
        return gr.Warning("Please select at least one AI model"), None, None, state["current_step"], None
    
    # Parse assumptions
    assumptions = [a.strip() for a in assumptions_text.split("\n") if a.strip()]
    
    # Create models list
    models = []
    if use_claude_sonnet:
        models.append("claude-3-7")
    if use_gpt4:
        models.append("gpt4")
    
    # Run brainstorming for each model
    results = {}
    errors = {}
    
    for model_id in models:
        try:
            logger.info(f"Starting brainstorming with {model_id} for topic: {topic}")
            result = workflow_engine.run_brainstorming(
                topic=topic,
                model_id=model_id,
                assumptions=assumptions,
                timeout=30  # Fixed timeout
            )
            
            logger.info(f"Brainstorming result from {model_id}: status={result.get('status')}")
            
            if result.get("status") == "success":
                response_text = result.get("result", "")
                if response_text:
                    logger.info(f"Got valid response from {model_id}, length: {len(response_text)}")
                    results[model_id] = response_text
                else:
                    errors[model_id] = "Received empty response"
            else:
                errors[model_id] = result.get("message", "Unknown error")
                
        except Exception as e:
            error_msg = f"Error with {model_id}: {str(e)}"
            errors[model_id] = error_msg
            logger.error(error_msg)
    
    # Store results and update state
    if results:
        # Store results in both local state and ensure they're in workflow engine
        state["brainstorming_results"] = results
        state["current_step"] = "outline"
        
        # Ensure the workflow engine has all the necessary data
        for model_id, content in results.items():
            # Double-check that the model's results are in the workflow engine
            if model_id not in workflow_engine.current_project.get("brainstorming", {}):
                logger.warning(f"Brainstorming results for {model_id} not found in workflow engine, adding them manually")
                # We can't fully recover without the topic, so we use a generic one
                workflow_engine.current_project["brainstorming"][model_id] = {
                    "topic": topic,
                    "assumptions": assumptions,
                    "result": content,
                    "timestamp": datetime.now().isoformat(),
                    "model": model_id
                }
        
        # Auto-select the first model if needed
        if not state["selected_model"] and len(results) > 0:
            state["selected_model"] = list(results.keys())[0]
            logger.info(f"Auto-selected model: {state['selected_model']}")
        
        # Format results for display
        result_html = ""
        for model_id, content in results.items():
            result_html += f"<h3>{model_id.capitalize()}</h3>"
            result_html += f"<div>{content}</div>"
            result_html += "<hr>"
        
        # Format errors if any
        error_text = ""
        if errors:
            error_text = "Some models had errors:\n"
            for model_id, message in errors.items():
                error_text += f"- {model_id}: {message}\n"
        
        # Get model choices for the dropdown
        model_choices = list(results.keys())
        
        # Update models dropdown for outline generation
        models_dropdown_choices = gr.update(choices=model_choices, value=state["selected_model"])
        
        # Update model dropdown for slide generation with the same values
        model_dropdown_choices = gr.update(choices=model_choices, value=state["selected_model"])
        
        return result_html, error_text, models_dropdown_choices, state["current_step"], model_dropdown_choices
    else:
        error_msg = "Failed to generate any brainstorming results. Please try again."
        if errors:
            error_msg += "\nErrors:\n"
            for model_id, message in errors.items():
                error_msg += f"- {model_id}: {message}\n"
        
        return None, error_msg, None, state["current_step"], None

def generate_outline(selected_model_id):
    """Generate an outline using the selected model's brainstorming results."""
    logger.info(f"Starting outline generation with model_id: {selected_model_id} (type: {type(selected_model_id)})")
    
    if not selected_model_id:
        return None, "Please select a model for outline generation", state["current_step"]
    
    # Handle if selected_model_id is a list (shouldn't happen, but just in case)
    if isinstance(selected_model_id, list):
        logger.warning(f"Received a list of models instead of a single model: {selected_model_id}")
        if selected_model_id:
            selected_model_id = selected_model_id[0]  # Take the first model in the list
            logger.info(f"Using first model from list: {selected_model_id}")
        else:
            return None, "Please select a model for outline generation", state["current_step"]
    
    logger.info(f"Generating outline using model: {selected_model_id}")
    logger.info(f"Current project brainstorming models: {list(workflow_engine.current_project.get('brainstorming', {}).keys())}")
    
    try:
        # Ensure the selected model's brainstorming results exist
        if selected_model_id not in workflow_engine.current_project.get("brainstorming", {}):
            logger.warning(f"Model {selected_model_id} not found in workflow engine brainstorming results")
            if selected_model_id in state.get("brainstorming_results", {}):
                # Try to recover by manually adding to workflow engine
                logger.warning(f"Adding missing brainstorming results for {selected_model_id} to workflow engine")
                # We can't fully recover without the topic, so we use a generic one
                workflow_engine.current_project["brainstorming"][selected_model_id] = {
                    "topic": "Generated Content",
                    "assumptions": [],
                    "result": state["brainstorming_results"][selected_model_id],
                    "timestamp": datetime.now().isoformat(),
                    "model": selected_model_id
                }
                logger.info(f"Added {selected_model_id} to workflow engine brainstorming results")
            else:
                logger.error(f"No brainstorming results found for model {selected_model_id} in state either")
                return None, f"No brainstorming results found for model {selected_model_id}", state["current_step"]
        
        # Call workflow engine to create outline
        logger.info(f"Calling workflow_engine.create_outline with selected_model_id={selected_model_id}")
        result = workflow_engine.create_outline(
            selected_model_id=selected_model_id
        )
        
        logger.info(f"Outline generation result: status={result.get('status')}")
        
        if result.get("status") == "success":
            outline = result.get("outline", "")
            logger.info(f"Got outline of length: {len(outline)}")
            state["outline"] = outline
            state["current_step"] = "slides"
            logger.info("Successfully generated outline")
            
            # Update the UI state for tabs
            return outline, "", "slides"  # Return current_step value directly
        else:
            error_msg = f"Error generating outline: {result.get('message')}"
            logger.error(error_msg)
            return None, error_msg, state["current_step"]
    except Exception as e:
        error_msg = f"Error generating outline: {str(e)}"
        logger.error(f"Exception in outline generation: {str(e)}", exc_info=True)  # Add full traceback
        return None, error_msg, state["current_step"]

def save_manual_outline(manual_outline):
    """Save a manually created outline."""
    if not manual_outline:
        return gr.Warning("Please enter an outline")
    
    try:
        # Call workflow engine to process the manual outline
        result = workflow_engine.create_outline(
            manual_outline=manual_outline
        )
        
        if result.get("status") == "success":
            state["outline"] = manual_outline
            state["current_step"] = "slides"
            return "Outline saved successfully!", "", state["current_step"]
        else:
            return gr.Warning(f"Error saving outline: {result.get('message')}"), "", state["current_step"]
    except Exception as e:
        return gr.Warning(f"Error saving outline: {str(e)}"), "", state["current_step"]

def generate_slides(style_template, use_ai=True, selected_model=None):
    """
    Generate slides from the outline with optional AI enhancement
    
    Args:
        style_template: The style template to use
        use_ai: Whether to use AI to enhance the slide content
        selected_model: The AI model to use for enhancement (if use_ai is True)
    """
    logging.info(f"Generating slides with template: {style_template}, use_ai: {use_ai}, model: {selected_model if use_ai else 'N/A'}")
    
    if not state.get("outline"):
        return None, "Please create an outline first", state["current_step"]
    
    # If no model is selected but AI is enabled, use the current selected model or default to claude-3-7
    if use_ai and not selected_model:
        selected_model = state.get("selected_model") or "claude-3-7"
        logging.info(f"No model specified, using {selected_model}")
        
    try:
        result = workflow_engine.generate_slide_deck(
            style_template=style_template,
            use_ai=use_ai,
            model_id=selected_model if use_ai else None
        )
        
        if result.get("status") == "success":
            slides = result.get("slides", [])
            state["slides"] = slides
            state["style_template"] = style_template
            state["current_step"] = "export"  # Set current step to export
            
            # Format slides for display
            slides_text = ""
            for i, slide in enumerate(slides):
                slides_text += f"### Slide {i+1}: {slide.get('title', 'Untitled')}\n\n"
                if slide.get("content"):
                    slides_text += f"{slide['content']}\n\n"
                
                if slide.get("points"):
                    for point in slide["points"]:
                        slides_text += f"- {point}\n"
                
                slides_text += "\n---\n\n"
            
            # Add a note about AI enhancement
            if use_ai:
                slides_text = f"*Slides enhanced using {selected_model}*\n\n" + slides_text
            
            return slides_text, None, "export"  # Return export as the current step
        else:
            return None, f"Error generating slides: {result.get('message')}", state["current_step"]
    
    except Exception as e:
        logging.exception(f"Error in generate_slides: {str(e)}")
        return None, f"Error generating slides: {str(e)}", state["current_step"]

def export_slides(export_format, style_template):
    """
    Export slides to the selected format
    """
    logging.info(f"Exporting slides with format: {export_format}, style: {style_template}")
    
    if not state.get("current_step") == "export":
        return {"status": "error", "message": "Please generate slides first"}, None
        
    # Create an exports directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Update style template in state if it has changed
        if style_template and style_template != state.get("style_template"):
            state["style_template"] = style_template
            # Regenerate slides with new template
            generate_slides(style_template)
        
        result = workflow_engine.export_slides(
            format=export_format,
            output_dir=output_dir
        )
        
        if result.get("status") == "success":
            state["export_result"] = result
            state["export_path"] = result.get("export_path")
            
            # Create a file path for Gradio to display
            file_path = result.get("export_path")
            
            # Generate a message with a link to open the file
            message = f"✅ Slides exported successfully to: {file_path}"
            if export_format in ["google_slides", "html"]:
                message += f"\n\nClick the button below to open in browser."
                
            return message, file_path
        else:
            error_msg = result.get("message", "Unknown error during export")
            logging.error(f"Export error: {error_msg}")
            return f"❌ Error exporting slides: {error_msg}", None
    
    except Exception as e:
        logging.exception(f"Error in export_slides: {str(e)}")
        return f"❌ Error: {str(e)}", None

def open_in_browser(file_path):
    """
    Open the exported file in the browser
    """
    if not file_path:
        return "No file to open"
    
    if os.path.exists(file_path):
        # Open the file in the default browser
        import webbrowser
        webbrowser.open(f"file:///{file_path}")
        return f"Opening {file_path} in browser"
    else:
        return f"File not found: {file_path}"

def get_step_info():
    """Get information about the current step."""
    if state["current_step"] == "brainstorming":
        return "Step 1: Brainstorming - Generate ideas for your content"
    elif state["current_step"] == "outline":
        return "Step 2: Outline - Structure your presentation"
    elif state["current_step"] == "slides":
        return "Step 3: Slides - Generate your slide deck"
    elif state["current_step"] == "export":
        return "Step 4: Export - Export your presentation"
    return "Content Workflow Automation Agent"

def get_brainstorming_models():
    """Get the list of models used in brainstorming for the outline step."""
    if state.get("brainstorming_results"):
        return list(state["brainstorming_results"].keys())
    return None

def on_selected_model_change(model_id):
    """Update the selected model."""
    state["selected_model"] = model_id
    return model_id

def update_model_dropdown(brainstorming_models):
    if brainstorming_models and len(brainstorming_models) > 0:
        logging.info(f"Updating model dropdown with choices: {brainstorming_models}")
        return gr.update(choices=brainstorming_models, value=state.get("selected_model") or brainstorming_models[0])
    else:
        logging.info("No brainstorming models available, using default choices")
        return gr.update(choices=["claude-3-7", "gpt4"], value=None)

# Create the Gradio interface
with gr.Blocks(theme=gr.themes.Soft(), title="Content Workflow Automation Agent") as app:
    gr.Markdown("# Content Workflow Automation Agent")
    gr.Markdown("This tool automates the process of creating presentation slide decks from initial ideas.")
    
    # Project setup
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Project Setup")
            api_status = gr.Checkbox(label="API Keys Set", value=check_api_keys(), interactive=False)
            project_title = gr.Textbox(label="Project Title", placeholder="Enter a title for your project")
            create_project_btn = gr.Button("Create Project")
            project_status = gr.Textbox(label="Status", interactive=False)
            current_step_info = gr.Textbox(label="Current Step", value=get_step_info(), interactive=False)
    
    # Tab interface for workflow steps
    with gr.Tabs() as tabs:
        # Brainstorming tab
        with gr.TabItem("1. Brainstorming"):
            with gr.Row():
                with gr.Column():
                    topic_input = gr.Textbox(
                        label="Topic or Question",
                        placeholder="Enter your topic or question here (e.g., 'How to create an effective AI product strategy')",
                        lines=2
                    )
                    
                    with gr.Row():
                        use_claude = gr.Checkbox(label="Use Claude", value=False)
                        use_claude_sonnet = gr.Checkbox(label="Use Claude 3.7", value=True)
                        use_gpt4 = gr.Checkbox(label="Use GPT-4", value=True)
                    
                    assumptions_input = gr.Textbox(
                        label="Assumptions (Optional, one per line)",
                        placeholder="Enter any assumptions, one per line",
                        lines=4
                    )
                    
                    brainstorm_btn = gr.Button("Start Brainstorming", variant="primary")
                    
                    brainstorm_error = gr.Textbox(label="Errors", visible=False)
            
            brainstorm_results = gr.HTML(label="Brainstorming Results")
        
        # Outline tab
        with gr.TabItem("2. Outline"):
            gr.Markdown("### Create Presentation Outline")
            
            with gr.Tabs() as outline_tabs:
                with gr.TabItem("AI-Generated Outline"):
                    with gr.Row():
                        with gr.Column():
                            model_dropdown = gr.Dropdown(
                                label="Select model for outline generation",
                                choices=["claude-3-7", "gpt4"],
                                interactive=True,
                                allow_custom_value=True,
                                multiselect=False  # Ensure only one model can be selected
                            )
                            
                            generate_outline_btn = gr.Button("Generate Outline", variant="primary")
                            outline_error = gr.Textbox(label="Errors", visible=False)
                    
                    ai_outline_output = gr.Textbox(
                        label="AI-Generated Outline",
                        lines=10,
                        interactive=False
                    )
                
                with gr.TabItem("Manual Outline"):
                    with gr.Row():
                        with gr.Column():
                            manual_outline_template = """# Introduction
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
-- Final thoughts or call to action"""
                            
                            manual_outline_input = gr.Textbox(
                                label="Create your own outline",
                                value=manual_outline_template,
                                lines=15
                            )
                            
                            save_outline_btn = gr.Button("Save Manual Outline", variant="primary")
                            manual_outline_status = gr.Textbox(label="Status", interactive=False)
                            manual_outline_error = gr.Textbox(label="Errors", visible=False)
        
        # Slides tab
        with gr.TabItem("3. Slides"):
            gr.Markdown("### Generate Slide Deck")
            
            with gr.Row():
                with gr.Column():
                    style_dropdown = gr.Dropdown(
                        label="Select style template",
                        choices=["default", "minimalist", "corporate", "creative", "academic"],
                        value="default",
                        interactive=True
                    )
                    
                    use_ai_checkbox = gr.Checkbox(label="Use AI to enhance slides", value=True)
                    
                    model_dropdown = gr.Dropdown(
                        label="Select AI model for slide enhancement",
                        choices=["claude-3-7", "gpt4"],
                        value=None,  # Set to None initially
                        interactive=True,
                        visible=True,
                        allow_custom_value=True  # Allow any value to prevent errors
                    )
                    
                    generate_slides_btn = gr.Button("Generate Slides", variant="primary")
                    slides_error = gr.Textbox(label="Errors", visible=False)
            
            slides_output = gr.Textbox(label="Generated Slides", lines=20, interactive=False)
        
        # Export tab
        with gr.TabItem("4. Export"):
            gr.Markdown("### Export Your Presentation")
            
            with gr.Row():
                with gr.Column(scale=2):
                    export_format = gr.Dropdown(
                        choices=["google_slides", "powerpoint", "html", "pdf"],
                        value="google_slides",
                        label="Export Format"
                    )
                    
                    style_template = gr.Dropdown(
                        choices=["default", "creative", "professional", "minimal"],
                        value="creative",
                        label="Style Template"
                    )
                    
                with gr.Column(scale=3):
                    export_btn = gr.Button("Export Slides", variant="primary")
                    export_status = gr.Textbox(label="Export Status", interactive=False)
                    export_file_path = gr.State(None)
                    open_browser_btn = gr.Button("Open in Browser", variant="secondary")
            
            # Connect components
            export_btn.click(
                fn=export_slides,
                inputs=[export_format, style_template],
                outputs=[export_status, export_file_path]
            )
            
            open_browser_btn.click(
                fn=open_in_browser,
                inputs=[export_file_path],
                outputs=[export_status]
            )
    
    # Set up event handlers
    create_project_btn.click(
        set_project_title,
        inputs=[project_title],
        outputs=[project_status, current_step_info]
    )
    
    brainstorm_btn.click(
        run_brainstorming,
        inputs=[topic_input, use_claude, use_claude_sonnet, use_gpt4, assumptions_input],
        outputs=[brainstorm_results, brainstorm_error, model_dropdown, current_step_info, model_dropdown]
    )
    
    model_dropdown.change(
        on_selected_model_change,
        inputs=[model_dropdown],
        outputs=[model_dropdown]
    )
    
    generate_outline_btn.click(
        generate_outline,
        inputs=[model_dropdown],
        outputs=[ai_outline_output, outline_error, current_step_info]
    )
    
    save_outline_btn.click(
        save_manual_outline,
        inputs=[manual_outline_input],
        outputs=[manual_outline_status, manual_outline_error, current_step_info]
    )
    
    generate_slides_btn.click(
        generate_slides,
        inputs=[style_dropdown, use_ai_checkbox, model_dropdown],
        outputs=[slides_output, slides_error, current_step_info]
    )
    
    use_ai_checkbox.change(
        fn=lambda use_ai: gr.update(visible=use_ai),
        inputs=[use_ai_checkbox],
        outputs=[model_dropdown]
    )
    
    # Update tabs based on the current step
    def update_ui_based_on_step(step):
        if step == "brainstorming":
            return gr.update(selected="1. Brainstorming")
        elif step == "outline":
            return gr.update(selected="2. Outline")
        elif step == "slides":
            return gr.update(selected="3. Slides")
        elif step == "export":
            return gr.update(selected="4. Export")
        return gr.update(selected="1. Brainstorming")
    
    # Define tab-switching behavior based on state changes
    for event_handler in [
        brainstorm_btn.click, 
        generate_outline_btn.click, 
        save_outline_btn.click, 
        generate_slides_btn.click
    ]:
        event_handler(
            lambda step=None: update_ui_based_on_step(state["current_step"]),
            outputs=[tabs]
        )

    # Add a specific tab update for the generate outline button
    generate_outline_btn.click(
        lambda: gr.update(selected="3. Slides"), 
        [], 
        [tabs]
    )

if __name__ == "__main__":
    # Launch the app
    app.launch(share=False)
