"""
Google Slides Exporter module for the Content Workflow Automation Agent.
Handles the export of slide decks to Google Slides.
"""
import logging
import os
from typing import Dict, Any, List, Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
except ImportError:
    logging.warning("Google API libraries not fully installed. Google Slides export may not work.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/presentations', 'https://www.googleapis.com/auth/drive']

class GoogleSlidesExporter:
    """Handles the export of slide decks to Google Slides."""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """
        Initialize the Google Slides exporter.
        
        Args:
            credentials_path: Path to the Google API credentials file
        """
        self.credentials_path = credentials_path
        self.service = None
        self.drive_service = None
        self.credentials = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google API.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            creds = None
            # The file token.json stores the user's access and refresh tokens
            if os.path.exists('token.json'):
                try:
                    creds = Credentials.from_authorized_user_info(
                        json.loads(open('token.json', 'r').read()), SCOPES)
                except (ValueError, RefreshError) as e:
                    logger.warning(f"Error loading credentials: {e}")
                    os.remove('token.json')
                    creds = None
            
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except RefreshError:
                        os.remove('token.json')
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Credentials file not found at {self.credentials_path}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            self.credentials = creds
            self.service = build('slides', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            return True
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def create_presentation(self, title: str) -> Optional[str]:
        """
        Create a new Google Slides presentation.
        
        Args:
            title: Title of the presentation
            
        Returns:
            str: ID of the created presentation, or None if creation failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            presentation = {
                'title': title
            }
            presentation = self.service.presentations().create(body=presentation).execute()
            presentation_id = presentation.get('presentationId')
            logger.info(f"Created presentation with ID: {presentation_id}")
            return presentation_id
        
        except Exception as e:
            logger.error(f"Failed to create presentation: {e}")
            return None
    
    def add_slide(self, presentation_id: str, title: str, content: List[str], 
                  layout: str = 'TITLE_AND_BODY') -> bool:
        """
        Add a slide to an existing presentation.
        
        Args:
            presentation_id: ID of the presentation
            title: Title of the slide
            content: List of content items for the slide
            layout: Slide layout type
            
        Returns:
            bool: True if slide was added successfully, False otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return False
            
            # Determine the appropriate layout based on the input
            slide_layout_mapping = {
                'TITLE_AND_BODY': 'TITLE_AND_BODY',
                'TITLE_ONLY': 'TITLE_ONLY',
                'SECTION_HEADER': 'SECTION_HEADER',
                'TITLE_AND_TWO_COLUMNS': 'TITLE_AND_TWO_COLUMNS',
                'BLANK': 'BLANK'
            }
            
            layout_id = slide_layout_mapping.get(layout, 'TITLE_AND_BODY')
            
            # Create a new slide
            requests = [
                {
                    'createSlide': {
                        'slideLayoutReference': {
                            'predefinedLayout': layout_id
                        },
                        'placeholderIdMappings': [
                            {
                                'layoutPlaceholder': {
                                    'type': 'TITLE',
                                    'index': 0
                                },
                                'objectId': f'title_{int(time.time())}'
                            },
                            {
                                'layoutPlaceholder': {
                                    'type': 'BODY',
                                    'index': 0
                                },
                                'objectId': f'body_{int(time.time())}'
                            }
                        ]
                    }
                }
            ]
            
            response = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            slide_id = response.get('replies')[0].get('createSlide').get('objectId')
            
            # Add title and content to the slide
            requests = [
                {
                    'insertText': {
                        'objectId': f'title_{int(time.time())}',
                        'text': title
                    }
                }
            ]
            
            # Format content as bullet points
            content_text = ""
            for item in content:
                content_text += f"• {item}\n"
            
            requests.append({
                'insertText': {
                    'objectId': f'body_{int(time.time())}',
                    'text': content_text
                }
            })
            
            self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Added slide to presentation {presentation_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add slide: {e}")
            return False
    
    def export_slide_deck(self, slide_deck: Dict[str, Any]) -> Optional[str]:
        """
        Export a slide deck to Google Slides.
        
        Args:
            slide_deck: Dictionary containing slide deck information
            
        Returns:
            str: URL of the created presentation, or None if export failed
        """
        try:
            title = slide_deck.get('title', 'Untitled Presentation')
            presentation_id = self.create_presentation(title)
            
            if not presentation_id:
                return None
            
            slides = slide_deck.get('slides', [])
            for slide in slides:
                slide_title = slide.get('title', '')
                slide_content = slide.get('points', [])
                slide_type = slide.get('type', 'standard')
                
                # Map slide type to Google Slides layout
                layout_mapping = {
                    'title': 'TITLE_ONLY',
                    'section': 'SECTION_HEADER',
                    'standard': 'TITLE_AND_BODY',
                    'two_column': 'TITLE_AND_TWO_COLUMNS',
                    'blank': 'BLANK'
                }
                
                layout = layout_mapping.get(slide_type, 'TITLE_AND_BODY')
                
                self.add_slide(presentation_id, slide_title, slide_content, layout)
            
            # Get the presentation URL
            presentation = self.service.presentations().get(
                presentationId=presentation_id).execute()
            
            presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
            logger.info(f"Exported slide deck to {presentation_url}")
            
            return presentation_url
        
        except Exception as e:
            logger.error(f"Failed to export slide deck: {e}")
            return None
