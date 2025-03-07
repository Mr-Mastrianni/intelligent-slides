"""
Workflow Engine module for the Content Workflow Automation Agent.
Orchestrates the entire workflow from idea to final slide deck.
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

from ai_interface import AIInterface
from slide_deck_generator import SlideDeckGenerator
from image_generator import ImageGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """Orchestrates the entire content creation workflow."""
    
    def __init__(self):
        """Initialize the workflow engine."""
        self.ai = AIInterface()
        self.slide_generator = SlideDeckGenerator()
        self.image_generator = ImageGenerator()
        self.current_project = None
        
        # Default timeouts
        self.default_timeout = 90  # 90 seconds for workflow operations
    
    def create_new_project(self, title: str) -> Dict[str, Any]:
        """Create a new content project."""
        project_id = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_project = {
            "id": project_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "initialized",
            "brainstorming": {},
            "outline": {},
            "slides": [],
            "formatting": {},
            "images": {},
        }
        
        logger.info(f"Created new project: {title} (ID: {project_id})")
        return self.current_project
    
    def run_brainstorming(self, 
                        topic: str, 
                        model_id: str = "claude", 
                        assumptions: Optional[List[str]] = None,
                        timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the brainstorming phase using AI.
        
        Args:
            topic: The main topic/idea to brainstorm
            model_id: The AI model to use (default: claude)
            assumptions: Optional list of economic or other assumptions
            timeout: Optional timeout in seconds
            
        Returns:
            Dict with brainstorming results
        """
        if not topic:
            return {"status": "error", "message": "Topic is required"}
        
        logger.info(f"Starting brainstorming for topic: {topic}")
        
        # Simplified prompt for faster responses
        prompt = f"Topic: {topic}\n\n"
        
        # Add assumptions if provided (simplified)
        if assumptions and len(assumptions) > 0:
            prompt += "Assumptions:\n"
            for assumption in assumptions:
                prompt += f"- {assumption}\n"
        
        prompt += "\nProvide a brief, focused brainstorming on this topic."

        # Get AI completion with reduced timeout
        if timeout is None:
            # Use even shorter timeouts for brainstorming
            timeout = 25 if model_id == "claude" else 30
            
        # Simplified system prompt
        system_prompt = "You are a concise thought partner for brainstorming. Keep responses focused and brief."
        
        try:
            response = self.ai.get_completion(
                model_id=model_id,
                prompt=prompt,
                system_prompt=system_prompt,
                with_thinking=False,  # Disable thinking mode for speed
                timeout=timeout,
                max_tokens=800  # Limit tokens for faster responses
            )
            
            # Check for errors
            if response.get("status") == "error":
                logger.error(f"Brainstorming error: {response.get('message')}")
                return {
                    "status": "error",
                    "message": f"Failed to generate brainstorming: {response.get('message')}"
                }
            
            # Log the response details to help with debugging
            logger.info(f"AI response received for {model_id}. Status: {response.get('status')}")
            
            # Extract the actual response text
            response_text = response.get("response", "")
            if not response_text:
                logger.error(f"Empty response text from {model_id}")
                return {
                    "status": "error",
                    "message": f"Received empty response from {model_id}"
                }
                
            logger.info(f"Response has content length: {len(response_text)}")
            # Show a preview of the response for debugging
            preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
            logger.info(f"Response preview: {preview}")
            
            # Store the response in the current project
            if self.current_project:
                self.current_project["brainstorming"][model_id] = {
                    "topic": topic,
                    "assumptions": assumptions or [],
                    "result": response_text,
                    "timestamp": datetime.now().isoformat(),
                    "model": model_id
                }
                self.current_project["updated_at"] = datetime.now().isoformat()
                
            logger.info(f"Successfully completed brainstorming for {model_id}")
            return {
                "status": "success",
                "result": response_text,
                "model": model_id,
                "elapsed_time": response.get("elapsed_time", 0)
            }
        except Exception as e:
            logger.error(f"Unexpected error in brainstorming: {str(e)}")
            return {
                "status": "error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def compare_ai_models(self, 
                         topic: str,
                         assumptions: Optional[List[str]] = None,
                         timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Compare results from multiple AI models for the same topic.
        
        Args:
            topic: The main topic/idea to brainstorm
            assumptions: Optional list of assumptions
            timeout: Optional timeout in seconds
            
        Returns:
            Dict with comparison results
        """
        logger.info(f"Comparing AI models for topic: {topic}")
        
        results = {}
        errors = []
        
        # For each model, run the brainstorming
        for model_id in ["claude-3-7", "gpt4"]:
            try:
                result = self.run_brainstorming(
                    topic=topic,
                    model_id=model_id,
                    assumptions=assumptions,
                    timeout=timeout
                )
                
                if result.get("status") == "success":
                    results[model_id] = result.get("result", "")
                else:
                    errors.append(f"{model_id}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                errors.append(f"{model_id}: {str(e)}")
        
        # Return results
        if results:
            return {
                "status": "success",
                "results": results,
                "errors": errors if errors else None
            }
        else:
            return {
                "status": "error",
                "message": "Failed to get results from any AI model",
                "errors": errors
            }
    
    def create_outline(self, 
                     selected_model_id: str = None,
                     manual_outline: str = None,
                     timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a structured outline for the content.
        
        Args:
            selected_model_id: Optionally specify which model's brainstorming to use
            manual_outline: Optionally provide a manual outline
            timeout: Optional timeout in seconds
            
        Returns:
            Dict with outline results
        """
        logger.info("Creating outline")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project"}
            
        if manual_outline:
            # Use the provided manual outline
            outline = manual_outline
            source = "manual"
        elif selected_model_id and selected_model_id in self.current_project["brainstorming"]:
            # Use the selected model's brainstorming result
            brainstorming = self.current_project["brainstorming"][selected_model_id]
            topic = brainstorming["topic"]
            result = brainstorming["result"]
            source = f"ai_{selected_model_id}"
            
            # Generate outline from brainstorming
            prompt = f"""
Based on the following brainstorming for the topic "{topic}", create a structured outline for a presentation.

BRAINSTORMING:
{result}

Create an outline with the following:
1. An attention-grabbing title
2. 5-8 main sections
3. 2-3 key points for each section
4. A strong conclusion

Format the outline in a clean, hierarchical structure using markdown.
"""
            system_prompt = "You are an expert content strategist who excels at creating structured outlines."
            
            try:
                response = self.ai.get_completion(
                    model_id="claude-3-7",  # Use Claude 3.7 for outline generation
                    prompt=prompt,
                    system_prompt=system_prompt,
                    timeout=timeout or self.default_timeout
                )
                
                if response.get("status") == "error":
                    return {
                        "status": "error",
                        "message": f"Failed to generate outline: {response.get('message')}"
                    }
                
                outline = response.get("response", "")
            except Exception as e:
                logger.error(f"Error generating outline: {str(e)}")
                return {"status": "error", "message": f"Error generating outline: {str(e)}"}
        else:
            # No valid source for outline
            return {
                "status": "error", 
                "message": "No brainstorming result selected and no manual outline provided"
            }
        
        # Store the outline in the current project
        self.current_project["outline"] = {
            "content": outline,
            "source": source,
            "timestamp": datetime.now().isoformat()
        }
        self.current_project["updated_at"] = datetime.now().isoformat()
        
        return {
            "status": "success",
            "outline": outline,
            "source": source
        }
    
    def generate_slide_deck(self, style_template: str = "default", use_ai: bool = True, model_id: str = "claude-sonnet") -> Dict[str, Any]:
        """
        Generate a complete slide deck based on the outline.
        
        Args:
            style_template: The style template to use
            use_ai: Whether to use AI to enhance slide content
            model_id: The AI model to use for enhancement
            
        Returns:
            Dict with slide deck results
        """
        logger.info(f"Generating slide deck with template: {style_template}, use_ai: {use_ai}, model: {model_id if use_ai else 'N/A'}")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project"}
            
        if not self.current_project.get("outline"):
            return {"status": "error", "message": "No outline available. Please create an outline first."}
        
        outline = self.current_project["outline"]["content"]
        
        try:
            # First generate basic slides from outline
            basic_slides = self.slide_generator.generate_slides(
                outline=outline,
                style_template=style_template
            )
            
            # If use_ai is true, enhance the slides with AI
            if use_ai:
                slides = self.enhance_slides_with_ai(basic_slides, model_id)
            else:
                slides = basic_slides
            
            # Store slides in the project
            self.current_project["slides"] = slides
            self.current_project["updated_at"] = datetime.now().isoformat()
            
            return {
                "status": "success",
                "slides": slides
            }
        except Exception as e:
            logger.error(f"Error generating slides: {str(e)}")
            return {"status": "error", "message": f"Error generating slides: {str(e)}"}
    
    def enhance_slides_with_ai(self, slides: List[Dict[str, Any]], model_id: str = "claude-sonnet") -> List[Dict[str, Any]]:
        """
        Enhance slide content using AI.
        
        Args:
            slides: Basic slides to enhance
            model_id: AI model to use
            
        Returns:
            Enhanced slides
        """
        logger.info(f"Enhancing slides with AI model: {model_id}")
        
        if not self.ai.validate_model_availability(model_id):
            logger.warning(f"Model {model_id} not available. Falling back to claude.")
            model_id = "claude"
        
        enhanced_slides = []
        
        for slide in slides:
            slide_title = slide.get("title", "")
            slide_content = slide.get("content", "")
            original_points = slide.get("points", [])
            
            # Format existing points for reference
            original_points_text = "\n".join([f"- {point}" for point in original_points])
            
            # Create a prompt for AI to enhance this slide
            prompt = f"""
I need you to enhance the content for a presentation slide with the following details:

SLIDE TITLE: {slide_title}

SLIDE CONTENT: {slide_content}

EXISTING POINTS:
{original_points_text}

Please generate 5 improved, substantive key points for this slide that follow this EXACT format:
"<Key Term>: <One complete sentence explanation>"

Each point should:
1. Start with a meaningful key term (1-3 words) that captures an important concept
2. Follow with a colon
3. End with a full, informative sentence that provides valuable context or explanation
4. Be substantive and specific to the slide's topic
5. Avoid generic placeholders

The explanation should be insightful, specific, and directly relevant to the topic. 
DO NOT use generic explanations like "This represents a fundamental concept within the realm of..."

Only provide the 5 points in the exact format requested, nothing else.
"""
            
            # Get AI completion
            try:
                response = self.ai.get_completion(
                    model_id=model_id,
                    prompt=prompt,
                    system_prompt="You are an expert presentation designer who excels at creating substantive, insightful slide content.",
                    timeout=45  # Shorter timeout for individual slide enhancement
                )
                
                if response.get("status") == "success":
                    # Parse the enhanced points from the AI response
                    enhanced_points = []
                    
                    # Split response by lines and process each line that contains a colon
                    for line in response.get("response", "").split("\n"):
                        line = line.strip()
                        # Remove any bullet points or numbers
                        line = line.lstrip("•-*#0123456789. ")
                        
                        if ":" in line and len(line) > 5:
                            enhanced_points.append(line)
                    
                    # Ensure we have at least 5 points
                    if len(enhanced_points) >= 5:
                        # Use the enhanced points
                        enhanced_slide = slide.copy()
                        enhanced_slide["points"] = enhanced_points[:5]  # Take only the first 5 points
                        enhanced_slides.append(enhanced_slide)
                    else:
                        # If we don't have enough enhanced points, use the original slide
                        logger.warning(f"Not enough enhanced points generated for slide '{slide_title}'. Using original.")
                        enhanced_slides.append(slide)
                else:
                    # If AI enhancement failed, use the original slide
                    logger.warning(f"Failed to enhance slide '{slide_title}'. Using original. Error: {response.get('message')}")
                    enhanced_slides.append(slide)
            
            except Exception as e:
                logger.error(f"Error enhancing slide '{slide_title}': {str(e)}")
                enhanced_slides.append(slide)  # Use original if enhancement fails
        
        return enhanced_slides
    
    def format_slide_deck(self, 
                        bold_key_terms: bool = True,
                        highlight_color: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply formatting to the slide deck for better presentation.
        
        Args:
            bold_key_terms: Whether to bold key terms
            highlight_color: Optional highlight color for important points
            
        Returns:
            Dict with formatting results
        """
        logger.info("Applying formatting to slide deck")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project"}
            
        if not self.current_project.get("slides"):
            return {"status": "error", "message": "No slides available. Please generate slides first."}
        
        try:
            formatted_slides = self.slide_generator.format_slides(
                slides=self.current_project["slides"],
                bold_key_terms=bold_key_terms,
                highlight_color=highlight_color
            )
            
            # Store formatting options
            self.current_project["formatting"] = {
                "bold_key_terms": bold_key_terms,
                "highlight_color": highlight_color,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update slides
            self.current_project["slides"] = formatted_slides
            self.current_project["updated_at"] = datetime.now().isoformat()
            
            return {
                "status": "success",
                "slides": formatted_slides
            }
        except Exception as e:
            logger.error(f"Error formatting slides: {str(e)}")
            return {"status": "error", "message": f"Error formatting slides: {str(e)}"}
    
    def generate_thumbnail(self, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a thumbnail image for the content.
        
        Args:
            prompt: Optional custom prompt for image generation
            
        Returns:
            Dict with thumbnail results
        """
        logger.info("Generating thumbnail")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project"}
        
        # Get the project title and outline if available
        title = self.current_project["title"]
        outline_content = self.current_project.get("outline", {}).get("content", "")
        
        # Create a prompt for image generation
        if not prompt:
            # Extract the first couple of lines from the outline to use as context
            outline_summary = "\n".join(outline_content.split("\n")[:5])
            
            prompt = f"""Create a professional, visually striking thumbnail image for a presentation titled 
"{title}". 

The presentation covers:
{outline_summary}

The image should be modern, clean, and suitable for a business or academic context.
Use a color scheme that conveys professionalism and innovation.
"""
        
        try:
            # Call image generation
            image_result = self.image_generator.generate_image(prompt)
            
            # Check for errors
            if image_result.get("status") == "error":
                return {
                    "status": "error",
                    "message": f"Failed to generate thumbnail: {image_result.get('message')}"
                }
            
            # Store in the project
            self.current_project["images"]["thumbnail"] = {
                "url": image_result.get("image_url"),
                "prompt": prompt,
                "revised_prompt": image_result.get("revised_prompt"),
                "timestamp": datetime.now().isoformat()
            }
            self.current_project["updated_at"] = datetime.now().isoformat()
            
            return {
                "status": "success",
                "url": image_result.get("image_url"),
                "revised_prompt": image_result.get("revised_prompt")
            }
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return {"status": "error", "message": f"Error generating thumbnail: {str(e)}"}
    
    def export_slides(self, format: str = "google_slides", output_dir: str = None) -> Dict[str, Any]:
        """
        Export the slides to the specified format.
        
        Args:
            format: The format to export to (google_slides, powerpoint, pdf, html)
            output_dir: The directory to save the exported file
            
        Returns:
            Dict with export results
        """
        logger.info(f"Exporting slides to {format}")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project"}
            
        if not self.current_project.get("slides"):
            return {"status": "error", "message": "No slides available. Please generate slides first."}
        
        if not output_dir:
            # Use the exports directory in the project folder
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use the SlideDeckGenerator to export
            result = self.slide_generator.export_slides(
                slides=self.current_project["slides"],
                format=format,
                output_dir=output_dir
            )
            
            # Update project with export information
            if "export_path" in result:
                self.current_project["export"] = {
                    "path": result["export_path"],
                    "format": result.get("format", format),
                    "timestamp": datetime.now().isoformat()
                }
                self.current_project["updated_at"] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Error exporting slides: {str(e)}")
            return {"status": "error", "message": f"Error exporting slides: {str(e)}"}
    
    def save_project(self, filepath: str) -> Dict[str, Any]:
        """
        Save the current project to a file.
        
        Args:
            filepath: Path to save the project
            
        Returns:
            Dict with save results
        """
        logger.info(f"Saving project to {filepath}")
        
        if not self.current_project:
            return {"status": "error", "message": "No active project to save"}
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_project, f, indent=2)
                
            return {
                "status": "success",
                "filepath": filepath
            }
        except Exception as e:
            logger.error(f"Error saving project: {str(e)}")
            return {"status": "error", "message": f"Error saving project: {str(e)}"}
    
    def load_project(self, filepath: str) -> Dict[str, Any]:
        """
        Load a project from a file.
        
        Args:
            filepath: Path to load the project from
            
        Returns:
            Dict with load results
        """
        logger.info(f"Loading project from {filepath}")
        
        try:
            with open(filepath, 'r') as f:
                project_data = json.load(f)
                
            self.current_project = project_data
            
            return {
                "status": "success",
                "project": project_data
            }
        except Exception as e:
            logger.error(f"Error loading project: {str(e)}")
            return {"status": "error", "message": f"Error loading project: {str(e)}"}
