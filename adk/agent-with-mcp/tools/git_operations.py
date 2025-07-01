"""
Git Operations Agent for Data Acquisition Team.

Handles Git repository operations including cloning, branch management,
repository information extraction, and Pull Request analysis.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from loguru import logger
import json
import re
from datetime import datetime

import git
from git import Repo, GitCommandError

# GitHub/GitLab API imports
try:
    import requests
    from github import Github
    from gitlab import Gitlab
    GITHUB_AVAILABLE = True
    GITLAB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    GITLAB_AVAILABLE = False
    requests = None
    Github = None
    Gitlab = None

# Import debug logging
try:
    from src.core.logging import debug_trace, get_debug_logger
except ImportError:
    # Fallback for testing environment
    def debug_trace(func):
        return func
    
    class MockDebugLogger:
        def __init__(self):
            from loguru import logger
            self.logger = logger
            
        def log_step(self, message, data=None):
            self.logger.info(f"{message}: {data}")
            
        def log_error(self, error, data=None):
            self.logger.error(f"Error: {error} - {data}")
            
        def log_performance_metric(self, metric, value, unit):
            self.logger.info(f"Performance: {metric}={value}{unit}")
            
        def log_data(self, stage, data):
            self.logger.info(f"Data [{stage}]: {data}")
    
    def get_debug_logger():
        return MockDebugLogger()


@dataclass
class RepositoryInfo:
    """Repository information extracted from Git operations."""
    url: str
    local_path: str
    default_branch: str
    commit_hash: str
    author: str
    commit_message: str
    languages: List[str]
    size_mb: float
    file_count: int


@dataclass
class PullRequestInfo:
    """Pull Request information with metadata and diff."""
    
    # Basic PR info
    pr_id: str
    title: str
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    status: str  # open, closed, merged
    
    # Branch information
    source_branch: str
    target_branch: str
    base_commit: str
    head_commit: str
    
    # Changes information
    diff_text: str
    changed_files: List[str]
    files_added: List[str]
    files_modified: List[str]
    files_deleted: List[str]
    
    # Statistics
    additions: int
    deletions: int
    changed_lines: int
    
    # Platform-specific metadata
    platform: str  # github, gitlab, etc.
    web_url: str
    api_url: str
    labels: List[str]
    assignees: List[str]
    reviewers: List[str]
    
    # Additional metadata
    metadata: Dict[str, Any]


class GitOperationsAgent:
    """Agent responsible for Git repository operations and PR analysis."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize Git Operations Agent.
        
        Args:
            temp_dir: Temporary directory for cloning repos. If None, uses system temp.
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.base_clone_dir = Path(self.temp_dir) / "ai_codescan_repos"
        self.base_clone_dir.mkdir(exist_ok=True)
        
        # Setup debug logger reference
        self._debug_logger = get_debug_logger()
        
        # Log agent initialization
        self._debug_logger.log_step("GitOperationsAgent initialized", {
            "temp_dir": str(self.temp_dir),
            "base_clone_dir": str(self.base_clone_dir),
            "github_available": GITHUB_AVAILABLE,
            "gitlab_available": GITLAB_AVAILABLE
        })
        
    @debug_trace
    def clone_repository(
        self, 
        repo_url: str, 
        local_path: Optional[str] = None,
        depth: int = 1,
        branch: Optional[str] = None,
        pat: Optional[str] = None
    ) -> RepositoryInfo:
        """
        Clone a Git repository to local path.
        
        Args:
            repo_url: URL of the repository to clone
            local_path: Local path to clone to. If None, auto-generates path
            depth: Clone depth (default 1 for shallow clone)
            branch: Specific branch to clone
            pat: Personal Access Token for private repos
            
        Returns:
            RepositoryInfo object with repository details
            
        Raises:
            GitCommandError: If clone operation fails
            ValueError: If repository URL is invalid
        """
        self._debug_logger.log_step("Starting repository clone", {
            "repo_url": repo_url,
            "depth": depth,
            "branch": branch,
            "has_pat": bool(pat)
        })
        
        # Validate repository URL
        if not self._is_valid_git_url(repo_url):
            error_msg = f"Invalid Git repository URL: {repo_url}"
            self._debug_logger.log_error(ValueError(error_msg), {"repo_url": repo_url})
            raise ValueError(error_msg)
        
        # Generate local path if not provided
        if local_path is None:
            repo_name = self._extract_repo_name(repo_url)
            local_path = str(self.base_clone_dir / repo_name)
            self._debug_logger.log_step("Generated local path", {
                "repo_name": repo_name,
                "local_path": local_path
            })
        
        # Clean existing directory if it exists
        if os.path.exists(local_path):
            self._debug_logger.log_step("Cleaning existing directory", {"path": local_path})
            shutil.rmtree(local_path)
        
        try:
            # Prepare clone arguments
            clone_kwargs = {
                'depth': depth,
                'single_branch': True
            }
            
            # Add branch if specified
            if branch:
                clone_kwargs['branch'] = branch
                self._debug_logger.log_step("Using specific branch", {"branch": branch})
            
            # Add authentication if PAT provided
            auth_url = repo_url
            if pat:
                auth_url = self._add_auth_to_url(repo_url, pat)
                self._debug_logger.log_step("Added authentication to URL", {"has_auth": True})
            
            # Performance tracking
            import time
            clone_start_time = time.time()
            
            # Clone repository
            self._debug_logger.log_step("Executing git clone", {
                "target_path": local_path,
                "clone_args": {k: v for k, v in clone_kwargs.items() if k != 'branch'}
            })
            
            repo = Repo.clone_from(auth_url, local_path, **clone_kwargs)
            
            clone_duration = time.time() - clone_start_time
            self._debug_logger.log_performance_metric("git_clone_duration", clone_duration, "seconds")
            
            # Extract repository information
            repo_info = self._extract_repository_info(repo, repo_url, local_path)
            
            self._debug_logger.log_step("Repository clone completed successfully", {
                "local_path": local_path,
                "duration": f"{clone_duration:.2f}s",
                "repo_info": {
                    "commit_hash": repo_info.commit_hash,
                    "size_mb": repo_info.size_mb,
                    "file_count": repo_info.file_count,
                    "languages": repo_info.languages
                }
            })
            
            return repo_info
            
        except GitCommandError as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "local_path": local_path,
                "clone_kwargs": clone_kwargs
            })
            
            # Clean up failed clone attempt
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
                self._debug_logger.log_step("Cleaned up failed clone", {"path": local_path})
            raise
        except Exception as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "local_path": local_path,
                "operation": "clone_repository"
            })
            
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
            raise
    
    @debug_trace
    def get_repository_info(self, local_path: str) -> RepositoryInfo:
        """
        Get information about an existing local repository.
        
        Args:
            local_path: Path to local repository
            
        Returns:
            RepositoryInfo object
        """
        self._debug_logger.log_step("Getting repository info", {"local_path": local_path})
        
        if not os.path.exists(local_path):
            error_msg = f"Repository path does not exist: {local_path}"
            self._debug_logger.log_error(FileNotFoundError(error_msg), {"path": local_path})
            raise FileNotFoundError(error_msg)
        
        try:
            repo = Repo(local_path)
            # Get original URL from remote
            remote_url = repo.remotes.origin.url if repo.remotes else "unknown"
            
            repo_info = self._extract_repository_info(repo, remote_url, local_path)
            
            self._debug_logger.log_step("Repository info extracted", {
                "remote_url": remote_url,
                "info": {
                    "commit_hash": repo_info.commit_hash,
                    "size_mb": repo_info.size_mb,
                    "file_count": repo_info.file_count
                }
            })
            
            return repo_info
        except Exception as e:
            self._debug_logger.log_error(e, {"local_path": local_path, "operation": "get_repository_info"})
            raise
    
    @debug_trace
    def cleanup_repository(self, local_path: str) -> bool:
        """
        Clean up cloned repository by removing local directory.
        
        Args:
            local_path: Path to the repository directory to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        self._debug_logger.log_step("Cleaning up repository", {"path": local_path})
        
        try:
            if os.path.exists(local_path):
                shutil.rmtree(local_path)
                self._debug_logger.log_step("Repository cleanup successful", {"path": local_path})
                return True
            else:
                self._debug_logger.log_step("Repository path not found", {"path": local_path})
                return True  # Already clean
        except Exception as e:
            self._debug_logger.log_error(e, {"operation": "cleanup", "path": local_path})
            return False

    @debug_trace
    def is_valid_repository_url(self, url: str) -> bool:
        """
        Public method to validate repository URL.
        
        Args:
            url: Repository URL to validate
            
        Returns:
            True if URL is valid Git repository URL
        """
        return self._is_valid_git_url(url)
    
    def _is_valid_git_url(self, url: str) -> bool:
        """Validate if URL is a valid Git repository URL."""
        try:
            parsed = urlparse(url)
            # Check for common Git hosting patterns
            valid_patterns = [
                'github.com',
                'gitlab.com',
                'bitbucket.org',
                '.git'
            ]
            is_valid = any(pattern in url.lower() for pattern in valid_patterns)
            
            self._debug_logger.log_step("URL validation", {
                "url": url,
                "is_valid": is_valid,
                "matched_patterns": [p for p in valid_patterns if p in url.lower()]
            })
            
            return is_valid
        except Exception as e:
            self._debug_logger.log_error(e, {"url": url, "operation": "url_validation"})
            return False
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        
        # Remove .git suffix if present
        if path.endswith('.git'):
            path = path[:-4]
        
        # Get last part of path (repo name)
        repo_name = path.split('/')[-1] if '/' in path else path
        
        self._debug_logger.log_step("Extracted repository name", {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "parsed_path": path
        })
        
        return repo_name
    
    def _add_auth_to_url(self, url: str, pat: str) -> str:
        """Add PAT authentication to repository URL."""
        parsed = urlparse(url)
        
        # For GitHub, GitLab, etc., use token in URL
        if 'github.com' in url:
            auth_url = url.replace('https://', f'https://{pat}@')
        elif 'gitlab.com' in url:
            auth_url = url.replace('https://', f'https://oauth2:{pat}@')
        else:
            auth_url = url.replace('https://', f'https://{pat}@')
        
        self._debug_logger.log_step("Added authentication to URL", {
            "original_domain": parsed.netloc,
            "auth_added": True
        })
        
        return auth_url
    
    def _extract_repository_info(
        self, 
        repo: Repo, 
        repo_url: str, 
        local_path: str
    ) -> RepositoryInfo:
        """Extract comprehensive repository information."""
        self._debug_logger.log_step("Extracting repository information", {
            "repo_url": repo_url,
            "local_path": local_path
        })
        
        try:
            # Get basic repo info
            default_branch = repo.head.reference.name if repo.head.is_valid() else "main"
            commit = repo.head.commit
            commit_hash = commit.hexsha
            author = str(commit.author)
            commit_message = commit.message.strip()
            
            # Calculate repository metrics
            size_mb = self._calculate_repo_size(local_path)
            file_count = self._count_files(local_path)
            languages = self._detect_basic_languages(local_path)
            
            repo_info = RepositoryInfo(
                url=repo_url,
                local_path=local_path,
                default_branch=default_branch,
                commit_hash=commit_hash,
                author=author,
                commit_message=commit_message,
                languages=languages,
                size_mb=size_mb,
                file_count=file_count
            )
            
            self._debug_logger.log_data("repository_info", {
                "url": repo_url,
                "branch": default_branch,
                "commit_hash": commit_hash[:8],  # Short hash for logging
                "author": author,
                "size_mb": size_mb,
                "file_count": file_count,
                "languages": languages
            })
            
            # Log performance metrics
            self._debug_logger.log_performance_metric("repo_size_mb", size_mb, "MB")
            self._debug_logger.log_performance_metric("repo_file_count", file_count, "files")
            
            return repo_info
            
        except Exception as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "local_path": local_path,
                "operation": "extract_repository_info"
            })
            raise
    
    def _calculate_repo_size(self, path: str) -> float:
        """Calculate repository size in MB."""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            size_mb = total_size / (1024 * 1024)
            
            self._debug_logger.log_step("Calculated repository size", {
                "path": path,
                "total_bytes": total_size,
                "size_mb": round(size_mb, 2)
            })
            
            return size_mb
        except Exception as e:
            self._debug_logger.log_error(e, {"path": path, "operation": "calculate_repo_size"})
            return 0.0
    
    def _count_files(self, path: str) -> int:
        """Count total files in repository."""
        try:
            file_count = 0
            for root, dirs, files in os.walk(path):
                file_count += len(files)
            
            self._debug_logger.log_step("Counted repository files", {
                "path": path,
                "file_count": file_count
            })
            
            return file_count
        except Exception as e:
            self._debug_logger.log_error(e, {"path": path, "operation": "count_files"})
            return 0
    
    def _detect_basic_languages(self, path: str) -> List[str]:
        """Detect programming languages in repository."""
        try:
            language_extensions = {
                '.py': 'Python',
                '.js': 'JavaScript', 
                '.ts': 'TypeScript',
                '.java': 'Java',
                '.kt': 'Kotlin',
                '.dart': 'Dart',
                '.cpp': 'C++',
                '.c': 'C',
                '.cs': 'C#',
                '.php': 'PHP',
                '.rb': 'Ruby',
                '.go': 'Go',
                '.rs': 'Rust',
                '.swift': 'Swift'
            }
            
            detected_languages = set()
            
            for root, dirs, files in os.walk(path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in language_extensions:
                        detected_languages.add(language_extensions[ext])
            
            languages = list(detected_languages)
            
            self._debug_logger.log_step("Detected programming languages", {
                "path": path,
                "languages": languages,
                "total_languages": len(languages)
            })
            
            return languages
        except Exception as e:
            self._debug_logger.log_error(e, {"path": path, "operation": "detect_basic_languages"})
            return []
    
    # Pull Request Analysis Methods
    
    @debug_trace
    def get_pr_details(
        self, 
        repo_url: str, 
        pr_id: str, 
        pat: Optional[str] = None
    ) -> PullRequestInfo:
        """
        Fetch comprehensive Pull Request details from GitHub/GitLab.
        
        Args:
            repo_url: Repository URL
            pr_id: Pull Request ID/number
            pat: Personal Access Token for authentication
            
        Returns:
            PullRequestInfo object with PR details and diff
            
        Raises:
            ValueError: If platform not supported or PR not found
            Exception: If API call fails
        """
        self._debug_logger.log_step("Starting PR details fetch", {
            "repo_url": repo_url,
            "pr_id": pr_id,
            "has_pat": bool(pat)
        })
        
        try:
            # Determine platform
            platform = self._detect_platform(repo_url)
            
            if platform == "github":
                return self._fetch_github_pr(repo_url, pr_id, pat)
            elif platform == "gitlab":
                return self._fetch_gitlab_pr(repo_url, pr_id, pat)
            else:
                # Fallback to Git-based diff extraction
                return self._fetch_git_pr(repo_url, pr_id, pat)
                
        except Exception as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "pr_id": pr_id,
                "operation": "get_pr_details"
            })
            raise
    
    @debug_trace
    def _fetch_github_pr(
        self, 
        repo_url: str, 
        pr_id: str, 
        pat: Optional[str] = None
    ) -> PullRequestInfo:
        """Fetch PR details from GitHub API."""
        if not GITHUB_AVAILABLE:
            self._debug_logger.log_error(
                ImportError("PyGithub not available"), 
                {"fallback": "git_pr_fetch"}
            )
            return self._fetch_git_pr(repo_url, pr_id, pat)
        
        try:
            # Extract owner and repo from URL
            owner, repo_name = self._parse_github_url(repo_url)
            
            # Initialize GitHub API client
            github = Github(pat) if pat else Github()
            repo = github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(int(pr_id))
            
            self._debug_logger.log_step("Fetched GitHub PR", {
                "owner": owner,
                "repo": repo_name,
                "pr_number": pr_id,
                "pr_title": pr.title
            })
            
            # Get diff content
            diff_text = self._fetch_pr_diff_github(pr)
            
            # Parse changed files
            changed_files, files_added, files_modified, files_deleted = self._parse_pr_files(pr)
            
            # Create PullRequestInfo
            pr_info = PullRequestInfo(
                pr_id=str(pr.number),
                title=pr.title,
                description=pr.body or "",
                author=pr.user.login,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                status="merged" if pr.merged else ("closed" if pr.state == "closed" else "open"),
                
                source_branch=pr.head.ref,
                target_branch=pr.base.ref,
                base_commit=pr.base.sha,
                head_commit=pr.head.sha,
                
                diff_text=diff_text,
                changed_files=changed_files,
                files_added=files_added,
                files_modified=files_modified,
                files_deleted=files_deleted,
                
                additions=pr.additions,
                deletions=pr.deletions,
                changed_lines=pr.additions + pr.deletions,
                
                platform="github",
                web_url=pr.html_url,
                api_url=pr.url,
                labels=[label.name for label in pr.labels],
                assignees=[assignee.login for assignee in pr.assignees],
                reviewers=[review.user.login for review in pr.get_reviews() if review.user],
                
                metadata={
                    "mergeable": pr.mergeable,
                    "merged_by": pr.merged_by.login if pr.merged_by else None,
                    "comments": pr.comments,
                    "review_comments": pr.review_comments,
                    "commits": pr.commits
                }
            )
            
            return pr_info
            
        except Exception as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "pr_id": pr_id,
                "operation": "fetch_github_pr"
            })
            # Fallback to git-based approach
            return self._fetch_git_pr(repo_url, pr_id, pat)
    
    @debug_trace
    def _fetch_gitlab_pr(
        self, 
        repo_url: str, 
        pr_id: str, 
        pat: Optional[str] = None
    ) -> PullRequestInfo:
        """Fetch PR details from GitLab API."""
        if not GITLAB_AVAILABLE:
            self._debug_logger.log_error(
                ImportError("python-gitlab not available"), 
                {"fallback": "git_pr_fetch"}
            )
            return self._fetch_git_pr(repo_url, pr_id, pat)
        
        try:
            # Extract project path from URL
            project_path = self._parse_gitlab_url(repo_url)
            
            # Initialize GitLab API client
            gitlab = Gitlab("https://gitlab.com", private_token=pat) if pat else Gitlab("https://gitlab.com")
            project = gitlab.projects.get(project_path)
            mr = project.mergerequests.get(int(pr_id))
            
            self._debug_logger.log_step("Fetched GitLab MR", {
                "project_path": project_path,
                "mr_iid": pr_id,
                "mr_title": mr.title
            })
            
            # Get diff content
            diff_text = mr.changes().get('changes', '')
            
            # Create PullRequestInfo
            pr_info = PullRequestInfo(
                pr_id=str(mr.iid),
                title=mr.title,
                description=mr.description or "",
                author=mr.author.get('username', ''),
                created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(mr.updated_at.replace('Z', '+00:00')),
                status=mr.state,
                
                source_branch=mr.source_branch,
                target_branch=mr.target_branch,
                base_commit=mr.diff_refs.get('base_sha', ''),
                head_commit=mr.diff_refs.get('head_sha', ''),
                
                diff_text=str(diff_text),
                changed_files=mr.changes().get('changes', []),
                files_added=[],  # GitLab API doesn't easily provide this breakdown
                files_modified=[],
                files_deleted=[],
                
                additions=0,  # Not easily available in GitLab API
                deletions=0,
                changed_lines=0,
                
                platform="gitlab",
                web_url=mr.web_url,
                api_url=f"https://gitlab.com/api/v4/projects/{project.id}/merge_requests/{mr.iid}",
                labels=mr.labels,
                assignees=[assignee.get('username', '') for assignee in (mr.assignees or [])],
                reviewers=[],  # GitLab handles this differently
                
                metadata={
                    "mergeable": mr.merge_status == 'can_be_merged',
                    "work_in_progress": mr.work_in_progress,
                    "milestone": mr.milestone.get('title') if mr.milestone else None
                }
            )
            
            return pr_info
            
        except Exception as e:
            self._debug_logger.log_error(e, {
                "repo_url": repo_url,
                "pr_id": pr_id,
                "operation": "fetch_gitlab_pr"
            })
            # Fallback to git-based approach
            return self._fetch_git_pr(repo_url, pr_id, pat)
    
    @debug_trace
    def _fetch_git_pr(
        self, 
        repo_url: str, 
        pr_id: str, 
        pat: Optional[str] = None
    ) -> PullRequestInfo:
        """
        Fallback method to fetch PR using Git commands.
        
        This is a simplified approach that creates a basic PR info
        when API access is not available.
        """
        self._debug_logger.log_step("Using Git fallback for PR fetch", {
            "repo_url": repo_url,
            "pr_id": pr_id
        })
        
        # Create a basic PR info structure
        pr_info = PullRequestInfo(
            pr_id=pr_id,
            title=f"Pull Request #{pr_id}",
            description="PR details fetched via Git fallback",
            author="unknown",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status="unknown",
            
            source_branch="unknown",
            target_branch="main",
            base_commit="",
            head_commit="",
            
            diff_text="Diff not available via Git fallback",
            changed_files=[],
            files_added=[],
            files_modified=[],
            files_deleted=[],
            
            additions=0,
            deletions=0,
            changed_lines=0,
            
            platform="git_fallback",
            web_url=repo_url,
            api_url="",
            labels=[],
            assignees=[],
            reviewers=[],
            
            metadata={"fallback": True}
        )
        
        return pr_info
    
    # Helper methods for PR analysis
    
    def _detect_platform(self, repo_url: str) -> str:
        """Detect Git platform from repository URL."""
        if 'github.com' in repo_url.lower():
            return "github"
        elif 'gitlab.com' in repo_url.lower():
            return "gitlab"
        else:
            return "unknown"
    
    def _parse_github_url(self, repo_url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name."""
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1]
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            return owner, repo_name
        else:
            raise ValueError(f"Invalid GitHub URL format: {repo_url}")
    
    def _parse_gitlab_url(self, repo_url: str) -> str:
        """Parse GitLab URL to extract project path."""
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path
    
    def _fetch_pr_diff_github(self, pr) -> str:
        """Fetch PR diff content from GitHub PR object."""
        try:
            # Get diff via GitHub API
            diff_url = pr.diff_url
            headers = {'Accept': 'application/vnd.github.v3.diff'}
            
            if hasattr(pr._requester, '_Requester__authorizationHeader'):
                headers.update(pr._requester._Requester__authorizationHeader)
            
            response = requests.get(diff_url, headers=headers)
            response.raise_for_status()
            
            return response.text
        except Exception as e:
            self._debug_logger.log_error(e, {"operation": "fetch_pr_diff_github"})
            return f"Error fetching diff: {str(e)}"
    
    def _parse_pr_files(self, pr) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Parse PR files to categorize changes."""
        try:
            files = pr.get_files()
            
            changed_files = []
            files_added = []
            files_modified = []
            files_deleted = []
            
            for file in files:
                changed_files.append(file.filename)
                
                if file.status == 'added':
                    files_added.append(file.filename)
                elif file.status == 'modified':
                    files_modified.append(file.filename)
                elif file.status == 'removed':
                    files_deleted.append(file.filename)
            
            return changed_files, files_added, files_modified, files_deleted
            
        except Exception as e:
            self._debug_logger.log_error(e, {"operation": "parse_pr_files"})
            return [], [], [], [] 