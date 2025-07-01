"""
CodeFetcherAgent - Agent để fetch code và PR diffs từ Git repositories
Sử dụng GitPython để clone, fetch, và analyze Pull Request changes
"""

import os
import tempfile
import shutil
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from urllib.parse import urlparse
import re

import git
from git import Repo, GitCommandError, InvalidGitRepositoryError
from git.exc import GitError


class CodeFetcherAgent:
    """
    Agent để fetch code từ Git repositories và analyze PR diffs
    
    Hỗ trợ:
    - Clone repositories từ GitHub, GitLab, Bitbucket
    - Fetch PR/MR diffs
    - Handle Git errors gracefully
    - Temporary workspace management
    """
    
    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Initialize CodeFetcherAgent
        
        Args:
            workspace_dir: Directory để store cloned repos. Nếu None, sử dụng temp directory
        """
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="codefetcher_")
        self.logger = logging.getLogger(__name__)
        
        # Ensure workspace directory exists
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)
        
        # Track cloned repositories
        self.cloned_repos: Dict[str, Repo] = {}
        
        self.logger.info(f"CodeFetcherAgent initialized với workspace: {self.workspace_dir}")
    
    def __del__(self):
        """Cleanup workspace khi agent bị destroyed"""
        self.cleanup()
    
    def cleanup(self):
        """Clean up cloned repositories và temporary files"""
        try:
            # Close all repo connections
            for repo in self.cloned_repos.values():
                if hasattr(repo, 'close'):
                    repo.close()
            
            # Remove workspace if it's a temp directory
            if self.workspace_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
                self.logger.info(f"Cleaned up workspace: {self.workspace_dir}")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
    
    def _parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """
        Parse repository URL để extract platform, owner, repo name
        
        Args:
            repo_url: Repository URL (GitHub, GitLab, Bitbucket)
            
        Returns:
            Dict với platform, owner, repo_name
            
        Raises:
            ValueError: Nếu URL format không hợp lệ
        """
        # Clean URL
        clean_url = repo_url.rstrip('/').replace('.git', '')
        
        # Parse URL
        parsed = urlparse(clean_url)
        if not parsed.netloc or not parsed.path or parsed.scheme != 'https':
            raise ValueError(f"Invalid repository URL: {repo_url}")
        
        # Extract platform
        platform_map = {
            'github.com': 'github',
            'gitlab.com': 'gitlab', 
            'bitbucket.org': 'bitbucket'
        }
        
        platform = platform_map.get(parsed.netloc.lower())
        if not platform:
            raise ValueError(f"Unsupported platform: {parsed.netloc}")
        
        # Extract owner và repo name
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) < 2:
            raise ValueError(f"Invalid repository path: {parsed.path}")
        
        owner = path_parts[0]
        repo_name = path_parts[1]
        
        return {
            'platform': platform,
            'owner': owner,
            'repo_name': repo_name,
            'full_name': f"{owner}/{repo_name}",
            'clone_url': f"https://{parsed.netloc}/{owner}/{repo_name}.git"
        }
    
    def _get_repo_local_path(self, repo_info: Dict[str, str]) -> str:
        """Get local path cho cloned repository"""
        return os.path.join(self.workspace_dir, f"{repo_info['platform']}_{repo_info['full_name'].replace('/', '_')}")
    
    def clone_repository(self, repo_url: str, force_refresh: bool = False) -> Repo:
        """
        Clone repository nếu chưa có, hoặc fetch updates
        
        Args:
            repo_url: Repository URL
            force_refresh: Force re-clone nếu repo đã tồn tại
            
        Returns:
            GitPython Repo object
            
        Raises:
            GitError: Nếu có lỗi Git operations
            ValueError: Nếu URL không hợp lệ
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            local_path = self._get_repo_local_path(repo_info)
            repo_key = repo_info['full_name']
            
            # Check if already cloned
            if repo_key in self.cloned_repos and not force_refresh:
                repo = self.cloned_repos[repo_key]
                try:
                    # Try to fetch latest changes
                    self.logger.info(f"Fetching updates cho {repo_key}")
                    repo.remotes.origin.fetch()
                    return repo
                except GitCommandError as e:
                    self.logger.warning(f"Failed to fetch updates: {e}")
                    # Continue với existing repo
                    return repo
            
            # Remove existing directory nếu force_refresh
            if force_refresh and os.path.exists(local_path):
                shutil.rmtree(local_path)
                if repo_key in self.cloned_repos:
                    del self.cloned_repos[repo_key]
            
            # Clone repository
            if not os.path.exists(local_path):
                self.logger.info(f"Cloning {repo_info['clone_url']} to {local_path}")
                repo = Repo.clone_from(
                    repo_info['clone_url'],
                    local_path,
                    depth=1  # Shallow clone để faster performance
                )
            else:
                # Open existing repository
                repo = Repo(local_path)
            
            self.cloned_repos[repo_key] = repo
            self.logger.info(f"Successfully cloned/opened {repo_key}")
            return repo
            
        except GitCommandError as e:
            error_msg = f"Git command failed: {e}"
            self.logger.error(error_msg)
            raise GitError(error_msg) from e
        except InvalidGitRepositoryError as e:
            error_msg = f"Invalid Git repository: {e}"
            self.logger.error(error_msg)
            raise GitError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to clone repository {repo_url}: {e}"
            self.logger.error(error_msg)
            raise GitError(error_msg) from e
    
    def get_pr_diff(self, repo_url: str, pr_id: int, context_lines: int = 3) -> Dict[str, Any]:
        """
        Get diff cho một Pull Request
        
        Args:
            repo_url: Repository URL
            pr_id: Pull Request ID
            context_lines: Number of context lines trong diff
            
        Returns:
            Dict chứa PR diff information:
            {
                'pr_id': int,
                'repo_url': str,
                'diff': str,
                'files_changed': List[str],
                'stats': Dict[str, int],
                'commits': List[Dict],
                'error': Optional[str]
            }
        """
        result = {
            'pr_id': pr_id,
            'repo_url': repo_url,
            'diff': '',
            'files_changed': [],
            'stats': {'additions': 0, 'deletions': 0, 'files': 0},
            'commits': [],
            'error': None
        }
        
        try:
            repo_info = self._parse_repo_url(repo_url)
            repo = self.clone_repository(repo_url)
            
            # Fetch PR refs (GitHub style)
            pr_ref = f"pull/{pr_id}/head"
            
            try:
                # Try to fetch PR reference
                self.logger.info(f"Fetching PR {pr_id} reference")
                repo.remotes.origin.fetch(f"+refs/{pr_ref}:refs/remotes/origin/{pr_ref}")
                
                # Get PR commit
                pr_commit = repo.commit(f"origin/{pr_ref}")
                
                # Get base commit (usually main/master)
                base_branches = ['main', 'master', 'develop']
                base_commit = None
                
                for branch in base_branches:
                    try:
                        base_commit = repo.commit(f"origin/{branch}")
                        break
                    except:
                        continue
                
                if not base_commit:
                    # Fallback to parent commit
                    if pr_commit.parents:
                        base_commit = pr_commit.parents[0]
                    else:
                        raise GitError("Cannot find base commit for comparison")
                
                # Generate diff
                diff = base_commit.diff(pr_commit, create_patch=True)
                
                # Process diff
                diff_text = ""
                files_changed = []
                total_additions = 0
                total_deletions = 0
                
                for diff_item in diff:
                    if diff_item.a_path:
                        files_changed.append(diff_item.a_path)
                    elif diff_item.b_path:
                        files_changed.append(diff_item.b_path)
                    
                    # Add diff text
                    if hasattr(diff_item, 'diff') and diff_item.diff:
                        diff_text += diff_item.diff.decode('utf-8', errors='ignore') + "\n"
                
                # Get commit information
                commits = []
                for commit in repo.iter_commits(f"{base_commit}..{pr_commit}"):
                    commits.append({
                        'sha': commit.hexsha[:8],
                        'message': commit.message.strip(),
                        'author': str(commit.author),
                        'date': commit.committed_datetime.isoformat()
                    })
                
                # Update result
                result.update({
                    'diff': diff_text,
                    'files_changed': list(set(files_changed)),
                    'stats': {
                        'additions': len([l for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++')]),
                        'deletions': len([l for l in diff_text.split('\n') if l.startswith('-') and not l.startswith('---')]),
                        'files': len(files_changed)
                    },
                    'commits': commits
                })
                
                self.logger.info(f"Successfully fetched PR {pr_id} diff: {len(files_changed)} files changed")
                
            except GitCommandError as e:
                # Try alternative approach for GitLab/Bitbucket
                if repo_info['platform'] in ['gitlab', 'bitbucket']:
                    result['error'] = f"PR diff not available for {repo_info['platform']} (API access required)"
                else:
                    result['error'] = f"Failed to fetch PR {pr_id}: {e}"
                self.logger.warning(result['error'])
            
        except Exception as e:
            error_msg = f"Error getting PR diff: {e}"
            result['error'] = error_msg
            self.logger.error(error_msg)
        
        return result
    
    def get_file_content(self, repo_url: str, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """
        Get content của một file từ repository
        
        Args:
            repo_url: Repository URL
            file_path: Path to file trong repository
            ref: Git reference (branch, commit, tag)
            
        Returns:
            File content as string, hoặc None nếu file không tồn tại
        """
        try:
            repo = self.clone_repository(repo_url)
            
            # Get file content at specific ref
            try:
                blob = repo.commit(ref).tree[file_path]
                return blob.data_stream.read().decode('utf-8', errors='ignore')
            except KeyError:
                self.logger.warning(f"File {file_path} not found at {ref}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error getting file content: {e}")
            return None
    
    def list_repository_files(self, repo_url: str, path: str = "", ref: str = "HEAD") -> List[str]:
        """
        List files trong repository
        
        Args:
            repo_url: Repository URL
            path: Directory path (empty for root)
            ref: Git reference
            
        Returns:
            List of file paths
        """
        try:
            repo = self.clone_repository(repo_url)
            
            tree = repo.commit(ref).tree
            if path:
                tree = tree[path]
            
            files = []
            for item in tree.traverse():
                if item.type == 'blob':  # File
                    files.append(item.path)
            
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Error listing repository files: {e}")
            return []
    
    def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """
        Get basic repository information
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Dict với repository information
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            repo = self.clone_repository(repo_url)
            
            # Get latest commit
            latest_commit = repo.head.commit
            
            # Get branches
            branches = [ref.name.split('/')[-1] for ref in repo.remote().refs]
            
            # Get tags
            tags = [tag.name for tag in repo.tags]
            
            return {
                'platform': repo_info['platform'],
                'owner': repo_info['owner'],
                'repo_name': repo_info['repo_name'],
                'full_name': repo_info['full_name'],
                'clone_url': repo_info['clone_url'],
                'latest_commit': {
                    'sha': latest_commit.hexsha[:8],
                    'message': latest_commit.message.strip(),
                    'author': str(latest_commit.author),
                    'date': latest_commit.committed_datetime.isoformat()
                },
                'branches': branches[:10],  # Limit to first 10
                'tags': tags[-10:],  # Last 10 tags
                'local_path': self._get_repo_local_path(repo_info)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting repository info: {e}")
            return {'error': str(e)}


# Utility functions
def validate_git_url(url: str) -> bool:
    """
    Validate nếu URL là valid Git repository URL
    
    Args:
        url: Repository URL
        
    Returns:
        True nếu valid, False otherwise
    """
    try:
        agent = CodeFetcherAgent()
        agent._parse_repo_url(url)
        agent.cleanup()  # Cleanup temp directory
        return True
    except:
        return False


def extract_pr_number_from_url(pr_url: str) -> Optional[int]:
    """
    Extract PR number từ PR URL
    
    Args:
        pr_url: Pull Request URL
        
    Returns:
        PR number hoặc None nếu không tìm thấy
    """
    # Pattern for GitHub PR URLs
    patterns = [
        r'/pull/(\d+)',
        r'/merge_requests/(\d+)',  # GitLab
        r'/pullrequests/(\d+)',    # Bitbucket
    ]
    
    for pattern in patterns:
        match = re.search(pattern, pr_url)
        if match:
            return int(match.group(1))
    
    return None


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    agent = CodeFetcherAgent()
    
    # Test với public repository
    test_repo = "https://github.com/octocat/Hello-World"
    
    try:
        # Get repository info
        info = agent.get_repository_info(test_repo)
        print(f"Repository info: {info}")
        
        # List files
        files = agent.list_repository_files(test_repo)
        print(f"Files: {files[:5]}")  # First 5 files
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        agent.cleanup() 