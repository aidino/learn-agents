import json
from dataclasses import asdict
from typing import List
from google.adk.agents import LlmAgent
from google.adk.agents import SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseServerParams
from google.genai import types as genai_types
from security_agent.tools.language_identifier import LanguageIdentifier

GEMINI_MODEL = "gemini-2.0-flash"

def get_language_profile(project_path: str) -> str:
    language_identifier = LanguageIdentifier()
    language_profile = language_identifier.identify_language(project_path)
    return json.dumps(asdict(language_profile), indent=2, ensure_ascii=False)

def run_local_semgrep_scan(project_path: str, configs: List[str]) -> str:
    """
    Fallback function to run Semgrep locally when MCP tools fail
    """
    import subprocess
    import tempfile
    import os
    
    try:
        # Build semgrep command
        cmd = ["semgrep", "--json", "--quiet"]
        
        # Add configs
        for config in configs:
            cmd.extend(["--config", config])
        
        # Add target path
        cmd.append(project_path)
        
        # Run semgrep
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            return f"Semgrep scan completed successfully:\n{result.stdout}"
        else:
            return f"Semgrep scan completed with warnings/errors:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            
    except subprocess.TimeoutExpired:
        return "Semgrep scan timed out after 5 minutes"
    except Exception as e:
        return f"Error running local Semgrep scan: {str(e)}"

language_identifier_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='language_identifier_agent',
    description='Identify the programming language of the code',
    instruction="""
    You are a language identifier agent. Your task is to identify the programming languages and frameworks used in the provided code project.
    
    WORKFLOW:
    1. **Execute language analysis**: Use the available tool 'get_language_profile' with the project_path parameter (/home/dino/Documents/novaguard-ai2/) to analyze the codebase and generate a comprehensive language profile.
    
    2. **Generate output**: The tool will scan the project directory and return a JSON object containing:
       - Primary programming languages detected
       - Frameworks and libraries identified
       - File types and their distribution
       - Technology stack information
    
    CRITICAL: You MUST call the get_language_profile function with the project path /home/dino/Documents/novaguard-ai2/ to complete this analysis.
    
    EXAMPLE USAGE:
    Call: get_language_profile("/home/dino/Documents/novaguard-ai2/")
    
    OUTPUT REQUIREMENT:
    You must successfully execute the language analysis and provide the language_profile results for the next agent to use.
    """,
    tools=[get_language_profile], 
    output_key='language_profile'
)

rule_identifier_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='rule_identifier_agent',
    description='Identify the appropriate rulesets for the code',
    instruction="""
    You are a rule identifier agent. Your task is to identify the most appropriate Semgrep rulesets for security analysis based on the language_profile received from the previous agent.

    CRITICAL: You MUST complete this task by generating a specific rule_profile output. Do NOT stop after just checking available rules.

    WORKFLOW:
    1. **Analyze the language_profile**: Review the programming languages, frameworks, and technologies identified in the previous step from the state.
    
    2. **Check available Semgrep rules**: Use the 'semgrep_rule_schema' tool from the MCPToolset to discover what Semgrep rulesets and configurations are supported and available.
    
    3. **Select appropriate rules**: Based on the language_profile and available Semgrep rules, identify the most relevant rulesets for comprehensive security scanning. Consider:
       - Language-specific rulesets (e.g., javascript, python, java, go, etc.)
       - Framework-specific rules (e.g., react, django, spring, etc.)
       - Security-focused rulesets (e.g., owasp-top-10, security-audit, cwe-top-25)
       - Industry standards and best practices
    
    4. **Generate rule_profile**: Create a JSON object containing a list of selected ruleset names that will be used for the security scan.

    IMPORTANT: After checking the available rules with semgrep_rule_schema, you MUST create and output a final rule_profile as a JSON list of strings. Do not just describe what rules are available - you must make specific selections.

    FALLBACK STRATEGY: If semgrep_rule_schema fails or is not accessible, use these standard proven Semgrep rulesets based on the detected languages:
    - For Python: "p/python", "p/security-audit", "p/owasp-top-10"
    - For JavaScript: "p/javascript", "p/react", "p/nodejs" 
    - For SQL: "p/sql-injection"
    - For Shell: "p/bash", "p/shell-injection"
    - General security: "p/security-audit", "p/owasp-top-10", "p/cwe-top-25"

    EXAMPLE OUTPUT:
    Based on the language_profile analysis, I select the following rules for scanning:
    rule_profile: ["p/security-audit", "p/owasp-top-10", "p/python", "p/javascript", "p/sql-injection"]

    AVAILABLE TOOLS:
    - Use MCPToolset tools, specifically 'semgrep_rule_schema' to check supported rulesets
    - Base your selections on the language_profile from the state

    OUTPUT REQUIREMENT:
    You MUST end your response with a clear rule_profile JSON list that will be used by the next agent for scanning.
    """,
    tools=[
        MCPToolset(
            connection_params=SseServerParams(url='http://0.0.0.0:50052/sse')
        )
    ],
    output_key='rule_profile'
)

security_scan_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='security_scan_agent',
    description='Scan the code for security vulnerabilities',
    instruction="""
    You are a security scan agent. Your task is to execute a comprehensive Semgrep security scan on the project folder using the rules identified in the previous step.

    CRITICAL: You MUST actually execute the Semgrep scan and generate scan results. Do NOT just describe what you would do.

    WORKFLOW:
    1. **Retrieve rule_profile**: Extract the list of selected Semgrep rulesets from the rule_profile in the state (generated by the rule_identifier_agent). The rule_profile should be a JSON list like ["p/security-audit", "p/owasp-top-10", "p/python"].

    2. **Prepare scan parameters**: 
       - Use the project path/folder that needs to be scanned (/home/dino/Documents/novaguard-ai2/)
       - Apply the rules from rule_profile to ensure comprehensive coverage
       - Configure scan options for detailed security analysis

    3. **Execute Semgrep scan**: Use the MCPToolset tools to run Semgrep security scan with:
       - The identified rulesets from rule_profile (e.g., p/security-audit, p/owasp-top-10, language-specific rules)
       - Target the entire project directory for complete coverage
       - Generate detailed output including file paths, line numbers, and vulnerability details
       - Use appropriate Semgrep command like: semgrep --config=p/security-audit --config=p/owasp-top-10 /path/to/project

    4. **Process scan results**: Collect and organize the scan output for further analysis.

    EXAMPLE COMMAND USAGE:
    Based on rule_profile: ["p/security-audit", "p/owasp-top-10", "p/python"]
    Execute: semgrep --config=p/security-audit --config=p/owasp-top-10 --config=p/python --json /home/dino/Documents/novaguard-ai2/

    FALLBACK STRATEGY: If MCP tools fail, use these approaches:
    1. Use the 'run_local_semgrep_scan' function as fallback
    2. Try simpler configs: ["p/security-audit"] or ["auto"] 
    3. Call: run_local_semgrep_scan("/home/dino/Documents/novaguard-ai2/", ["p/security-audit", "p/owasp-top-10"])
    4. Always attempt to provide some security analysis even if partial

    AVAILABLE TOOLS:
    - MCPToolset: Primary tool for Semgrep commands through MCP server
    - run_local_semgrep_scan: Fallback local Semgrep execution (project_path, configs_list)
    - Apply the rules specified in rule_profile from state

    INPUT FROM STATE:
    - rule_profile: JSON list of Semgrep ruleset names to be used for scanning
    - language_profile: Programming languages detected (for context)
    - project_path: Directory path to scan (/home/dino/Documents/novaguard-ai2/)

    OUTPUT REQUIREMENT:
    You MUST execute the actual Semgrep scan and produce a security_scan_result containing all findings. Do not just plan or describe - actually run the scan.
    """,
    tools=[
        MCPToolset(connection_params=SseServerParams(url='http://0.0.0.0:50052/sse')),
        run_local_semgrep_scan
    ],
    output_key='security_scan_result'
)


security_analysis_agent = LlmAgent(
    model=GEMINI_MODEL,
    name='security_analysis_agent',
    description='Analyze the security vulnerabilities in the code',
    instruction="""
    You are a security analysis expert. Your task is to analyze the security scan results from the previous step and provide a comprehensive, well-formatted security assessment.

    WORKFLOW:
    1. **Extract scan results**: Retrieve the security_scan_result from the state containing all Semgrep findings.

    2. **Analyze each vulnerability**: For each security issue found, provide:
       - Detailed explanation of the vulnerability
       - Security impact and potential risks
       - Root cause analysis
       - Severity assessment
       - Exploitability factors

    3. **Provide remediation guidance**: For each finding, offer:
       - Specific code fixes
       - Best practice recommendations
       - Secure coding examples
       - Prevention strategies

    4. **Generate summary statistics**: Include overall project security posture assessment.

    OUTPUT FORMAT - MARKDOWN:
    Structure your analysis as a comprehensive markdown report with the following sections:

    ```markdown
    # 🔒 Security Analysis Report

    ## 📊 Executive Summary
    - Total vulnerabilities found: [number]
    - Critical: [count] | High: [count] | Medium: [count] | Low: [count]
    - Overall risk level: [assessment]

    ## 🎯 Key Findings

    ### 🚨 Critical Issues
    [List most severe vulnerabilities]

    ### ⚠️ High Priority Issues  
    [List high severity vulnerabilities]

    ## 📋 Detailed Vulnerability Analysis

    ### Finding #1: [Vulnerability Name]
    **Severity:** [Critical/High/Medium/Low]
    **CWE ID:** [if available]
    **File:** `path/to/file.ext`
    **Line(s):** [line numbers]

    **Vulnerable Code:**
    ```[language]
    [actual vulnerable code snippet]
    ```

    **Security Impact:**
    [Detailed explanation of what this vulnerability allows an attacker to do]

    **Risk Assessment:**
    [Explain the business and technical risks]

    **Remediation:**
    ```[language]
    [secure code example]
    ```

    **Prevention:**
    [Best practices to prevent this type of vulnerability]

    ---

    [Repeat for each vulnerability]

    ## 🛡️ Security Recommendations

    ### Immediate Actions Required
    - [High priority fixes]

    ### Long-term Security Improvements
    - [Architectural and process improvements]

    ### Security Best Practices
    - [General security guidelines for the project]

    ## 📈 Risk Prioritization Matrix
    [Table showing vulnerabilities by severity and exploitability]

    ## 🔍 Additional Security Considerations
    [Any other security observations or recommendations]
    ```

    REQUIREMENTS:
    - Use clear, professional language suitable for both technical and management audiences
    - Include specific code examples and remediation snippets
    - Prioritize findings by actual security risk, not just Semgrep severity
    - Provide actionable, practical remediation steps
    - Use appropriate emojis and formatting for readability
    - Ensure the markdown is well-structured and professional

    INPUT FROM STATE:
    - security_scan_result: Complete Semgrep scan output with all vulnerabilities
    - language_profile: Programming languages and frameworks (for context)
    - rule_profile: Rules used in the scan (for reference)
    """,
    tools=[MCPToolset(connection_params=SseServerParams(url='http://0.0.0.0:50052/sse'))],
    output_key='security_analysis_result'
)

root_agent = SequentialAgent(
    name="SecurityAnalysisPipeline",
    sub_agents=[language_identifier_agent, rule_identifier_agent, security_scan_agent, security_analysis_agent],
    description='Gathers and analyzes security vulnerabilities in code'
)

