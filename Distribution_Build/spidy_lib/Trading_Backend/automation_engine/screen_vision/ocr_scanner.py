import pyautogui
import pytesseract
from PIL import Image, ImageOps
import sys
import os
import json

# NOTE: Tesseract-OCR executable path must be in PATH or set here
# If user doesn't have it, we fallback to a message
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class SpidyVision:
    def __init__(self, tesseract_cmd=None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def capture_screen(self, save_path="screenshot.png", region=None):
        """
        Takes a screenshot of the screen.
        :param save_path: Path to save the screenshot.
        :param region: Optional tuple (x, y, width, height) to capture a specific area.
        """
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            return save_path
        except Exception as e:
            return None

    def read_text(self, image_path="screenshot.png", preprocess=True):
        """
        Extracts text from the image using Tesseract OCR.
        :param image_path: Path to the image file.
        :param preprocess: Whether to apply basic preprocessing (grayscale) to improve accuracy.
        """
        if not os.path.exists(image_path):
            return "Error: Image file not found."

        try:
            img = Image.open(image_path)
            
            if preprocess:
                # Convert to grayscale to improve OCR accuracy
                img = ImageOps.grayscale(img)
                # Additional preprocessing like thresholding could be added here
            
            text = pytesseract.image_to_string(img)
            return text.strip()
        except FileNotFoundError:
            return "Error: Image file not found."
        except Exception as e:
            return f"Error reading text (Is Tesseract Installed?): {e}"

    def cleanup(self, image_path):
        """Removes the temporary image file."""
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            pass

if __name__ == "__main__":
    vision = SpidyVision()
    result = {}
    
    # Simple argument parsing for testing region or debug
    # Usage: python ocr_scanner.py [x y w h]
    region = None
    if len(sys.argv) == 5:
        try:
            region = tuple(map(int, sys.argv[1:5]))
        except ValueError:
            pass

    try:
        img_path = vision.capture_screen(region=region)
        if img_path:
            text = vision.read_text(img_path)
            
            result = {
                "status": "success",
                "image_path": img_path,
                "text": text if text else "",
                "region": region
            }
            
            # Cleanup for clean execution, comment out if debugging is needed
            vision.cleanup(img_path) 
        else:
            result = {
                "status": "error",
                "message": "Failed to capture screen."
            }
            
    except Exception as e:
        result = {
            "status": "error",
            "message": str(e)
        }
    
    print(json.dumps(result))
