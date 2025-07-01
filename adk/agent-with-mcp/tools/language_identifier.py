"""
Language Identifier Agent for Data Acquisition Team.

Identifies programming languages and frameworks used in repositories
with detailed analysis of project structure and configuration files.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import Counter
from loguru import logger


@dataclass
class LanguageInfo:
    """Information about a programming language in the repository."""
    name: str
    percentage: float
    file_count: int
    total_lines: int
    framework: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ProjectLanguageProfile:
    """Complete language profile of a project."""
    primary_language: str
    languages: List[LanguageInfo]
    frameworks: List[str]
    build_tools: List[str]
    package_managers: List[str]
    project_type: str  # web, mobile, desktop, library, etc.
    confidence_score: float  # 0.0 to 1.0


class LanguageIdentifierAgent:
    """Agent responsible for identifying programming languages and frameworks in repositories."""
    
    def __init__(self):
        """Initialize Language Identifier Agent."""
        self.language_extensions = {
            'Python': ['.py', '.pyw', '.pyi'],
            'Java': ['.java'],
            'JavaScript': ['.js', '.jsx', '.mjs'],
            'TypeScript': ['.ts', '.tsx'],
            'Dart': ['.dart'],
            'Kotlin': ['.kt', '.kts'],
            'C++': ['.cpp', '.cxx', '.cc', '.c++', '.hpp', '.hxx', '.h++'],
            'C': ['.c', '.h'],
            'C#': ['.cs'],
            'Go': ['.go'],
            'Rust': ['.rs'],
            'Ruby': ['.rb'],
            'PHP': ['.php'],
            'Swift': ['.swift'],
            'Objective-C': ['.m', '.mm', '.h'],
            'Shell': ['.sh', '.bash', '.zsh'],
            'HTML': ['.html', '.htm'],
            'CSS': ['.css', '.scss', '.sass', '.less'],
            'XML': ['.xml', '.xsd', '.xsl'],
            'JSON': ['.json'],
            'YAML': ['.yml', '.yaml'],
            'Markdown': ['.md', '.markdown'],
            'SQL': ['.sql']
        }
        
        self.config_files = {
            'Python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg', 
                      'Pipfile', 'poetry.lock', 'conda.yml', 'environment.yml'],
            'Java': ['pom.xml', 'build.gradle', 'gradle.properties', 'ivy.xml',
                    'ant.xml', 'build.xml'],
            'JavaScript': ['package.json', 'package-lock.json', 'yarn.lock', 
                          'webpack.config.js', 'babel.config.js', 'tsconfig.json'],
            'TypeScript': ['tsconfig.json', 'package.json', 'webpack.config.ts'],
            'Dart': ['pubspec.yaml', 'pubspec.lock', 'analysis_options.yaml'],
            'Kotlin': ['build.gradle.kts', 'settings.gradle.kts', 'pom.xml'],
            'C++': ['CMakeLists.txt', 'Makefile', 'configure.ac', 'meson.build'],
            'C': ['Makefile', 'CMakeLists.txt', 'configure.ac'],
            'C#': ['*.csproj', '*.sln', 'packages.config', 'project.json'],
            'Go': ['go.mod', 'go.sum', 'Gopkg.toml', 'Gopkg.lock'],
            'Rust': ['Cargo.toml', 'Cargo.lock'],
            'Ruby': ['Gemfile', 'Gemfile.lock', '.gemspec'],
            'PHP': ['composer.json', 'composer.lock'],
            'Swift': ['Package.swift', '*.xcodeproj', '*.xcworkspace']
        }
        
        self.framework_indicators = {
            'Python': {
                'Django': ['manage.py', 'settings.py', 'urls.py'],
                'Flask': ['app.py', 'wsgi.py'],
                'FastAPI': ['main.py'],
                'Streamlit': ['streamlit'],
                'Jupyter': ['.ipynb']
            },
            'JavaScript': {
                'React': ['react', 'jsx'],
                'Vue': ['vue'],
                'Angular': ['@angular'],
                'Node.js': ['express', 'node'],
                'Next.js': ['next']
            },
            'Java': {
                'Spring': ['spring', 'SpringApplication'],
                'Android': ['android', 'MainActivity'],
                'Maven': ['pom.xml'],
                'Gradle': ['build.gradle']
            },
            'Dart': {
                'Flutter': ['flutter', 'pubspec.yaml'],
                'Angular Dart': ['angular']
            }
        }
    
    def identify_language(self, local_path: str) -> ProjectLanguageProfile:
        """
        Identify programming languages and frameworks in the repository.
        
        Args:
            local_path: Path to the local repository
            
        Returns:
            ProjectLanguageProfile with detailed language analysis
        """
        logger.info(f"Analyzing languages in repository: {local_path}")
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Repository path does not exist: {local_path}")
        
        # Analyze file extensions and content
        language_stats = self._analyze_file_extensions(local_path)
        
        # Analyze configuration files
        config_analysis = self._analyze_config_files(local_path)
        
        # Detect frameworks
        frameworks = self._detect_frameworks(local_path, language_stats)
        
        # Determine project type
        project_type = self._determine_project_type(local_path, frameworks)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(language_stats, config_analysis)
        
        # Combine analysis results
        languages = self._create_language_info_list(language_stats)
        primary_language = languages[0].name if languages else "Unknown"
        
        # Extract build tools and package managers
        build_tools = self._extract_build_tools(config_analysis)
        package_managers = self._extract_package_managers(config_analysis)
        
        profile = ProjectLanguageProfile(
            primary_language=primary_language,
            languages=languages,
            frameworks=frameworks,
            build_tools=build_tools,
            package_managers=package_managers,
            project_type=project_type,
            confidence_score=confidence
        )
        
        logger.success(f"Language analysis completed. Primary language: {primary_language}")
        return profile
    
    def _analyze_file_extensions(self, path: str) -> Dict[str, Dict[str, int]]:
        """Analyze file extensions to determine language usage."""
        language_stats = {}
        
        for lang, extensions in self.language_extensions.items():
            language_stats[lang] = {
                'file_count': 0,
                'total_lines': 0,
                'total_size': 0
            }
        
        try:
            for root, dirs, files in os.walk(path):
                # Skip hidden directories and common non-source directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and 
                          d not in ['node_modules', '__pycache__', 'venv', 'env',
                                   'build', 'dist', 'target', '.git']]
                
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # Find matching language
                    for lang, extensions in self.language_extensions.items():
                        if file_ext in extensions:
                            try:
                                file_size = os.path.getsize(file_path)
                                line_count = self._count_lines(file_path)
                                
                                language_stats[lang]['file_count'] += 1
                                language_stats[lang]['total_lines'] += line_count
                                language_stats[lang]['total_size'] += file_size
                            except Exception as e:
                                logger.warning(f"Could not analyze file {file_path}: {e}")
                            break
        
        except Exception as e:
            logger.error(f"Error analyzing file extensions: {e}")
        
        # Remove languages with no files
        return {lang: stats for lang, stats in language_stats.items() 
                if stats['file_count'] > 0}
    
    def _analyze_config_files(self, path: str) -> Dict[str, List[str]]:
        """Analyze configuration files to identify languages and frameworks."""
        found_configs = {}
        
        try:
            for root, dirs, files in os.walk(path):
                if '.git' in root:
                    continue
                    
                for file in files:
                    for lang, config_patterns in self.config_files.items():
                        for pattern in config_patterns:
                            if pattern.startswith('*'):
                                # Handle wildcard patterns
                                if file.endswith(pattern[1:]):
                                    if lang not in found_configs:
                                        found_configs[lang] = []
                                    found_configs[lang].append(file)
                            elif file == pattern:
                                if lang not in found_configs:
                                    found_configs[lang] = []
                                found_configs[lang].append(file)
        
        except Exception as e:
            logger.error(f"Error analyzing config files: {e}")
        
        return found_configs
    
    def _detect_frameworks(self, path: str, language_stats: Dict) -> List[str]:
        """Detect frameworks used in the project."""
        frameworks = []
        
        try:
            # Check for framework-specific files and patterns
            for lang in language_stats.keys():
                if lang in self.framework_indicators:
                    for framework, indicators in self.framework_indicators[lang].items():
                        if self._check_framework_indicators(path, indicators):
                            frameworks.append(f"{lang}: {framework}")
            
            # Check package.json for JavaScript frameworks
            package_json_path = os.path.join(path, 'package.json')
            if os.path.exists(package_json_path):
                frameworks.extend(self._analyze_package_json(package_json_path))
            
            # Check requirements.txt for Python frameworks
            requirements_path = os.path.join(path, 'requirements.txt')
            if os.path.exists(requirements_path):
                frameworks.extend(self._analyze_requirements_txt(requirements_path))
        
        except Exception as e:
            logger.error(f"Error detecting frameworks: {e}")
        
        return frameworks
    
    def _check_framework_indicators(self, path: str, indicators: List[str]) -> bool:
        """Check if framework indicators are present in the project."""
        for indicator in indicators:
            # Check for files
            if os.path.exists(os.path.join(path, indicator)):
                return True
            
            # Check for patterns in file content (basic search)
            try:
                for root, dirs, files in os.walk(path):
                    if '.git' in root:
                        continue
                    for file in files:
                        if file.endswith(('.py', '.js', '.java', '.dart')):
                            file_path = os.path.join(root, file)
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read(1000)  # Read first 1KB
                                    if indicator in content:
                                        return True
                            except:
                                continue
            except:
                continue
        
        return False
    
    def _analyze_package_json(self, package_json_path: str) -> List[str]:
        """Analyze package.json for JavaScript frameworks."""
        frameworks = []
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            dependencies = {**package_data.get('dependencies', {}), 
                          **package_data.get('devDependencies', {})}
            
            framework_mapping = {
                'react': 'JavaScript: React',
                'vue': 'JavaScript: Vue.js',
                '@angular/core': 'JavaScript: Angular',
                'express': 'JavaScript: Express',
                'next': 'JavaScript: Next.js',
                'gatsby': 'JavaScript: Gatsby',
                'svelte': 'JavaScript: Svelte'
            }
            
            for dep, framework in framework_mapping.items():
                if dep in dependencies:
                    frameworks.append(framework)
        
        except Exception as e:
            logger.warning(f"Could not analyze package.json: {e}")
        
        return frameworks
    
    def _analyze_requirements_txt(self, requirements_path: str) -> List[str]:
        """Analyze requirements.txt for Python frameworks."""
        frameworks = []
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = f.read().lower()
            
            framework_mapping = {
                'django': 'Python: Django',
                'flask': 'Python: Flask',
                'fastapi': 'Python: FastAPI',
                'streamlit': 'Python: Streamlit',
                'jupyter': 'Python: Jupyter',
                'numpy': 'Python: NumPy/Scientific',
                'tensorflow': 'Python: TensorFlow',
                'pytorch': 'Python: PyTorch'
            }
            
            for package, framework in framework_mapping.items():
                if package in requirements:
                    frameworks.append(framework)
        
        except Exception as e:
            logger.warning(f"Could not analyze requirements.txt: {e}")
        
        return frameworks
    
    def _determine_project_type(self, path: str, frameworks: List[str]) -> str:
        """Determine the type of project based on structure and frameworks."""
        framework_str = ' '.join(frameworks).lower()
        
        # Check for specific project types
        if 'flutter' in framework_str or 'android' in framework_str:
            return 'mobile'
        elif 'react' in framework_str or 'vue' in framework_str or 'angular' in framework_str:
            return 'web_frontend'
        elif 'express' in framework_str or 'django' in framework_str or 'flask' in framework_str:
            return 'web_backend'
        elif 'streamlit' in framework_str or 'jupyter' in framework_str:
            return 'data_science'
        elif os.path.exists(os.path.join(path, 'setup.py')) or os.path.exists(os.path.join(path, 'pyproject.toml')):
            return 'library'
        elif os.path.exists(os.path.join(path, 'Dockerfile')):
            return 'containerized_app'
        else:
            return 'general'
    
    def _calculate_confidence(self, language_stats: Dict, config_analysis: Dict) -> float:
        """Calculate confidence score for the language analysis."""
        confidence = 0.0
        
        # Base confidence from file analysis
        total_files = sum(stats['file_count'] for stats in language_stats.values())
        if total_files > 0:
            confidence += 0.5
        
        # Boost confidence with config files
        if config_analysis:
            confidence += 0.3
        
        # Boost confidence with multiple languages
        if len(language_stats) > 1:
            confidence += 0.1
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _create_language_info_list(self, language_stats: Dict) -> List[LanguageInfo]:
        """Create sorted list of LanguageInfo objects."""
        languages = []
        total_files = sum(stats['file_count'] for stats in language_stats.values())
        
        if total_files == 0:
            return languages
        
        for lang, stats in language_stats.items():
            percentage = (stats['file_count'] / total_files) * 100
            lang_info = LanguageInfo(
                name=lang,
                percentage=round(percentage, 2),
                file_count=stats['file_count'],
                total_lines=stats['total_lines']
            )
            languages.append(lang_info)
        
        # Sort by percentage (descending)
        languages.sort(key=lambda x: x.percentage, reverse=True)
        return languages
    
    def _extract_build_tools(self, config_analysis: Dict) -> List[str]:
        """Extract build tools from config analysis."""
        build_tools = []
        
        tool_mapping = {
            'pom.xml': 'Maven',
            'build.gradle': 'Gradle',
            'CMakeLists.txt': 'CMake',
            'Makefile': 'Make',
            'setup.py': 'Python setuptools',
            'pyproject.toml': 'Python build',
            'Cargo.toml': 'Cargo'
        }
        
        for lang, configs in config_analysis.items():
            for config in configs:
                if config in tool_mapping:
                    build_tools.append(tool_mapping[config])
        
        return list(set(build_tools))  # Remove duplicates
    
    def _extract_package_managers(self, config_analysis: Dict) -> List[str]:
        """Extract package managers from config analysis."""
        package_managers = []
        
        manager_mapping = {
            'package.json': 'npm/yarn',
            'requirements.txt': 'pip',
            'Pipfile': 'pipenv',
            'poetry.lock': 'poetry',
            'pubspec.yaml': 'pub',
            'Gemfile': 'bundler',
            'composer.json': 'composer',
            'go.mod': 'go modules'
        }
        
        for lang, configs in config_analysis.items():
            for config in configs:
                if config in manager_mapping:
                    package_managers.append(manager_mapping[config])
        
        return list(set(package_managers))  # Remove duplicates
    
    def _count_lines(self, file_path: str) -> int:
        """Count lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0 