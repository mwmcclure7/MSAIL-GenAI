import pymupdf

def extract_text_from_pdf(pdf_path):
    full_text = ""
    
    with pymupdf.open(pdf_path) as doc:
        # Loop through every page
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract plain text (best for natural reading order)
            page_text = page.get_text("text")
            full_text += f"\n\n--- Page {page_num + 1} ---\n" + page_text
    
    return full_text

# Usage example
pdf_file = "example.pdf"
extracted = extract_text_from_pdf(pdf_file)

print(extracted)

