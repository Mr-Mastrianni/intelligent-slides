"""
AI Interface module for the Content Workflow Automation Agent.
Handles communication with various AI providers (Anthropic, OpenAI).
"""
import time
import logging
import concurrent.futures
from typing import Dict, Any, List, Optional

import anthropic
import openai
from config import ANTHROPIC_API_KEY, OPENAI_API_KEY, AI_MODELS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AIInterface:
    """Interface for communicating with various AI models."""
    
    def __init__(self):
        """Initialize API clients."""
        # Initialize Anthropic client
        self.anthropic_client = None
        if ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Initialize OpenAI client
        self.openai_client = None
        if OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Track usage for rate limiting
        self.last_request_time = {}
        
        # Set default timeouts - much shorter to prevent hanging
        self.default_timeout = 30  # 30 seconds
        self.claude_timeout = 20   # Even shorter for Claude
        self.max_retries = 1       # Reduce retries to speed up process
    
    def validate_model_availability(self, model_id: str) -> bool:
        """Check if the specified model is available for use."""
        if model_id not in AI_MODELS:
            logger.warning(f"Unknown model ID: {model_id}")
            return False
            
        model_config = AI_MODELS[model_id]
        provider = model_config["provider"]
        
        if provider == "anthropic" and not self.anthropic_client:
            logger.warning("Anthropic API key not configured")
            return False
        elif provider == "openai" and not self.openai_client:
            logger.warning("OpenAI API key not configured")
            return False
            
        return True
    
    def get_completion(self, 
                      model_id: str, 
                      prompt: str, 
                      system_prompt: Optional[str] = None,
                      temperature: Optional[float] = None,
                      max_tokens: Optional[int] = None,
                      with_thinking: bool = False,
                      timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Get completion from the specified AI model.
        
        Args:
            model_id: The ID of the model to use (as defined in config.AI_MODELS)
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            with_thinking: Whether to use "thinking" mode with Claude
            timeout: Optional timeout in seconds
            
        Returns:
            Dict containing response text and metadata
        """
        if not self.validate_model_availability(model_id):
            return {"status": "error", "message": f"Model {model_id} is not available"}
        
        # Apply rate limiting
        self._apply_rate_limit(model_id)
        
        model_config = AI_MODELS[model_id]
        provider = model_config["provider"]
        model_name = model_config["model"]
        
        # Use config defaults if not overridden
        if temperature is None:
            temperature = model_config.get("temperature", 0.7)
        if max_tokens is None:
            max_tokens = model_config.get("max_tokens", 4000)
        
        # Set timeout based on provider - Claude needs shorter timeouts to avoid hanging
        if timeout is None:
            if provider == "anthropic":
                timeout = self.claude_timeout
            else:
                timeout = self.default_timeout
            
        # Default system prompt if none provided
        if system_prompt is None:
            system_prompt = self.get_default_prompts()["outline"]
        
        start_time = time.time()
        
        # Use a timeout mechanism with concurrent futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if provider == "anthropic":
                future = executor.submit(
                    self._get_anthropic_completion_with_retry,
                    model_name, prompt, system_prompt, temperature, max_tokens, with_thinking
                )
            elif provider == "openai":
                future = executor.submit(
                    self._get_openai_completion_with_retry,
                    model_name, prompt, system_prompt, temperature, max_tokens
                )
            else:
                return {"status": "error", "message": f"Unsupported provider: {provider}"}
            
            try:
                # Wait for the future to complete with a timeout
                result = future.result(timeout=timeout)
                
                # Calculate and log the response time
                elapsed_time = time.time() - start_time
                logger.info(f"Got {provider} response in {elapsed_time:.2f}s")
                
                # Add metadata to the response
                result.update({
                    "elapsed_time": elapsed_time,
                    "model": model_name,
                    "provider": provider,
                    "status": "success"
                })
                
                return result
            except concurrent.futures.TimeoutError:
                # Handle timeout - cancel the future if possible
                future.cancel()
                logger.error(f"Request to {provider} timed out after {timeout}s")
                return {
                    "status": "error",
                    "message": f"Request timed out after {timeout} seconds",
                    "model": model_name,
                    "provider": provider
                }
            except Exception as e:
                # Handle any other exceptions
                logger.error(f"Error getting {provider} completion: {str(e)}")
                return {
                    "status": "error",
                    "message": str(e),
                    "model": model_name,
                    "provider": provider
                }
    
    def get_default_prompts(self) -> Dict[str, str]:
        """
        Get default system prompts for different tasks.
        
        Returns:
            Dict of default prompts
        """
        return {
            "brainstorming": """You are an expert content strategist helping brainstorm ideas for a presentation.
            Generate thoughtful, creative, and diverse ideas related to the topic.
            Focus on providing a variety of approaches, perspectives, and angles that could be developed into a presentation.
            Include both mainstream and potentially novel or unexpected ideas.
            Format your response as a well-organized set of brief thoughts, using clear paragraphs without numbered lists.
            Keep the total length to around 800-1200 characters, focusing on quality over quantity.""",
            
            "outline": """You are an expert presentation designer. Your task is to create a structured outline for a slide deck 
            based on the brainstorming content provided.
            
            Follow these guidelines for creating an effective presentation outline:
            
            1. Create a compelling title (2-6 words) for the presentation
            2. Structure the outline with main sections, each containing 1-3 slides
            3. Design each slide to follow this exact format:
               - Title: 2 to 6 words, pithy and memorable
               - Body: 2 to 3 complete sentences explaining the slide's main message
               - Points: 5 key points with the format "<Key Point>: <One complete sentence explanation>"
                 IMPORTANT: Every key point must be substantive and specific to the slide's topic,
                 not generic placeholders. Each point should start with a meaningful term followed by
                 a colon and then a full, informative sentence that provides valuable context.
            
            4. Each slide should be focused on a single clear concept
            5. Include approximately 7-10 slides total (including title slide)
            6. Ensure the presentation flows logically from start to finish
            7. The outline should be comprehensive enough to generate complete slides
            
            Format the outline in Markdown with clear hierarchical structure.
            
            Example slide format:
            
            ## Durable Trends
            
            Durable trends provide measurable, long-term patterns that anchor future forecasts. Humans evolved to think "locally and geometrically" thus we suck at intuitively understanding data and exponentials.
            
            - Global Scope: We do not have the ability to comprehend global data or trends intuitively. It's just statistics.
            - Exponential Growth: We have no intuitive understanding of exponential growth.
            - Short Horizons: Humans evolved to think, at most, a year ahead. We needed to survive winter and that was it.
            - Trust the Data: Real data and durable trends on a graph provide more insight than expert gut checks.
            - Future Planning: The most reliable forecasting combines historical data patterns with critical trend analysis.""",
            
            "slides": """You are an expert presentation designer. Your task is to transform the provided outline into fully-formed slide content.
            
            Follow these guidelines for creating effective slides:
            
            1. Ensure each slide follows this exact format:
               - Title: 2 to 6 words, pithy and memorable
               - Body: 2 to 3 complete sentences explaining the slide's main message
               - Points: Exactly 5 key points with the format "<Key Point>: <One complete sentence explanation>"
               
               CRITICAL: Each key point MUST follow this exact format:
               * Start with a meaningful term (1-3 words) that captures an important concept
               * Follow with a colon
               * End with a full, informative sentence that provides valuable context or explanation
               * Never use generic placeholders like "Key Point: Additional information" 
               * Ensure each point is substantive and specific to the slide's topic
            
            2. Use clear, concise language with specific terminology from the outline
            3. Create visually balanced slides (similar amount of content per slide)
            4. Maintain a consistent tone and style across all slides
            5. Avoid jargon unless it's domain-appropriate
            
            Example of well-formed key points:
            - Global Scope: We do not have the ability to comprehend global data or trends intuitively.
            - Exponential Growth: Humans have no intuitive understanding of exponential functions and consistently underestimate their impact.
            - Short Horizons: Our evolutionary history optimized for short-term planning rather than long-term forecasting.
            
            Return the content in a structured format that clearly shows each slide's content."""
        }
    
    def _get_anthropic_completion_with_retry(self, 
                                          model: str, 
                                          prompt: str, 
                                          system_prompt: str,
                                          temperature: float,
                                          max_tokens: int,
                                          with_thinking: bool) -> Dict[str, Any]:
        """Get completion from Anthropic models with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                return self._get_anthropic_completion(
                    model, prompt, system_prompt, temperature, max_tokens, with_thinking
                )
            except Exception as e:
                logger.warning(f"Anthropic API attempt {attempt+1} failed: {str(e)}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # If all retries failed, re-raise the exception
                    raise
    
    def _get_openai_completion_with_retry(self,
                                       model: str,
                                       prompt: str,
                                       system_prompt: str,
                                       temperature: float,
                                       max_tokens: int) -> Dict[str, Any]:
        """Get completion from OpenAI models with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                return self._get_openai_completion(
                    model, prompt, system_prompt, temperature, max_tokens
                )
            except Exception as e:
                logger.warning(f"OpenAI API attempt {attempt+1} failed: {str(e)}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # If all retries failed, re-raise the exception
                    raise
    
    def _get_anthropic_completion(self, 
                                  model: str, 
                                  prompt: str, 
                                  system_prompt: str,
                                  temperature: float,
                                  max_tokens: int,
                                  with_thinking: bool) -> Dict[str, Any]:
        """Get completion from Anthropic models."""
        logger.info(f"Getting Anthropic completion with model: {model}")
        
        if not self.anthropic_client:
            raise ValueError("Anthropic client not initialized")
            
        try:
            # Use a simpler prompt structure to reduce token count
            formatted_prompt = prompt
            if with_thinking:
                # Simplified thinking prompt
                formatted_prompt = f"Topic: {prompt}\n\nThink through this step by step."
            
            # Call the Anthropic API with strict timeout and reduced max tokens
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=min(max_tokens, 1000),  # Limit token count for faster responses
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": formatted_prompt}
                ],
                timeout=self.claude_timeout
            )
            
            # Extract the response text
            response_text = response.content[0].text
            logger.info(f"Received response from Anthropic API. Content length: {len(response_text)}")
            
            # Debug truncated response
            preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
            logger.info(f"Response preview: {preview}")
            
            return {
                "response": response_text,
                "token_usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }
        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout: {str(e)}")
            raise TimeoutError(f"Timeout error: {str(e)}")
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in Anthropic API call: {str(e)}")
            raise
    
    def _get_openai_completion(self,
                              model: str,
                              prompt: str,
                              system_prompt: str,
                              temperature: float,
                              max_tokens: int) -> Dict[str, Any]:
        """Get completion from OpenAI models."""
        logger.info(f"Getting OpenAI completion with model: {model}")
        
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
            
        try:
            # Call the OpenAI API
            response = self.openai_client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            return {
                "response": response_text,
                "token_usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                }
            }
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {str(e)}")
            raise
    
    def _apply_rate_limit(self, model_id: str, min_interval: float = 0.5) -> None:
        """Apply basic rate limiting to avoid hitting API limits."""
        current_time = time.time()
        last_time = self.last_request_time.get(model_id, 0)
        
        # If we've made a request too recently, wait
        if current_time - last_time < min_interval:
            sleep_time = min_interval - (current_time - last_time)
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
            
        # Update the last request time
        self.last_request_time[model_id] = time.time()
    
    def generate_image(self, prompt: str, size: str = "1792x1024", quality: str = "hd") -> Dict[str, Any]:
        """Generate an image using DALL-E."""
        logger.info(f"Generating image with prompt: {prompt[:50]}...")
        
        if not self.openai_client:
            return {"status": "error", "message": "OpenAI client not initialized"}
            
        start_time = time.time()
        
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    self._generate_image_with_retry,
                    prompt, size, quality
                )
                
                try:
                    # Wait for the future to complete with a timeout
                    result = future.result(timeout=60)  # 60 second timeout for image generation
                    
                    # Calculate and log the response time
                    elapsed_time = time.time() - start_time
                    logger.info(f"Generated image in {elapsed_time:.2f}s")
                    
                    result["elapsed_time"] = elapsed_time
                    result["status"] = "success"
                    return result
                except concurrent.futures.TimeoutError:
                    logger.error("Image generation timed out after 60s")
                    return {
                        "status": "error",
                        "message": "Image generation request timed out after 60 seconds"
                    }
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_image_with_retry(self, prompt: str, size: str, quality: str) -> Dict[str, Any]:
        """Generate an image with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                response = self.openai_client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1
                )
                
                return {
                    "image_url": response.data[0].url,
                    "revised_prompt": response.data[0].revised_prompt
                }
            except Exception as e:
                logger.warning(f"DALL-E API attempt {attempt+1} failed: {str(e)}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # If all retries failed, re-raise the exception
                    raise
