
import sys
import subprocess

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
    from PIL import Image

def convert_to_ico(png_path, ico_path):
    print(f"Converting {png_path} -> {ico_path}")
    img = Image.open(png_path)
    
    # Create icon with multiple sizes for best quality
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print("Success!")

if __name__ == "__main__":
    import os
    
    base_dir = r"C:\Users\Shandeesh R P\spidy"
    logo_path = os.path.join(base_dir, "assets", "logo.png")
    
    # 1. Main App Icon
    app_icon_path = os.path.join(base_dir, "spidy_icon.ico")
    convert_to_ico(logo_path, app_icon_path)
    
    # 2. Web Favicon
    web_favicon_path = os.path.join(base_dir, "Member3_Frontend_UI", "dashboard_app", "public", "favicon.ico")
    # Ensure dir exists
    os.makedirs(os.path.dirname(web_favicon_path), exist_ok=True)
    convert_to_ico(logo_path, web_favicon_path)
