"""
Google Drive Uploader module for the Content Workflow Automation Agent.
Handles uploading files to Google Drive.
"""
import logging
import os
import json
from typing import Dict, Any, List, Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
except ImportError:
    logging.warning("Google API libraries not fully installed. Google Drive upload may not work.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveUploader:
    """Handles uploading files to Google Drive."""
    
    def __init__(self, credentials_path: str = 'credentials.json'):
        """
        Initialize the Google Drive uploader.
        
        Args:
            credentials_path: Path to the Google API credentials file
        """
        self.credentials_path = credentials_path
        self.service = None
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
            self.service = build('drive', 'v3', credentials=creds)
            return True
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def upload_file(self, file_path: str, mime_type: Optional[str] = None, 
                   folder_id: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to the file to upload
            mime_type: MIME type of the file (optional)
            folder_id: ID of the folder to upload to (optional)
            
        Returns:
            str: ID of the uploaded file, or None if upload failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            file_name = os.path.basename(file_path)
            
            # Determine MIME type if not provided
            if not mime_type:
                extension = os.path.splitext(file_path)[1].lower()
                mime_mapping = {
                    '.pdf': 'application/pdf',
                    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.txt': 'text/plain',
                    '.csv': 'text/csv',
                    '.json': 'application/json',
                    '.html': 'text/html',
                }
                mime_type = mime_mapping.get(extension, 'application/octet-stream')
            
            file_metadata = {'name': file_name}
            
            # If folder_id is provided, set the parent folder
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"File uploaded with ID: {file_id}")
            
            return file_id
        
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_folder_id: ID of the parent folder (optional)
            
        Returns:
            str: ID of the created folder, or None if creation failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # If parent_folder_id is provided, set the parent folder
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Folder created with ID: {folder_id}")
            
            return folder_id
        
        except Exception as e:
            logger.error(f"Failed to create folder: {e}")
            return None
    
    def get_file_url(self, file_id: str) -> Optional[str]:
        """
        Get the URL of a file in Google Drive.
        
        Args:
            file_id: ID of the file
            
        Returns:
            str: URL of the file, or None if retrieval failed
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return None
            
            # Get the file metadata
            file = self.service.files().get(fileId=file_id, fields='webViewLink').execute()
            
            return file.get('webViewLink')
        
        except Exception as e:
            logger.error(f"Failed to get file URL: {e}")
            return None
    
    def share_file(self, file_id: str, email: Optional[str] = None, 
                  role: str = 'reader', type: str = 'anyone') -> bool:
        """
        Share a file in Google Drive.
        
        Args:
            file_id: ID of the file to share
            email: Email address to share with (optional)
            role: Role to grant (reader, writer, commenter, owner)
            type: Type of sharing (user, group, domain, anyone)
            
        Returns:
            bool: True if sharing was successful, False otherwise
        """
        try:
            if not self.service:
                if not self.authenticate():
                    return False
            
            # Create the permission
            permission = {
                'type': type,
                'role': role
            }
            
            if email and type != 'anyone':
                permission['emailAddress'] = email
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            ).execute()
            
            logger.info(f"File {file_id} shared successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to share file: {e}")
            return False
