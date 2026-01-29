"""
Web Vulnerability Identifier
Fetches HTML, CSS, and JavaScript from a URL and uses Groq LLM to identify potential vulnerabilities.
Filters content for security-relevant patterns to stay within token limits.
"""

import argparse
import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Import Groq SDK
from groq import Groq

# Maximum characters to send to LLM (roughly 4 chars per token, targeting ~6000 tokens)
MAX_CONTENT_CHARS = 20000

# ----------------------------------------------------------------------------------
#               MOST OF THIS CODE IS FOR FETCHING THE WEBSITE CONTENT
#                       SCROLL DOWN TO SEE GROQ IN USE
# ----------------------------------------------------------------------------------

# Patterns that indicate security-relevant code sections
SECURITY_PATTERNS = [
    # Authentication & Authorization
    r'password', r'passwd', r'login', r'logout', r'auth', r'token', r'session',
    r'cookie', r'jwt', r'bearer', r'credential', r'secret', r'api[_-]?key',
    
    # User Input & Forms
    r'<form', r'<input', r'<textarea', r'action=', r'method=', r'submit',
    r'onsubmit', r'formaction', r'enctype',
    
    # Dangerous JavaScript patterns
    r'eval\s*\(', r'innerHTML', r'outerHTML', r'document\.write',
    r'\.html\s*\(', r'setTimeout\s*\(', r'setInterval\s*\(',
    r'Function\s*\(', r'exec\s*\(', r'new\s+Function',
    
    # DOM manipulation
    r'getElementById', r'querySelector', r'getElementsBy', r'\.src\s*=',
    r'\.href\s*=', r'location\s*=', r'location\.', r'window\.open',
    
    # URL & redirect patterns  
    r'redirect', r'url\s*=', r'next\s*=', r'return\s*=', r'goto',
    r'window\.location', r'document\.location',
    
    # AJAX & API calls
    r'fetch\s*\(', r'XMLHttpRequest', r'\.ajax', r'axios', r'\$\.get',
    r'\$\.post', r'httpClient', r'endpoint', r'/api/',
    
    # SQL-like patterns
    r'SELECT', r'INSERT', r'UPDATE', r'DELETE', r'WHERE', r'query',
    
    # Sensitive data patterns
    r'credit', r'card', r'ssn', r'social', r'email', r'phone',
    r'address', r'private', r'secret', r'admin',
    
    # Security headers & CSP
    r'X-Frame-Options', r'Content-Security-Policy', r'X-XSS-Protection',
    r'Strict-Transport', r'Access-Control',
    
    # Event handlers (potential XSS vectors)
    r'onclick', r'onerror', r'onload', r'onmouseover', r'onfocus',
    r'onblur', r'onchange', r'onkeyup', r'onkeydown',
    
    # Comments that might leak info
    r'TODO', r'FIXME', r'HACK', r'XXX', r'DEBUG', r'<!--',
    
    # Framework-specific sensitive patterns
    r'__NEXT_DATA__', r'__NUXT__', r'ng-', r'v-model', r'v-html',
]

# Compile patterns for efficiency
SECURITY_REGEX = re.compile('|'.join(SECURITY_PATTERNS), re.IGNORECASE)


def fetch_page_content(url: str) -> tuple[str, BeautifulSoup]:
    """Fetch the HTML content of a page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text, BeautifulSoup(response.text, "html.parser")


def extract_security_relevant_lines(content: str, context_lines: int = 2) -> str:
    """Extract only lines that contain security-relevant patterns with context."""
    if not content:
        return ""
    
    lines = content.split('\n')
    relevant_indices = set()
    
    for i, line in enumerate(lines):
        if SECURITY_REGEX.search(line):
            # Add the matching line and surrounding context
            for j in range(max(0, i - context_lines), min(len(lines), i + context_lines + 1)):
                relevant_indices.add(j)
    
    if not relevant_indices:
        return ""
    
    # Build output with line numbers for context
    result_lines = []
    sorted_indices = sorted(relevant_indices)
    prev_idx = -2
    
    for idx in sorted_indices:
        if idx > prev_idx + 1:
            result_lines.append(f"... [line {idx + 1}]")
        result_lines.append(f"{idx + 1}: {lines[idx]}")
        prev_idx = idx
    
    return '\n'.join(result_lines)


def extract_inline_css(soup: BeautifulSoup) -> list[str]:
    """Extract inline CSS from <style> tags."""
    styles = []
    for style_tag in soup.find_all("style"):
        if style_tag.string:
            styles.append(style_tag.string)
    return styles


def extract_external_css(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Fetch external CSS files linked in the page."""
    css_files = []
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            css_url = urljoin(base_url, href)
            try:
                response = requests.get(css_url, timeout=15)
                response.raise_for_status()
                css_files.append({"url": css_url, "content": response.text})
            except requests.RequestException as e:
                css_files.append({"url": css_url, "error": str(e)})
    return css_files


def extract_inline_javascript(soup: BeautifulSoup) -> list[str]:
    """Extract inline JavaScript from <script> tags."""
    scripts = []
    for script_tag in soup.find_all("script"):
        if script_tag.string and not script_tag.get("src"):
            scripts.append(script_tag.string)
    return scripts


def extract_external_javascript(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Fetch external JavaScript files linked in the page."""
    js_files = []
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            js_url = urljoin(base_url, src)
            try:
                response = requests.get(js_url, timeout=15)
                response.raise_for_status()
                js_files.append({"url": js_url, "content": response.text})
            except requests.RequestException as e:
                js_files.append({"url": js_url, "error": str(e)})
    return js_files


def extract_forms(soup: BeautifulSoup) -> list[dict]:
    """Extract form information for vulnerability analysis."""
    forms = []
    for form in soup.find_all("form"):
        form_data = {
            "action": form.get("action", ""),
            "method": form.get("method", "GET").upper(),
            "inputs": [],
        }
        for input_tag in form.find_all(["input", "textarea", "select"]):
            form_data["inputs"].append({
                "name": input_tag.get("name", ""),
                "type": input_tag.get("type", "text"),
                "id": input_tag.get("id", ""),
            })
        forms.append(form_data)
    return forms


def extract_meta_and_headers(soup: BeautifulSoup) -> dict:
    """Extract meta tags and other security-relevant header info."""
    meta_info = {}
    
    # Meta tags
    for meta in soup.find_all("meta"):
        name = meta.get("name", meta.get("property", meta.get("http-equiv", "")))
        content = meta.get("content", "")
        if name and content:
            meta_info[name] = content
    
    # Links (for CSP, etc.)
    links = []
    for link in soup.find_all("link"):
        links.append({
            "rel": link.get("rel", []),
            "href": link.get("href", ""),
        })
    
    return {"meta_tags": meta_info, "links": links[:10]}  # Limit links


def compile_website_content(url: str) -> dict:
    """Compile all website content for analysis."""
    print(f"Fetching content from: {url}")
    
    html_content, soup = fetch_page_content(url)
    
    print("Extracting meta information...")
    meta_info = extract_meta_and_headers(soup)
    
    print("Extracting inline CSS...")
    inline_css = extract_inline_css(soup)
    
    print("Fetching external CSS (skipping for efficiency)...")
    # Skip external CSS as it rarely contains security issues
    external_css = []
    
    print("Extracting inline JavaScript...")
    inline_js = extract_inline_javascript(soup)
    
    print("Fetching external JavaScript...")
    external_js = extract_external_javascript(soup, url)
    
    print("Extracting form information...")
    forms = extract_forms(soup)
    
    return {
        "url": url,
        "html": html_content,
        "meta_info": meta_info,
        "inline_css": inline_css,
        "external_css": external_css,
        "inline_javascript": inline_js,
        "external_javascript": external_js,
        "forms": forms,
    }


def format_content_for_llm(website_data: dict) -> str:
    """Format the website content for LLM analysis, filtering for security-relevant content."""
    sections = []
    char_count = 0
    char_limit = MAX_CONTENT_CHARS
    
    def add_section(title: str, content: str, max_chars: int = 5000) -> bool:
        nonlocal char_count
        if char_count >= char_limit:
            return False
        remaining = char_limit - char_count
        truncated = content[:min(max_chars, remaining)]
        if truncated:
            sections.append(f"\n## {title}\n{truncated}")
            char_count += len(truncated) + len(title) + 10
        return True
    
    # Forms are critical - always include first
    if website_data["forms"]:
        form_str = ""
        for i, form in enumerate(website_data["forms"], 1):
            form_str += f"\nForm {i}: action='{form['action']}' method='{form['method']}'\n"
            form_str += f"  Inputs: {form['inputs']}\n"
        add_section("FORMS", form_str, 2000)
    
    # Meta tags (security headers, etc.)
    if website_data.get("meta_info"):
        meta_str = str(website_data["meta_info"])
        add_section("META TAGS & HEADERS", meta_str, 1000)
    
    # Security-relevant HTML patterns
    html_relevant = extract_security_relevant_lines(website_data["html"], context_lines=1)
    if html_relevant:
        add_section("HTML (Security-Relevant Lines)", html_relevant, 4000)
    
    # Inline JavaScript - most important for XSS and other vulns
    if website_data["inline_javascript"]:
        for i, js in enumerate(website_data["inline_javascript"], 1):
            js_relevant = extract_security_relevant_lines(js, context_lines=2)
            if js_relevant:
                if not add_section(f"INLINE JS BLOCK {i}", js_relevant, 3000):
                    break
    
    # External JavaScript - filter for relevant lines
    if website_data["external_javascript"]:
        for js_file in website_data["external_javascript"]:
            if "content" in js_file:
                js_relevant = extract_security_relevant_lines(js_file["content"], context_lines=2)
                if js_relevant:
                    url_short = js_file["url"].split("/")[-1][:30]
                    if not add_section(f"EXTERNAL JS: {url_short}", js_relevant, 3000):
                        break
    
    # Inline CSS (rarely relevant, but check for url() patterns)
    if website_data["inline_css"]:
        for i, css in enumerate(website_data["inline_css"], 1):
            css_relevant = extract_security_relevant_lines(css, context_lines=1)
            if css_relevant:
                if not add_section(f"INLINE CSS {i}", css_relevant, 1000):
                    break
    
    result = '\n'.join(sections)
    print(f"\nFiltered content: {len(result)} characters (limit: {char_limit})")
    return result


# ----------------------------------------------------------------------------------
#               THIS IS WHERE GROQ IS USED TO ANALYZE THE WEBSITE
# ----------------------------------------------------------------------------------
def analyze_with_groq(website_content: str, url: str) -> str:
    """Send website content to Groq LLM for vulnerability analysis."""
    
    # Initialize Groq client
    client = Groq()
    
    # System prompt
    system_prompt = """You are a web security analyst. Analyze the provided code for vulnerabilities.

For each issue found, provide:
- Type (XSS, CSRF, SQLi, etc.)
- Severity (Critical/High/Medium/Low)
- Location (line number or code snippet)
- Description & Recommendation

Focus on: XSS, CSRF, injection, auth issues, exposed secrets, unsafe DOM manipulation, open redirects, missing security headers."""

    user_prompt = f"""Analyze this website content from {url}:

{website_content}

Report all security vulnerabilities found."""

    print("\nSending content to Groq for analysis...")
    print("This may take a moment...\n")
    
    # Send content to Groq for analysis
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # More reliable model with higher limits
        messages=[
            {"role": "system", "content": system_prompt}, # System prompt
            {"role": "user", "content": user_prompt}, # User prompt
        ],
        temperature=0.3, # Temperature
        max_tokens=4096, # Max tokens
    )
    
    # Return the response
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a website for potential security vulnerabilities using AI"
    )
    parser.add_argument("url", help="The URL of the website to analyze")
    parser.add_argument(
        "-o", "--output",
        help="Output file to save the analysis report (optional)",
        default=None
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output including fetched content"
    )
    
    args = parser.parse_args()
    url = args.url
    
    # Validate URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            print("Error: Invalid URL provided")
            sys.exit(1)
    except Exception as e:
        print(f"Error parsing URL: {e}")
        sys.exit(1)
    
    try:
        # Fetch website content
        website_data = compile_website_content(url)
        
        # Format for LLM (with security filtering)
        formatted_content = format_content_for_llm(website_data)
        
        if args.verbose:
            print("\n" + "=" * 60)
            print("FILTERED CONTENT SENT TO LLM")
            print("=" * 60)
            print(formatted_content[:3000] + "...\n" if len(formatted_content) > 3000 else formatted_content)
        
        # Analyze with Groq
        analysis = analyze_with_groq(formatted_content, url)
        
        # Output results
        print("=" * 60)
        print("VULNERABILITY ANALYSIS REPORT")
        print(f"Target: {url}")
        print("=" * 60)
        print(analysis)
        
        # Save to file if requested
        if args.output:
            with open(args.output, "w") as f:
                f.write(f"Vulnerability Analysis Report\n")
                f.write(f"Target: {url}\n")
                f.write("=" * 60 + "\n\n")
                f.write(analysis)
            print(f"\nReport saved to: {args.output}")
            
    except requests.RequestException as e:
        print(f"Error fetching website: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise


if __name__ == "__main__":
    main()
