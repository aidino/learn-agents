"""
Intelligent Code Scanner với ADK Workflow Agents

Sử dụng Sequential Agent để phối hợp các sub-agents trong quy trình:
1. Rule Analysis Agent - Xác định rules cần thiết
2. Code Pattern Agent - Phân tích patterns trong code
3. Optimized Security Scan Agent - Thực hiện scan với rules tối ưu

Dựa trên: https://google.github.io/adk-docs/agents/workflow-agents/
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import Counter

try:
    from google.adk.agents import Agent  # Original ADK Agent
except ImportError:
    # Fallback to custom Agent implemented in intelligent_workflows
    from .intelligent_workflows import Agent

logger = logging.getLogger(__name__)


class RuleAnalysisAgent(Agent):
    """
    Agent phân tích project để xác định rules Semgrep cần thiết
    """
    
    def __init__(self):
        super().__init__(name="RuleAnalysisAgent")
    
    def analyze_project_rules(self, directory_path: str) -> Dict[str, Any]:
        """
        Phân tích project để xác định rules cần thiết
        
        Args:
            directory_path: Đường dẫn thư mục project
            
        Returns:
            Dict chứa recommended rules và rationale
        """
        try:
            project_path = Path(directory_path)
            if not project_path.exists() or not project_path.is_dir():
                raise ValueError(f"Invalid directory: {directory_path}")
            
            # Phân tích file types và languages
            languages = self._detect_languages(project_path)
            frameworks = self._detect_frameworks(project_path)
            security_contexts = self._analyze_security_contexts(project_path)
            
            # Xác định rules dựa trên phân tích
            recommended_rules = self._determine_rules(languages, frameworks, security_contexts)
            
            return {
                "status": "success",
                "analysis": {
                    "languages_detected": languages,
                    "frameworks_detected": frameworks,
                    "security_contexts": security_contexts,
                    "recommended_rules": recommended_rules,
                    "rule_rationale": self._explain_rule_selection(recommended_rules, languages, frameworks)
                }
            }
            
        except Exception as e:
            logger.error(f"Rule analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_rules": ["auto"]  # Fallback to auto rules
            }
    
    def _detect_languages(self, project_path: Path) -> List[str]:
        """Phát hiện ngôn ngữ lập trình trong project"""
        language_extensions = {
            'python': ['.py', '.pyx', '.pyi'],
            'javascript': ['.js', '.mjs'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.cc', '.cxx', '.hpp'],
            'csharp': ['.cs'],
            'php': ['.php', '.phtml'],
            'ruby': ['.rb', '.rake'],
            'go': ['.go'],
            'rust': ['.rs'],
            'swift': ['.swift'],
            'kotlin': ['.kt', '.kts'],
            'scala': ['.scala'],
            'dart': ['.dart'],
            'r': ['.r', '.R']
        }
        
        detected_languages = set()
        file_count = Counter()
        
        # Quét files trong project
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                for lang, extensions in language_extensions.items():
                    if suffix in extensions:
                        detected_languages.add(lang)
                        file_count[lang] += 1
        
        # Sort by frequency
        sorted_languages = sorted(detected_languages, key=lambda x: file_count[x], reverse=True)
        
        logger.info(f"Detected languages: {sorted_languages}")
        return sorted_languages
    
    def _detect_frameworks(self, project_path: Path) -> List[str]:
        """Phát hiện frameworks và dependencies"""
        frameworks = set()
        
        # Check common config files
        config_indicators = {
            'package.json': ['react', 'vue', 'angular', 'express', 'nextjs'],
            'requirements.txt': ['django', 'flask', 'fastapi', 'pyramid'],
            'Gemfile': ['rails', 'sinatra'],
            'pom.xml': ['spring', 'struts'],
            'build.gradle': ['spring', 'android'],
            'Cargo.toml': ['actix', 'rocket'],
            'composer.json': ['laravel', 'symfony']
        }
        
        for config_file, framework_list in config_indicators.items():
            config_path = project_path / config_file
            if config_path.exists():
                try:
                    content = config_path.read_text(encoding='utf-8', errors='ignore').lower()
                    for framework in framework_list:
                        if framework in content:
                            frameworks.add(framework)
                except Exception as e:
                    logger.warning(f"Could not read {config_file}: {e}")
        
        # Check for specific patterns in code
        self._detect_code_patterns(project_path, frameworks)
        
        return list(frameworks)
    
    def _detect_code_patterns(self, project_path: Path, frameworks: Set[str]):
        """Phát hiện patterns trong code để xác định frameworks"""
        pattern_indicators = {
            'django': ['from django', 'import django'],
            'flask': ['from flask', 'import flask'],
            'react': ['import React', 'from react'],
            'vue': ['new Vue', '@vue/'],
            'express': ['require("express")', 'import express'],
            'spring': ['@SpringBootApplication', '@RestController']
        }
        
        sample_files = list(project_path.rglob('*.py'))[:10] + \
                      list(project_path.rglob('*.js'))[:10] + \
                      list(project_path.rglob('*.java'))[:10]
        
        for file_path in sample_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
                for framework, patterns in pattern_indicators.items():
                    if any(pattern.lower() in content for pattern in patterns):
                        frameworks.add(framework)
            except Exception:
                continue
    
    def _analyze_security_contexts(self, project_path: Path) -> List[str]:
        """Phân tích contexts bảo mật trong project"""
        security_contexts = set()
        
        # Indicators for different security contexts
        context_indicators = {
            'web_app': ['http', 'https', 'url', 'request', 'response', 'session'],
            'database': ['sql', 'database', 'db', 'query', 'connect'],
            'api': ['api', 'rest', 'graphql', 'endpoint'],
            'crypto': ['encrypt', 'decrypt', 'hash', 'cipher', 'key'],
            'auth': ['auth', 'login', 'password', 'token', 'jwt'],
            'file_ops': ['file', 'read', 'write', 'upload', 'download'],
            'network': ['socket', 'tcp', 'udp', 'port', 'network'],
            'subprocess': ['subprocess', 'exec', 'command', 'shell']
        }
        
        # Sample a few files for quick analysis
        sample_files = []
        for ext in ['.py', '.js', '.java', '.php', '.rb']:
            sample_files.extend(list(project_path.rglob(f'*{ext}'))[:5])
        
        for file_path in sample_files[:20]:  # Limit to 20 files for performance
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
                for context, indicators in context_indicators.items():
                    if any(indicator in content for indicator in indicators):
                        security_contexts.add(context)
            except Exception:
                continue
        
        return list(security_contexts)
    
    def _determine_rules(self, languages: List[str], frameworks: List[str], contexts: List[str]) -> List[str]:
        """Xác định Semgrep rules dựa trên phân tích"""
        rules = set()
        
        # Always include 'auto' for comprehensive coverage
        rules.add("auto")
        
        # Base security rules
        rules.add("p/security-audit")
        rules.add("p/owasp-top-ten")  # Add OWASP by default
        
        # Language-specific rules (only add if specific framework detected)
        language_rules = {
            'python': ['p/python'],
            'javascript': ['p/javascript'],
            'typescript': ['p/typescript'],
            'java': ['p/java'],
            'php': ['p/php'],
            'ruby': ['p/ruby'],
            'go': ['p/golang'],
            'rust': ['p/rust'],
            'swift': ['p/swift'],
            'csharp': ['p/csharp']
        }
        
        # Only add language rules for primary language
        if languages:
            primary_lang = languages[0]  # Most frequent language
            if primary_lang in language_rules:
                rules.update(language_rules[primary_lang])
        
        # Framework-specific rules
        framework_rules = {
            'django': ['p/django'],
            'flask': ['p/flask'],
            'react': ['p/react'],
            'vue': ['p/vue'],
            'spring': ['p/spring'],
            'laravel': ['p/laravel'],
            'rails': ['p/rails']
        }
        
        for framework in frameworks:
            if framework in framework_rules:
                rules.update(framework_rules[framework])
        
        # Context-specific rules
        if 'web_app' in contexts:
            rules.add('p/xss')
        if 'database' in contexts:
            rules.add('p/sql-injection')
        if 'crypto' in contexts:
            rules.add('p/crypto')
        if 'auth' in contexts:
            rules.add('p/jwt')
        
        # Remove non-existent rules and return sorted list
        validated_rules = self._validate_rules(list(rules))
        return sorted(validated_rules)
    
    def _validate_rules(self, rules: List[str]) -> List[str]:
        """Validate rule existence (simplified - in practice would check with Semgrep)"""
        # Common Semgrep rules that actually exist
        valid_rules = {
            'p/security-audit', 'p/python', 'p/javascript', 'p/typescript',
            'p/java', 'p/php', 'p/ruby', 'p/golang', 'p/rust', 'p/swift',
            'p/csharp', 'p/owasp-top-ten', 'p/react', 'p/django', 'p/flask'
        }
        
        return [rule for rule in rules if rule in valid_rules]
    
    def _explain_rule_selection(self, rules: List[str], languages: List[str], frameworks: List[str]) -> Dict[str, str]:
        """Giải thích lý do chọn rules"""
        explanations = {}
        
        for rule in rules:
            if rule == 'p/security-audit':
                explanations[rule] = "Base security audit rules for all projects"
            elif rule.startswith('p/') and rule[2:] in languages:
                explanations[rule] = f"Language-specific rules for {rule[2:]}"
            elif rule.startswith('p/') and rule[2:] in frameworks:
                explanations[rule] = f"Framework-specific rules for {rule[2:]}"
            elif rule == 'p/owasp-top-ten':
                explanations[rule] = "OWASP Top 10 security vulnerabilities"
            else:
                explanations[rule] = "Additional security rule based on project analysis"
        
        return explanations


class CodePatternAgent(Agent):
    """
    Agent phân tích patterns trong code để fine-tune scanning approach
    """
    
    def __init__(self):
        super().__init__(name="CodePatternAgent")
    
    def analyze_code_patterns(self, directory_path: str, languages: List[str]) -> Dict[str, Any]:
        """
        Phân tích patterns trong code để tối ưu scanning
        
        Args:
            directory_path: Đường dẫn project
            languages: Danh sách ngôn ngữ đã phát hiện
            
        Returns:
            Dict chứa pattern analysis và scanning priorities
        """
        try:
            project_path = Path(directory_path)
            
            # Phân tích file structure
            file_analysis = self._analyze_file_structure(project_path)
            
            # Phân tích complexity
            complexity_analysis = self._analyze_complexity(project_path, languages)
            
            # Xác định high-risk patterns
            risk_patterns = self._identify_risk_patterns(project_path, languages)
            
            # Tạo scanning priorities
            scan_priorities = self._create_scan_priorities(file_analysis, risk_patterns)
            
            return {
                "status": "success",
                "pattern_analysis": {
                    "file_structure": file_analysis,
                    "complexity_metrics": complexity_analysis,
                    "risk_patterns": risk_patterns,
                    "scan_priorities": scan_priorities,
                    "optimization_suggestions": self._get_optimization_suggestions(file_analysis, risk_patterns)
                }
            }
            
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_priority": "medium"
            }
    
    def _analyze_file_structure(self, project_path: Path) -> Dict[str, Any]:
        """Phân tích cấu trúc files"""
        file_stats = {
            'total_files': 0,
            'code_files': 0,
            'large_files': 0,
            'file_types': Counter(),
            'directory_depth': 0
        }
        
        for file_path in project_path.rglob('*'):
            if file_path.is_file():
                file_stats['total_files'] += 1
                
                # Track file extensions
                if file_path.suffix:
                    file_stats['file_types'][file_path.suffix] += 1
                
                # Check if it's a code file
                if file_path.suffix in ['.py', '.js', '.java', '.php', '.rb', '.go', '.rs']:
                    file_stats['code_files'] += 1
                    
                    # Check file size
                    try:
                        if file_path.stat().st_size > 100_000:  # 100KB
                            file_stats['large_files'] += 1
                    except Exception:
                        pass
                
                # Track directory depth
                depth = len(file_path.relative_to(project_path).parts) - 1
                file_stats['directory_depth'] = max(file_stats['directory_depth'], depth)
        
        return file_stats
    
    def _analyze_complexity(self, project_path: Path, languages: List[str]) -> Dict[str, Any]:
        """Phân tích complexity của code"""
        complexity_metrics = {
            'estimated_loc': 0,
            'average_file_size': 0,
            'complexity_indicators': []
        }
        
        total_lines = 0
        file_count = 0
        
        # Sample files for complexity analysis
        for lang in languages[:3]:  # Limit to top 3 languages
            ext_map = {
                'python': '.py', 'javascript': '.js', 'java': '.java',
                'php': '.php', 'ruby': '.rb', 'go': '.go'
            }
            
            if lang not in ext_map:
                continue
                
            files = list(project_path.rglob(f'*{ext_map[lang]}'))[:10]
            
            for file_path in files:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    lines = len(content.splitlines())
                    total_lines += lines
                    file_count += 1
                    
                    # Look for complexity indicators
                    if 'class ' in content:
                        complexity_metrics['complexity_indicators'].append('object_oriented')
                    if 'import ' in content or 'require(' in content:
                        complexity_metrics['complexity_indicators'].append('external_dependencies')
                    if 'async ' in content or 'await ' in content:
                        complexity_metrics['complexity_indicators'].append('asynchronous_code')
                        
                except Exception:
                    continue
        
        if file_count > 0:
            complexity_metrics['estimated_loc'] = total_lines
            complexity_metrics['average_file_size'] = total_lines / file_count
        
        return complexity_metrics
    
    def _identify_risk_patterns(self, project_path: Path, languages: List[str]) -> List[Dict[str, Any]]:
        """Xác định patterns có risk cao"""
        risk_patterns = []
        
        # High-risk patterns to look for
        pattern_definitions = {
            'hardcoded_secrets': {
                'patterns': ['password =', 'api_key =', 'secret =', 'token ='],
                'severity': 'high',
                'description': 'Potential hardcoded credentials'
            },
            'sql_queries': {
                'patterns': ['SELECT ', 'INSERT ', 'UPDATE ', 'DELETE ', '.execute('],
                'severity': 'medium',
                'description': 'SQL operations detected'
            },
            'subprocess_calls': {
                'patterns': ['subprocess.', 'os.system', 'exec(', 'eval('],
                'severity': 'high',
                'description': 'Subprocess or eval operations'
            },
            'network_operations': {
                'patterns': ['requests.', 'urllib', 'socket.', 'http'],
                'severity': 'medium',
                'description': 'Network operations detected'
            }
        }
        
        # Sample files for pattern detection
        sample_files = []
        for lang in languages[:2]:
            ext_map = {'python': '.py', 'javascript': '.js', 'java': '.java', 'php': '.php'}
            if lang in ext_map:
                sample_files.extend(list(project_path.rglob(f'*{ext_map[lang]}'))[:5])
        
        for pattern_name, pattern_def in pattern_definitions.items():
            matches = 0
            matched_files = []
            
            for file_path in sample_files[:15]:  # Limit for performance
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore').lower()
                    file_matches = sum(1 for pattern in pattern_def['patterns'] 
                                     if pattern.lower() in content)
                    if file_matches > 0:
                        matches += file_matches
                        # Store relative path instead of just name
                        try:
                            rel_path = file_path.relative_to(project_path)
                            matched_files.append(str(rel_path))
                        except ValueError:
                            matched_files.append(str(file_path.name))
                except Exception:
                    continue
            
            if matches > 0:
                risk_patterns.append({
                    'pattern_name': pattern_name,
                    'severity': pattern_def['severity'],
                    'description': pattern_def['description'],
                    'matches_found': matches,
                    'files_with_pattern': matched_files[:5]  # Top 5 files
                })
        
        return risk_patterns
    
    def _create_scan_priorities(self, file_analysis: Dict, risk_patterns: List[Dict]) -> Dict[str, Any]:
        """Tạo priorities cho scanning"""
        priority_score = 0
        priority_factors = []
        
        # Factor in file complexity
        if file_analysis['large_files'] > 10:
            priority_score += 2
            priority_factors.append("Many large files detected")
        
        if file_analysis['code_files'] > 100:
            priority_score += 1
            priority_factors.append("Large codebase")
        
        # Factor in risk patterns
        high_risk_patterns = [p for p in risk_patterns if p['severity'] == 'high']
        medium_risk_patterns = [p for p in risk_patterns if p['severity'] == 'medium']
        
        priority_score += len(high_risk_patterns) * 3
        priority_score += len(medium_risk_patterns) * 1
        
        if high_risk_patterns:
            priority_factors.append(f"High-risk patterns detected: {len(high_risk_patterns)}")
        
        # Determine priority level
        if priority_score >= 8:
            priority_level = "high"
        elif priority_score >= 4:
            priority_level = "medium"
        else:
            priority_level = "low"
        
        return {
            "priority_level": priority_level,
            "priority_score": priority_score,
            "priority_factors": priority_factors,
            "recommended_scan_approach": self._get_scan_approach(priority_level, file_analysis)
        }
    
    def _get_scan_approach(self, priority_level: str, file_analysis: Dict) -> str:
        """Đề xuất approach cho scanning"""
        if priority_level == "high":
            return "comprehensive_scan"
        elif priority_level == "medium":
            return "targeted_scan"
        else:
            return "quick_scan"
    
    def _get_optimization_suggestions(self, file_analysis: Dict, risk_patterns: List[Dict]) -> List[str]:
        """Đề xuất tối ưu hóa scanning"""
        suggestions = []
        
        if file_analysis['large_files'] > 20:
            suggestions.append("Consider excluding very large files from initial scan")
        
        if len(risk_patterns) > 5:
            suggestions.append("Focus on high-severity patterns first")
        
        if file_analysis['code_files'] > 200:
            suggestions.append("Use parallel scanning for better performance")
        
        return suggestions


class OptimizedSecurityScanAgent(Agent):
    """
    Agent thực hiện security scan với rules và priorities đã được tối ưu
    """
    
    def __init__(self):
        super().__init__(name="OptimizedSecurityScanAgent")
        # Will initialize semgrep_client when needed
    
    def perform_optimized_scan(self, directory_path: str, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực hiện optimized security scan
        
        Args:
            directory_path: Đường dẫn project
            analysis_results: Kết quả từ các agents trước
            
        Returns:
            Kết quả scan đã được tối ưu
        """
        try:
            from .semgrep_client import SemgrepSyncClient
            
            # Extract analysis data
            rule_analysis = analysis_results.get('rule_analysis', {})
            pattern_analysis = analysis_results.get('pattern_analysis', {})
            
            recommended_rules = rule_analysis.get('analysis', {}).get('recommended_rules', ['auto'])
            scan_priority = pattern_analysis.get('pattern_analysis', {}).get('scan_priorities', {})
            
            # Prepare optimized scan configuration
            scan_config = self._prepare_scan_config(recommended_rules, scan_priority)
            
            # Execute scan with optimized settings
            with SemgrepSyncClient() as client:
                if scan_config['approach'] == 'comprehensive_scan':
                    results = self._comprehensive_scan(client, directory_path, scan_config)
                elif scan_config['approach'] == 'targeted_scan':
                    results = self._targeted_scan(client, directory_path, scan_config)
                else:
                    results = self._quick_scan(client, directory_path, scan_config)
            
            # Post-process results with analysis context
            processed_results = self._post_process_results(results, analysis_results)
            
            return {
                "status": "success",
                "scan_results": processed_results,
                "optimization_applied": scan_config,
                "analysis_context": {
                    "rules_used": scan_config['rules'],
                    "scan_approach": scan_config['approach'],
                    "priority_level": scan_priority.get('priority_level', 'medium')
                }
            }
            
        except Exception as e:
            logger.error(f"Optimized scan failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_results": self._fallback_scan(directory_path)
            }
    
    def _prepare_scan_config(self, rules: List[str], scan_priority: Dict) -> Dict[str, Any]:
        """Chuẩn bị configuration cho scan"""
        approach = scan_priority.get('recommended_scan_approach', 'quick_scan')
        priority_level = scan_priority.get('priority_level', 'medium')
        
        # Optimize rules based on priority - always include 'auto' for better detection
        if priority_level == 'high':
            # Use all recommended rules for high priority 
            selected_rules = rules if 'auto' in rules else ['auto'] + rules[:3]
        elif priority_level == 'medium':
            # Use auto for better coverage
            selected_rules = ['auto']
        else:
            # Use auto for comprehensive coverage in quick scan
            selected_rules = ['auto']
        
        return {
            'approach': approach,
            'rules': selected_rules,
            'priority_level': priority_level,
            'config_string': self._build_config_string(selected_rules)
        }
    
    def _build_config_string(self, rules: List[str]) -> str:
        """Build Semgrep config string from rules"""
        if len(rules) == 1:
            return rules[0]
        else:
            # Prefer 'auto' for comprehensive coverage
            if 'auto' in rules:
                return 'auto'
            # For multiple rules, use the most important one
            priority_order = ['p/owasp-top-ten', 'p/security-audit']
            for priority_rule in priority_order:
                if priority_rule in rules:
                    return priority_rule
            return rules[0] if rules else 'auto'
    
    def _comprehensive_scan(self, client, directory_path: str, config: Dict) -> Dict[str, Any]:
        """Thực hiện comprehensive scan"""
        logger.info(f"Performing comprehensive scan with rules: {config['rules']}")
        return client.scan_directory(directory_path, config['config_string'])
    
    def _targeted_scan(self, client, directory_path: str, config: Dict) -> Dict[str, Any]:
        """Thực hiện targeted scan"""
        logger.info(f"Performing targeted scan with rules: {config['rules']}")
        return client.scan_directory(directory_path, config['config_string'])
    
    def _quick_scan(self, client, directory_path: str, config: Dict) -> Dict[str, Any]:
        """Thực hiện quick scan"""
        logger.info(f"Performing quick scan with rules: {config['rules']}")
        return client.scan_directory(directory_path, config['config_string'])
    
    def _post_process_results(self, results: Dict[str, Any], analysis_context: Dict) -> Dict[str, Any]:
        """Post-process scan results với analysis context"""
        from .agent import format_scan_results
        
        # Format raw Semgrep results properly first
        formatted_results = format_scan_results(results)
        
        # Add analysis context to results
        if 'metadata' not in formatted_results:
            formatted_results['metadata'] = {}
        
        formatted_results['metadata']['intelligent_analysis'] = {
            'rules_optimization_applied': True,
            'pattern_analysis_used': True,
            'scan_tailored_to_project': True
        }
        
        # Get findings from formatted results
        if 'detailed_results' in formatted_results and analysis_context:
            enhanced_findings = self._enhance_findings_with_context(
                formatted_results['detailed_results'], 
                analysis_context
            )
            formatted_results['findings'] = enhanced_findings
            formatted_results['detailed_results'] = enhanced_findings
        
        return formatted_results
    
    def _enhance_findings_with_context(self, findings: List[Dict], context: Dict) -> List[Dict]:
        """Enhance findings với analysis context"""
        # Add priority scoring based on pattern analysis
        pattern_analysis = context.get('pattern_analysis', {}).get('pattern_analysis', {})
        risk_patterns = pattern_analysis.get('risk_patterns', [])
        
        enhanced_findings = []
        for finding in findings:
            enhanced_finding = finding.copy()
            
            # Add context-based priority
            if any(risk['pattern_name'] in str(finding).lower() for risk in risk_patterns):
                enhanced_finding['context_priority'] = 'high'
                enhanced_finding['context_note'] = 'Matches detected risk pattern'
            else:
                enhanced_finding['context_priority'] = 'standard'
            
            enhanced_findings.append(enhanced_finding)
        
        return enhanced_findings
    
    def _fallback_scan(self, directory_path: str) -> Dict[str, Any]:
        """Fallback scan nếu optimized scan fails"""
        try:
            from .agent import scan_code_directory
            return scan_code_directory(directory_path, 'auto')
        except Exception as e:
            return {
                "status": "error",
                "error": f"Both optimized and fallback scans failed: {e}"
            }


class IntelligentCodeScanner:
    """
    Main Intelligent Code Scanner orchestrator
    Phối hợp ba sub-agents theo thứ tự để thực hiện intelligent scanning
    """
    
    def __init__(self):
        # Khởi tạo các sub-agents
        self.rule_agent = RuleAnalysisAgent()
        self.pattern_agent = CodePatternAgent() 
        self.scan_agent = OptimizedSecurityScanAgent()
        
        logger.info("IntelligentCodeScanner initialized with 3 sub-agents")
    
    def intelligent_scan_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Thực hiện intelligent scan cho directory
        
        Args:
            directory_path: Đường dẫn thư mục cần scan
            
        Returns:
            Kết quả scan intelligent với analysis context
        """
        try:
            logger.info(f"Starting intelligent scan for: {directory_path}")
            
            # Step 1: Rule Analysis
            logger.info("Step 1: Analyzing project to determine optimal rules...")
            rule_results = self.rule_agent.analyze_project_rules(directory_path)
            
            if rule_results['status'] == 'error':
                logger.warning("Rule analysis failed, using fallback")
                return self._fallback_traditional_scan(directory_path)
            
            # Step 2: Pattern Analysis
            logger.info("Step 2: Analyzing code patterns...")
            languages = rule_results.get('analysis', {}).get('languages_detected', [])
            pattern_results = self.pattern_agent.analyze_code_patterns(directory_path, languages)
            
            # Step 3: Optimized Scan
            logger.info("Step 3: Performing optimized security scan...")
            analysis_context = {
                'rule_analysis': rule_results,
                'pattern_analysis': pattern_results
            }
            scan_results = self.scan_agent.perform_optimized_scan(directory_path, analysis_context)
            
            # Format and combine all results
            formatted_scan_results = self._format_intelligent_results(scan_results, directory_path)
            
            final_results = {
                "status": "success",
                "intelligent_scan_complete": True,
                "directory_scanned": directory_path,
                "workflow_steps": {
                    "1_rule_analysis": rule_results,
                    "2_pattern_analysis": pattern_results, 
                    "3_optimized_scan": scan_results
                },
                "summary": self._create_scan_summary(rule_results, pattern_results, scan_results),
                "recommendations": self._generate_recommendations(rule_results, pattern_results, scan_results),
                # Include formatted results for user consumption
                **formatted_scan_results
            }
            
            logger.info("Intelligent scan completed successfully")
            return final_results
            
        except Exception as e:
            logger.error(f"Intelligent scan failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_scan": self._fallback_traditional_scan(directory_path)
            }
    
    def _create_scan_summary(self, rule_results: Dict, pattern_results: Dict, scan_results: Dict) -> Dict[str, Any]:
        """Tạo summary cho intelligent scan"""
        summary = {
            "scan_approach": "intelligent_multi_step",
            "optimization_applied": True
        }
        
        # Add rule analysis summary
        if rule_results.get('status') == 'success':
            analysis = rule_results.get('analysis', {})
            summary.update({
                "languages_detected": analysis.get('languages_detected', []),
                "frameworks_detected": analysis.get('frameworks_detected', []),
                "rules_optimized": len(analysis.get('recommended_rules', [])),
                "rule_selection_rationale": "Based on project analysis"
            })
        
        # Add pattern analysis summary
        if pattern_results.get('status') == 'success':
            pattern_analysis = pattern_results.get('pattern_analysis', {})
            summary.update({
                "risk_patterns_found": len(pattern_analysis.get('risk_patterns', [])),
                "scan_priority": pattern_analysis.get('scan_priorities', {}).get('priority_level', 'medium'),
                "complexity_assessed": True
            })
        
        # Add scan results summary
        if scan_results.get('status') == 'success':
            scan_data = scan_results.get('scan_results', {})
            summary.update({
                "scan_completed": True,
                "findings_count": len(scan_data.get('findings', [])),
                "optimization_effective": True
            })
        
        return summary
    
    def _generate_recommendations(self, rule_results: Dict, pattern_results: Dict, scan_results: Dict) -> List[str]:
        """Tạo recommendations dựa trên intelligent analysis"""
        recommendations = []
        
        # Recommendations từ rule analysis
        if rule_results.get('status') == 'success':
            analysis = rule_results.get('analysis', {})
            if len(analysis.get('languages_detected', [])) > 3:
                recommendations.append("Consider using language-specific scanning strategies for better coverage")
            
            if 'django' in analysis.get('frameworks_detected', []):
                recommendations.append("Enable Django-specific security rules for framework vulnerabilities")
        
        # Recommendations từ pattern analysis
        if pattern_results.get('status') == 'success':
            pattern_analysis = pattern_results.get('pattern_analysis', {})
            risk_patterns = pattern_analysis.get('risk_patterns', [])
            
            high_risk = [p for p in risk_patterns if p.get('severity') == 'high']
            if high_risk:
                recommendations.append(f"High-risk patterns detected: prioritize fixing {len(high_risk)} critical issues")
            
            suggestions = pattern_analysis.get('optimization_suggestions', [])
            recommendations.extend(suggestions)
        
        # Recommendations từ scan results
        if scan_results.get('status') == 'success':
            recommendations.append("Consider running periodic intelligent scans to maintain security posture")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _format_intelligent_results(self, scan_results: Dict, directory_path: str) -> Dict[str, Any]:
        """Format intelligent scan results cho end-user consumption"""
        from pathlib import Path
        
        # Get raw scan data
        scan_data = scan_results.get('scan_results', {})
        findings = scan_data.get('findings', [])
        
        # Format findings với proper file paths
        formatted_findings = []
        project_path = Path(directory_path)
        
        for finding in findings:
            if isinstance(finding, dict):
                formatted_finding = finding.copy()
                
                # Enhance file path display
                file_path = finding.get("path", "unknown")
                if file_path != "unknown":
                    try:
                        # Convert to relative path from project root
                        abs_path = Path(file_path)
                        if abs_path.is_absolute():
                            try:
                                rel_path = abs_path.relative_to(project_path)
                                formatted_finding["file_path"] = str(rel_path)
                                formatted_finding["full_path"] = str(abs_path)
                            except ValueError:
                                # Path is not relative to project, use as-is
                                formatted_finding["file_path"] = file_path
                                formatted_finding["full_path"] = file_path
                        else:
                            # Already relative
                            formatted_finding["file_path"] = file_path
                            formatted_finding["full_path"] = str(project_path / file_path)
                    except Exception:
                        # Fallback to original path
                        formatted_finding["file_path"] = file_path
                        formatted_finding["full_path"] = file_path
                
                formatted_findings.append(formatted_finding)
        
        # Calculate summary stats
        total_findings = len(formatted_findings)
        severity_breakdown = {}
        high_severity_findings = []
        
        for finding in formatted_findings:
            severity = finding.get("extra", {}).get("severity", "info").lower()
            severity_breakdown[severity] = severity_breakdown.get(severity, 0) + 1
            
            # Collect high severity findings với enhanced info
            if severity in ["error", "warning"]:
                high_severity_findings.append({
                    "rule_id": finding.get("check_id", "unknown"),
                    "message": finding.get("extra", {}).get("message", "No message"),
                    "severity": severity,
                    "file_path": finding.get("file_path", finding.get("path", "unknown")),
                    "full_path": finding.get("full_path", finding.get("path", "unknown")),
                    "line": finding.get("start", {}).get("line", "unknown"),
                    "context_priority": finding.get("context_priority", "standard")
                })
        
        # Create user-friendly summary
        if total_findings == 0:
            summary_text = f"✅ Intelligent scan completed - Không tìm thấy vấn đề bảo mật nào trong '{Path(directory_path).name}'"
        else:
            summary_text = f"🔍 Intelligent scan completed - Tìm thấy {total_findings} vấn đề trong '{Path(directory_path).name}'"
        
        return {
            "summary": summary_text,
            "total_findings": total_findings,
            "severity_breakdown": severity_breakdown,
            "high_severity_findings": high_severity_findings[:5],  # Top 5 critical issues
            "detailed_results": formatted_findings[:10],  # First 10 detailed results
            "intelligent_summary": {
                "scan_type": "intelligent_analysis",
                "optimization_applied": True,
                "context_enhanced": True
            }
        }
    
    def _fallback_traditional_scan(self, directory_path: str) -> Dict[str, Any]:
        """Fallback to traditional scan nếu intelligent scan fails"""
        try:
            from .agent import scan_code_directory
            logger.info("Falling back to traditional scan method")
            result = scan_code_directory(directory_path, 'auto')
            result['scan_type'] = 'traditional_fallback'
            result['intelligent_features'] = False
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": f"Both intelligent and traditional scans failed: {e}"
            }


# Export main function for use in agent.py
def intelligent_scan_code_directory(directory_path: str) -> Dict[str, Any]:
    """
    Main function để thực hiện intelligent scanning
    
    Args:
        directory_path: Đường dẫn thư mục cần scan
        
    Returns:
        Kết quả intelligent scan
    """
    scanner = IntelligentCodeScanner()
    return scanner.intelligent_scan_directory(directory_path)