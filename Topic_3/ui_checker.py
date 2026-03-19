import base64
import json
import os
from groq import Groq
from playwright.sync_api import sync_playwright

def capture_screenshot(url, output_path):
    """Navigates to a URL and takes a full-page screenshot."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.screenshot(path=output_path, full_page=True)
            print(f"Successfully captured screenshot for {url}")
            success = True
        except Exception as e:
            print(f"Failed to capture {url}: {e}")
            success = False
        finally:
            browser.close()
        return success


# =======================================================================
#                              IMAGE ENCODING
# =======================================================================

def encode_image(image_path):
    """Encodes the image to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# =======================================================================
#                             SCAN SCREENSHOT
# =======================================================================

def analyze_ui_errors(base64_image, groq_client, model="meta-llama/llama-4-scout-17b-16e-instruct"):
    """Sends the image to Groq and requests structured JSON output."""
    
    # Define the JSON schema
    json_schema = {
        "name": "ui_error_analysis",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "has_errors": {
                    "type": "boolean",
                    "description": "True if any UI errors are found, False otherwise."
                },
                "errors": {
                    "type": "array",
                    "description": "List of identified UI errors.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "severity": {
                                "type": "string",
                                "enum": ["Severe", "Minor"],
                                "description": "Severe for cut off/broken parts. Minor for poor contrast/suggestions."
                            },
                            "description": {
                                "type": "string",
                                "description": "Detailed description of the UI error."
                            }
                        },
                        "required": ["severity", "description"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["has_errors", "errors"],
            "additionalProperties": False
        }
    }

    print("Analyzing screenshot with Groq Vision Model...")
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system", 
                "content": "You are an expert UI/UX auditor. Analyze the provided webpage screenshot for obvious UI errors. Classify elements that are broken, overlapping, cut-off, or completely unreadable as 'Severe'. Classify poor contrast, minor misalignment, or layout suggestions as 'Minor'. If the page looks perfectly fine, set has_errors to false and leave the errors array empty."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please provide a structured UI analysis for this screenshot."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": json_schema
        }
    )

    # Parse the AI's string output into JSON
    raw_content = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        print("Error: Could not parse JSON from the model's response.")
        return {"has_errors": False, "errors": []}

def main():
    client = Groq()
    
    print("Enter the URLs of the webpages you want to check (comma separated):")
    urls_input = input("> ")
    urls = [url.strip() for url in urls_input.split(",") if url.strip()]

    if not urls:
        print("No valid URLs provided. Exiting.")
        return

    os.makedirs("screenshots", exist_ok=True)

    for i, url in enumerate(urls):
        print(f"\n--- Scanning Page {i+1}/{len(urls)} ---")
        
        # Ensure standard formatting so Playwright knows how to route it
        if not url.startswith("http://") and not url.startswith("https://") and not url.startswith("file://"):
            url = "https://" + url

        screenshot_path = f"screenshots/page_{i}.png"
        
        if capture_screenshot(url, screenshot_path):
            base64_img = encode_image(screenshot_path)
            analysis = analyze_ui_errors(base64_img, client)
            
            # Print the structured results
            if analysis.get("has_errors"):
                found_errors = analysis.get("errors", [])
                print(f"Results for {url}: Found {len(found_errors)} issue(s).")
                for error in found_errors:
                    print(f"  [{error.get('severity')}] - {error.get('description')}")
            else:
                print(f"Results for {url}: No obvious UI errors detected. The page looks good!")
        else:
            print("Skipping AI analysis due to screenshot failure.")

if __name__ == "__main__":
    main()

