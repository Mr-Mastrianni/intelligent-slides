"""
Configuration settings for the Content Workflow Automation Agent.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys (loaded from .env file)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Model configurations
AI_MODELS = {
    "claude": {
        "name": "Claude",
        "provider": "anthropic",
        "model": "claude-3-opus-20240229",
        "temperature": 0.7,
        "max_tokens": 4000,
    },
    "claude-sonnet": {
        "name": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "model": "claude-3-7-sonnet-20250219",
        "temperature": 0.7,
        "max_tokens": 4000,
    },
    "gpt4": {
        "name": "GPT-4",
        "provider": "openai",
        "model": "gpt-4-turbo",
        "temperature": 0.7,
        "max_tokens": 4000,
    },
}

# Slide deck formatting templates
SLIDE_DECK_TEMPLATE = {
    "title_slide": {
        "title_length": "2-6 words",
        "subtitle_length": "5-10 words",
    },
    "content_slide": {
        "title_length": "2-6 words",
        "body_length": "2-3 complete sentences",
        "bullet_points": "3-5 key points",
    },
}

# Slide deck style guide
STYLE_GUIDE = """
Title: 2-6 words, catchy and impactful
Body: 2-3 complete sentences, concise and clear
Key points: 3-5 bullet points with key insights
Rules:
- No conversational or generic language
- Bold key terms for emphasis
- Punchy titles that match the vibe
- Keep information dense and valuable
"""

# Image generation settings
IMAGE_GENERATION = {
    "provider": "openai",
    "model": "dall-e-3",
    "size": "1792x1024",
    "quality": "hd",
}

# Default project settings
DEFAULT_SETTINGS = {
    "output_format": "google_slides",  # or "powerpoint"
    "auto_formatting": True,
    "highlight_key_terms": True,
    "typography_style": "bold_highlights",
    "auto_image_generation": False,
}
