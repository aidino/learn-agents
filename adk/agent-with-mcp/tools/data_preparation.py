"""
Data Preparation Agent for Data Acquisition Team.

Prepares comprehensive project context data after repository cloning 
and language identification for downstream analysis.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from loguru import logger

from .git_operations import RepositoryInfo
from .language_identifier import ProjectLanguageProfile, LanguageInfo


@dataclass
class FileInfo:
    """Information about a single file in the project."""
    path: str
    relative_path: str
    size_bytes: int
    lines: int
    language: str
    last_modified: datetime
    is_test_file: bool = False
    is_config_file: bool = False


@dataclass
class DirectoryStructure:
    """
    Project directory structure information.
    
    Contains comprehensive statistics about project directory layout,
    file organization, và structural patterns.
    
    Attributes:
        total_directories (int): Total number of directories in project.
        total_files (int): Total number of files in project.
        max_depth (int): Maximum depth of directory nesting.
        common_directories (List[str]): Common directory names found (src, tests, docs, etc.).
        ignored_directories (List[str]): Directories ignored during analysis (.git, __pycache__, etc.).
    """
    total_directories: int
    total_files: int
    max_depth: int
    common_directories: List[str]
    ignored_directories: List[str]


@dataclass
class ProjectMetadata:
    """
    Project metadata extracted from configuration files.
    
    Aggregates metadata từ various project configuration files như
    pyproject.toml, setup.py, package.json, requirements.txt, etc.
    
    Attributes:
        name (str): Project name.
        version (Optional[str]): Project version string.
        description (Optional[str]): Project description.
        author (Optional[str]): Project author information.
        license (Optional[str]): Project license identifier.
        dependencies (Dict[str, List[str]]): Dependencies by category (dev, prod, test).
        scripts (Dict[str, str]): Available scripts and commands.
        keywords (List[str]): Project keywords and tags.
        
    Example:
        >>> metadata = ProjectMetadata(
        ...     name="my-project",
        ...     version="1.0.0",
        ...     dependencies={"prod": ["requests", "click"], "dev": ["pytest"]}
        ... )
    """
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    dependencies: Dict[str, List[str]] = None
    scripts: Dict[str, str] = None
    keywords: List[str] = None


@dataclass
class ProjectDataContext:
    """Complete project data context for analysis."""
    repository_info: RepositoryInfo
    language_profile: ProjectLanguageProfile
    project_metadata: ProjectMetadata
    directory_structure: DirectoryStructure
    files: List[FileInfo]
    analysis_timestamp: datetime
    preparation_config: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def save_to_file(self, file_path: str) -> None:
        """Save context to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


class DataPreparationAgent:
    """Agent responsible for preparing comprehensive project data context."""
    
    def __init__(self, 
                 include_test_files: bool = True,
                 max_file_size_mb: float = 1.0,
                 exclude_extensions: Optional[List[str]] = None):
        """
        Initialize Data Preparation Agent.
        
        Args:
            include_test_files: Whether to include test files in analysis
            max_file_size_mb: Maximum file size to analyze (in MB)
            exclude_extensions: File extensions to exclude from analysis
        """
        self.include_test_files = include_test_files
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self.exclude_extensions = exclude_extensions or [
            '.pyc', '.pyo', '.class', '.jar', '.war', '.ear',
            '.exe', '.dll', '.so', '.dylib',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wav',
            '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z'
        ]
        
        self.test_file_patterns = [
            'test_', '_test', 'tests/', '/test/', 'spec_', '_spec',
            '.test.', '.spec.', 'unittest', 'pytest'
        ]
        
        self.config_file_patterns = [
            'config', 'settings', '.env', 'dockerfile', 'makefile',
            'requirements', 'package.json', 'pom.xml', 'build.gradle',
            'pyproject.toml', 'setup.py', 'setup.cfg'
        ]
        
        self.common_ignore_dirs = {
            '.git', '.svn', '.hg',
            '__pycache__', '.pytest_cache',
            'node_modules', 'npm_modules',
            'venv', 'env', '.venv', '.env',
            'build', 'dist', 'target', 'out',
            '.idea', '.vscode', '.vs',
            'bin', 'obj', 'debug', 'release'
        }
    
    def prepare_project_context(self, 
                               repo_info: RepositoryInfo,
                               language_profile: ProjectLanguageProfile,
                               additional_config: Optional[Dict[str, Any]] = None) -> ProjectDataContext:
        """
        Prepare comprehensive project data context.
        
        Args:
            repo_info: Repository information from GitOperationsAgent
            language_profile: Language profile from LanguageIdentifierAgent
            additional_config: Additional configuration parameters
            
        Returns:
            ProjectDataContext with complete project analysis
        """
        logger.info(f"Preparing project context for: {repo_info.local_path}")
        
        if not os.path.exists(repo_info.local_path):
            raise FileNotFoundError(f"Repository path does not exist: {repo_info.local_path}")
        
        # Extract project metadata
        project_metadata = self._extract_project_metadata(repo_info.local_path, language_profile)
        
        # Analyze directory structure
        directory_structure = self._analyze_directory_structure(repo_info.local_path)
        
        # Analyze files
        files = self._analyze_files(repo_info.local_path, language_profile)
        
        # Create preparation config
        prep_config = {
            'include_test_files': self.include_test_files,
            'max_file_size_mb': self.max_file_size_bytes / (1024 * 1024),
            'exclude_extensions': self.exclude_extensions,
            'total_files_analyzed': len(files),
            'analysis_scope': additional_config.get('scope', 'full') if additional_config else 'full'
        }
        
        # Merge additional config
        if additional_config:
            prep_config.update(additional_config)
        
        context = ProjectDataContext(
            repository_info=repo_info,
            language_profile=language_profile,
            project_metadata=project_metadata,
            directory_structure=directory_structure,
            files=files,
            analysis_timestamp=datetime.now(),
            preparation_config=prep_config
        )
        
        logger.success(f"Project context prepared successfully. "
                      f"Analyzed {len(files)} files in {repo_info.local_path}")
        
        return context
    
    def _extract_project_metadata(self, path: str, language_profile: ProjectLanguageProfile) -> ProjectMetadata:
        """Extract project metadata from configuration files."""
        metadata = ProjectMetadata(
            name=os.path.basename(path),
            dependencies={}
        )
        
        # Extract from different config files based on primary language
        primary_lang = language_profile.primary_language.lower()
        
        try:
            if primary_lang == 'python':
                metadata = self._extract_python_metadata(path, metadata)
            elif primary_lang in ['javascript', 'typescript']:
                metadata = self._extract_javascript_metadata(path, metadata)
            elif primary_lang == 'java':
                metadata = self._extract_java_metadata(path, metadata)
            elif primary_lang == 'dart':
                metadata = self._extract_dart_metadata(path, metadata)
        except Exception as e:
            logger.warning(f"Could not extract complete metadata: {e}")
        
        return metadata
    
    def _extract_python_metadata(self, path: str, metadata: ProjectMetadata) -> ProjectMetadata:
        """Extract metadata from Python project files."""
        # Check pyproject.toml
        pyproject_path = os.path.join(path, 'pyproject.toml')
        if os.path.exists(pyproject_path):
            try:
                import tomli
                with open(pyproject_path, 'rb') as f:
                    data = tomli.load(f)
                
                project_info = data.get('project', {})
                metadata.name = project_info.get('name', metadata.name)
                metadata.version = project_info.get('version')
                metadata.description = project_info.get('description')
                metadata.author = ', '.join(project_info.get('authors', []))
                metadata.license = project_info.get('license', {}).get('text')
                metadata.keywords = project_info.get('keywords', [])
                
                if 'dependencies' in project_info:
                    metadata.dependencies['runtime'] = project_info['dependencies']
            except Exception as e:
                logger.warning(f"Could not parse pyproject.toml: {e}")
        
        # Check setup.py for additional info
        setup_path = os.path.join(path, 'setup.py')
        if os.path.exists(setup_path):
            try:
                with open(setup_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic extraction from setup.py (simplified)
                    if 'name=' in content and not metadata.name:
                        # This is a very basic parser - could be enhanced
                        pass
            except Exception as e:
                logger.warning(f"Could not parse setup.py: {e}")
        
        # Check requirements.txt
        req_path = os.path.join(path, 'requirements.txt')
        if os.path.exists(req_path):
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    requirements = [line.strip() for line in f 
                                  if line.strip() and not line.startswith('#')]
                metadata.dependencies['requirements'] = requirements
            except Exception as e:
                logger.warning(f"Could not parse requirements.txt: {e}")
        
        return metadata
    
    def _extract_javascript_metadata(self, path: str, metadata: ProjectMetadata) -> ProjectMetadata:
        """Extract metadata from JavaScript/TypeScript project files."""
        package_path = os.path.join(path, 'package.json')
        if os.path.exists(package_path):
            try:
                with open(package_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                metadata.name = data.get('name', metadata.name)
                metadata.version = data.get('version')
                metadata.description = data.get('description')
                metadata.author = data.get('author')
                metadata.license = data.get('license')
                metadata.keywords = data.get('keywords', [])
                
                if 'dependencies' in data:
                    metadata.dependencies['dependencies'] = list(data['dependencies'].keys())
                if 'devDependencies' in data:
                    metadata.dependencies['devDependencies'] = list(data['devDependencies'].keys())
                if 'scripts' in data:
                    metadata.scripts = data['scripts']
                    
            except Exception as e:
                logger.warning(f"Could not parse package.json: {e}")
        
        return metadata
    
    def _extract_java_metadata(self, path: str, metadata: ProjectMetadata) -> ProjectMetadata:
        """Extract metadata from Java project files."""
        # Check Maven pom.xml
        pom_path = os.path.join(path, 'pom.xml')
        if os.path.exists(pom_path):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(pom_path)
                root = tree.getroot()
                
                # Remove namespace for easier parsing
                for elem in root.iter():
                    if '}' in elem.tag:
                        elem.tag = elem.tag.split('}')[1]
                
                metadata.name = self._get_xml_text(root, 'artifactId') or metadata.name
                metadata.version = self._get_xml_text(root, 'version')
                metadata.description = self._get_xml_text(root, 'description')
                
                # Extract dependencies
                dependencies = root.find('dependencies')
                if dependencies is not None:
                    deps = []
                    for dep in dependencies.findall('dependency'):
                        group_id = self._get_xml_text(dep, 'groupId')
                        artifact_id = self._get_xml_text(dep, 'artifactId')
                        if group_id and artifact_id:
                            deps.append(f"{group_id}:{artifact_id}")
                    metadata.dependencies['maven'] = deps
                    
            except Exception as e:
                logger.warning(f"Could not parse pom.xml: {e}")
        
        # Check Gradle build.gradle
        gradle_path = os.path.join(path, 'build.gradle')
        if os.path.exists(gradle_path):
            try:
                with open(gradle_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Basic Gradle parsing (could be enhanced with proper parser)
                    if 'version' in content and not metadata.version:
                        # Extract version from Gradle file
                        pass
            except Exception as e:
                logger.warning(f"Could not parse build.gradle: {e}")
        
        return metadata
    
    def _extract_dart_metadata(self, path: str, metadata: ProjectMetadata) -> ProjectMetadata:
        """Extract metadata from Dart project files."""
        pubspec_path = os.path.join(path, 'pubspec.yaml')
        if os.path.exists(pubspec_path):
            try:
                import yaml
                with open(pubspec_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                metadata.name = data.get('name', metadata.name)
                metadata.version = data.get('version')
                metadata.description = data.get('description')
                metadata.author = data.get('author')
                
                if 'dependencies' in data:
                    metadata.dependencies['dependencies'] = list(data['dependencies'].keys())
                if 'dev_dependencies' in data:
                    metadata.dependencies['dev_dependencies'] = list(data['dev_dependencies'].keys())
                    
            except Exception as e:
                logger.warning(f"Could not parse pubspec.yaml: {e}")
        
        return metadata
    
    def _analyze_directory_structure(self, path: str) -> DirectoryStructure:
        """Analyze project directory structure."""
        total_dirs = 0
        total_files = 0
        max_depth = 0
        dir_names = set()
        ignored_dirs = []
        
        try:
            for root, dirs, files in os.walk(path):
                # Calculate depth
                relative_path = os.path.relpath(root, path)
                if relative_path != '.':
                    depth = len(relative_path.split(os.sep))
                    max_depth = max(max_depth, depth)
                
                total_dirs += len(dirs)
                total_files += len(files)
                
                # Collect directory names
                for d in dirs:
                    dir_names.add(d)
                    if d in self.common_ignore_dirs:
                        ignored_dirs.append(d)
                
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.common_ignore_dirs]
        
        except Exception as e:
            logger.warning(f"Error analyzing directory structure: {e}")
        
        # Get most common directory names
        common_dirs = sorted(list(dir_names))[:20]  # Top 20 most common
        
        return DirectoryStructure(
            total_directories=total_dirs,
            total_files=total_files,
            max_depth=max_depth,
            common_directories=common_dirs,
            ignored_directories=list(set(ignored_dirs))
        )
    
    def _analyze_files(self, path: str, language_profile: ProjectLanguageProfile) -> List[FileInfo]:
        """Analyze individual files in the project."""
        files = []
        
        try:
            for root, dirs, filenames in os.walk(path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in self.common_ignore_dirs]
                
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(file_path, path)
                    
                    # Skip files that are too large
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > self.max_file_size_bytes:
                            continue
                    except:
                        continue
                    
                    # Skip excluded extensions
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext in self.exclude_extensions:
                        continue
                    
                    # Determine language
                    file_language = self._determine_file_language(filename, language_profile)
                    
                    # Skip test files if not included
                    is_test = self._is_test_file(relative_path, filename)
                    if is_test and not self.include_test_files:
                        continue
                    
                    # Determine if config file
                    is_config = self._is_config_file(filename)
                    
                    # Count lines
                    line_count = self._count_file_lines(file_path)
                    
                    # Get last modified time
                    try:
                        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                    except:
                        last_modified = datetime.now()
                    
                    file_info = FileInfo(
                        path=file_path,
                        relative_path=relative_path,
                        size_bytes=file_size,
                        lines=line_count,
                        language=file_language,
                        last_modified=last_modified,
                        is_test_file=is_test,
                        is_config_file=is_config
                    )
                    files.append(file_info)
        
        except Exception as e:
            logger.error(f"Error analyzing files: {e}")
        
        return files
    
    def _determine_file_language(self, filename: str, language_profile: ProjectLanguageProfile) -> str:
        """Determine the programming language of a file."""
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Map extensions to languages from language profile
        for lang_info in language_profile.languages:
            # This is a simplified mapping - could use the same extension mapping as LanguageIdentifierAgent
            if lang_info.name == 'Python' and file_ext in ['.py', '.pyw', '.pyi']:
                return 'Python'
            elif lang_info.name == 'Java' and file_ext == '.java':
                return 'Java'
            elif lang_info.name == 'JavaScript' and file_ext in ['.js', '.jsx', '.mjs']:
                return 'JavaScript'
            elif lang_info.name == 'TypeScript' and file_ext in ['.ts', '.tsx']:
                return 'TypeScript'
            elif lang_info.name == 'Dart' and file_ext == '.dart':
                return 'Dart'
            # Add more mappings as needed
        
        # Default mapping for common files
        extension_map = {
            '.md': 'Markdown',
            '.txt': 'Text',
            '.json': 'JSON',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.xml': 'XML',
            '.html': 'HTML',
            '.css': 'CSS',
            '.sh': 'Shell'
        }
        
        return extension_map.get(file_ext, 'Unknown')
    
    def _is_test_file(self, relative_path: str, filename: str) -> bool:
        """Determine if a file is a test file."""
        path_lower = relative_path.lower()
        filename_lower = filename.lower()
        
        return any(pattern in path_lower or pattern in filename_lower 
                  for pattern in self.test_file_patterns)
    
    def _is_config_file(self, filename: str) -> bool:
        """Determine if a file is a configuration file."""
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in self.config_file_patterns)
    
    def _count_file_lines(self, file_path: str) -> int:
        """Count lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _get_xml_text(self, element, tag: str) -> Optional[str]:
        """Get text content from XML element."""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else None 