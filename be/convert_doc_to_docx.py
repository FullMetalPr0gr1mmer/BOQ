"""
Convert .doc files to .docx format using Windows COM automation.

This script requires Microsoft Word to be installed on Windows.
"""

import os
import sys

try:
    import win32com.client
except ImportError:
    print("Error: pywin32 is not installed.")
    print("Install it with: pip install pywin32")
    sys.exit(1)


def convert_doc_to_docx(doc_path, docx_path=None):
    """
    Convert a .doc file to .docx format.

    Args:
        doc_path: Path to the input .doc file
        docx_path: Path to the output .docx file (optional)
    """
    # Get absolute path
    doc_path = os.path.abspath(doc_path)

    if not os.path.exists(doc_path):
        print(f"Error: File not found: {doc_path}")
        return False

    # Generate output path if not provided
    if docx_path is None:
        base_name = os.path.splitext(doc_path)[0]
        docx_path = f"{base_name}.docx"
    else:
        docx_path = os.path.abspath(docx_path)

    try:
        # Create Word application instance
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False

        # Open the document
        print(f"Opening: {doc_path}")
        doc = word.Documents.Open(doc_path)

        # Save as .docx (format 16 is for .docx)
        print(f"Converting to: {docx_path}")
        doc.SaveAs2(docx_path, FileFormat=16)

        # Close the document
        doc.Close()
        word.Quit()

        print(f"[OK] Successfully converted to: {docx_path}")
        return True

    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        try:
            word.Quit()
        except:
            pass
        return False


if __name__ == "__main__":
    # Convert the PAC template
    template_doc = os.path.join(os.path.dirname(__file__), "templates", "PAC_SOPHIA 4_R4.doc")
    template_docx = os.path.join(os.path.dirname(__file__), "templates", "PAC_Template.docx")

    if not os.path.exists(template_doc):
        print(f"Error: Template not found: {template_doc}")
        sys.exit(1)

    print("Converting PAC template from .doc to .docx...")
    if convert_doc_to_docx(template_doc, template_docx):
        print("\n[SUCCESS] Conversion complete!")
        print(f"Template ready at: {template_docx}")
    else:
        print("\n[FAILED] Conversion failed!")
        sys.exit(1)
