"""
Personal Access Token (PAT) Handler Agent for Interaction & Tasking Team.

Handles secure storage và management của Personal Access Tokens cho
private repository access.
"""

import hashlib
import secrets
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from loguru import logger
from cryptography.fernet import Fernet
import base64


@dataclass
class PATInfo:
    """Information about a stored PAT."""
    platform: str  # GitHub, GitLab, BitBucket
    username: str
    token_hash: str  # SHA256 hash of token for identification
    encrypted_token: bytes  # Encrypted token
    created_at: str
    last_used: Optional[str] = None


class PATHandlerAgent:
    """
    Agent responsible for secure PAT management.
    
    Provides secure storage và retrieval của Personal Access Tokens
    within the session scope.
    """
    
    def __init__(self, session_key: Optional[str] = None):
        """
        Initialize PAT Handler Agent.
        
        Args:
            session_key: Session-specific encryption key. If None, generates random key.
        """
        self.session_key = session_key or self._generate_session_key()
        self.cipher = Fernet(self.session_key)
        self.stored_pats: Dict[str, PATInfo] = {}
        
        # Platform patterns for validation
        self.platform_patterns = {
            'github': {
                'prefixes': ['ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'],
                'min_length': 40
            },
            'gitlab': {
                'prefixes': ['glpat-'],
                'min_length': 20
            },
            'bitbucket': {
                'min_length': 32
            }
        }
        
        logger.info("PATHandlerAgent initialized with secure encryption")
    
    def store_pat(
        self, 
        platform: str, 
        username: str, 
        token: str,
        session_id: str
    ) -> str:
        """
        Store PAT securely within session scope.
        
        Args:
            platform: Git platform (GitHub, GitLab, BitBucket)
            username: Username for the platform
            token: Personal Access Token
            session_id: Current session identifier
            
        Returns:
            str: Token hash for later retrieval
        """
        if not token or not token.strip():
            raise ValueError("Token cannot be empty")
        
        # Create token hash for identification
        token_hash = self._create_token_hash(token, session_id)
        
        # Encrypt token
        encrypted_token = self.cipher.encrypt(token.encode())
        
        # Store PAT info
        pat_info = PATInfo(
            platform=platform.lower(),
            username=username,
            token_hash=token_hash,
            encrypted_token=encrypted_token,
            created_at=self._get_current_timestamp()
        )
        
        self.stored_pats[token_hash] = pat_info
        
        logger.info(f"PAT stored securely for {username}@{platform} (hash: {token_hash[:8]}...)")
        return token_hash
    
    def retrieve_pat(self, token_hash: str) -> Optional[str]:
        """
        Retrieve PAT by hash.
        
        Args:
            token_hash: Hash of the token to retrieve
            
        Returns:
            Decrypted token or None if not found
        """
        if token_hash not in self.stored_pats:
            logger.warning(f"PAT not found for hash: {token_hash[:8]}...")
            return None
        
        pat_info = self.stored_pats[token_hash]
        
        try:
            # Decrypt token
            decrypted_token = self.cipher.decrypt(pat_info.encrypted_token).decode()
            
            # Update last used timestamp
            pat_info.last_used = self._get_current_timestamp()
            
            logger.info(f"PAT retrieved for {pat_info.username}@{pat_info.platform}")
            return decrypted_token
            
        except Exception as e:
            logger.error(f"Failed to decrypt PAT: {str(e)}")
            return None
    
    def validate_pat_format(self, platform: str, token: str) -> bool:
        """
        Validate PAT format for different platforms.
        
        Args:
            platform: Git platform
            token: Token to validate
            
        Returns:
            True if format is valid
        """
        platform = platform.lower()
        
        # Basic validation rules
        validation_rules = {
            'github': {
                'prefixes': ['ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_'],
                'min_length': 40
            },
            'gitlab': {
                'prefixes': ['glpat-'],
                'min_length': 20
            },
            'bitbucket': {
                'min_length': 32
            }
        }
        
        if platform not in validation_rules:
            # Generic validation
            return len(token) >= 20 and token.isalnum()
        
        rules = validation_rules[platform]
        
        # Check minimum length
        if len(token) < rules['min_length']:
            return False
        
        # Check prefixes if specified
        if 'prefixes' in rules:
            if not any(token.startswith(prefix) for prefix in rules['prefixes']):
                return False
        
        logger.info(f"PAT format validation for {platform}: {'VALID' if True else 'INVALID'}")
        return True
    
    def is_valid_pat_format(self, token: str, platform: str) -> bool:
        """
        Alias for validate_pat_format với reversed parameter order.
        
        Args:
            token: Token to validate
            platform: Git platform
            
        Returns:
            True if format is valid
        """
        return self.validate_pat_format(platform, token)
    
    def get_platform_pat_url(self, platform: str) -> str:
        """
        Get URL for creating PAT on different platforms.
        
        Args:
            platform: Git platform
            
        Returns:
            URL for PAT creation
        """
        urls = {
            'github': 'https://github.com/settings/tokens',
            'gitlab': 'https://gitlab.com/-/profile/personal_access_tokens',
            'bitbucket': 'https://bitbucket.org/account/settings/app-passwords/'
        }
        
        return urls.get(platform.lower(), 'https://docs.git-scm.com/book/en/v2/Git-Tools-Credential-Storage')
    
    def clear_session_pats(self) -> None:
        """Clear all PATs from current session."""
        count = len(self.stored_pats)
        self.stored_pats.clear()
        logger.info(f"Cleared {count} PATs from session")
    
    def get_stored_pat_info(self) -> List[Dict[str, Any]]:
        """
        Get information about stored PATs (without tokens).
        
        Returns:
            List of PAT information dictionaries
        """
        return [
            {
                'platform': pat_info.platform,
                'username': pat_info.username,
                'token_hash': pat_info.token_hash[:8] + '...',
                'created_at': pat_info.created_at,
                'last_used': pat_info.last_used
            }
            for pat_info in self.stored_pats.values()
        ]
    
    def _generate_session_key(self) -> bytes:
        """Generate a random session encryption key."""
        return Fernet.generate_key()
    
    def _create_token_hash(self, token: str, session_id: str) -> str:
        """Create SHA256 hash of token with session ID salt."""
        combined = f"{token}_{session_id}_{secrets.token_hex(16)}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat() 