"""
Image Generator module for the Content Workflow Automation Agent.
Handles the generation of thumbnail images and slide graphics.
"""
import logging
import os
import requests
from typing import Dict, Any, Optional
from io import BytesIO
from PIL import Image

from config import OPENAI_API_KEY, IMAGE_GENERATION

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImageGenerator:
    """Handles the generation of images for thumbnails and slides."""
    
    def __init__(self):
        """Initialize the image generator."""
        self.openai_api_key = OPENAI_API_KEY
        self.config = IMAGE_GENERATION
    
    def generate_image(self, prompt: str, size: Optional[str] = None, quality: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an image using the configured provider.
        
        Args:
            prompt: The prompt for image generation
            size: Optional size override
            quality: Optional quality override
            
        Returns:
            Dict with image generation results
        """
        if not self.openai_api_key:
            return {"error": "OpenAI API key not configured"}
        
        # Use configuration defaults if not overridden
        if not size:
            size = self.config.get("size", "1024x1024")
        if not quality:
            quality = self.config.get("quality", "standard")
        
        provider = self.config.get("provider", "openai")
        
        if provider == "openai":
            return self._generate_image_openai(prompt, size, quality)
        else:
            return {"error": f"Unsupported image provider: {provider}"}
    
    def _generate_image_openai(self, prompt: str, size: str, quality: str) -> Dict[str, Any]:
        """
        Generate an image using OpenAI's DALL-E.
        
        Args:
            prompt: The prompt for image generation
            size: Image size
            quality: Image quality
            
        Returns:
            Dict with image generation results
        """
        import openai
        
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            logger.info(f"Generating image with prompt: {prompt}")
            response = client.images.generate(
                model=self.config.get("model", "dall-e-3"),
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            
            result = {
                "url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt if hasattr(response.data[0], 'revised_prompt') else None
            }
            
            logger.info("Image generation successful")
            return result
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return {"error": str(e)}
    
    def download_image(self, url: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Download an image from a URL.
        
        Args:
            url: The URL to download from
            save_path: Optional path to save the image
            
        Returns:
            Dict with download results
        """
        try:
            logger.info(f"Downloading image from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            
            if save_path:
                img.save(save_path)
                logger.info(f"Image saved to: {save_path}")
                return {
                    "success": True,
                    "filepath": save_path,
                    "width": img.width,
                    "height": img.height
                }
            else:
                # Return image data without saving
                return {
                    "success": True,
                    "image": img,
                    "width": img.width,
                    "height": img.height
                }
                
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return {"error": str(e)}
    
    def create_thumbnail_prompt(self, title: str, key_points: list) -> str:
        """
        Create an optimized prompt for thumbnail generation.
        
        Args:
            title: The title of the content
            key_points: List of key points or terms
            
        Returns:
            A prompt for image generation
        """
        # Filter to most relevant key points (max 5)
        filtered_points = key_points[:5] if len(key_points) > 5 else key_points
        
        prompt = f"""Create a widescreen digital art image for: "{title}". 
A professional, high-quality presentation thumbnail that visually represents the following concepts: {', '.join(filtered_points)}.
Style: Modern, clean, futuristic, with vibrant colors and professional aesthetics. 
The image should be visually striking and suitable as a video thumbnail or presentation cover.
No text or words should be included in the image.
"""
        
        return prompt
