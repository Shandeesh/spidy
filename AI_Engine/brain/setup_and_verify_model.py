import os
import sys

print("--- SPIDY AI: MANUAL MODEL INSTALLER & VERIFIER ---")
print("1. Checking Libraries...")

try:
    import torch
    from diffusers import StableDiffusionPipeline
    print("   [OK] Libraries found.")
except ImportError as e:
    print(f"   [ERROR] Missing libraries: {e}")
    print("   Run: pip install torch diffusers transformers accelerate")
    sys.exit(1)

print("\n2. Checking/Downloading AI Model (Stable Diffusion v1.5)...")
print("   NOTE: This looks for the model in your cache.")
print("   If missing, it will download ~4GB now. Please wait...")

try:
    model_id = "runwayml/stable-diffusion-v1-5"
    # Force loading to CPU to avoid CUDA OOM during setup if user has weak GPU
    # and to ensure compatibility.
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id, 
        use_safetensors=True
    )
    pipe = pipe.to("cpu")
    print("   [OK] Model loaded successfully!")
    
    print("\n3. Testing Generation (Quick Low-Res Test)...")
    pipe.safety_checker = None # Disable safety check for speed in test
    image = pipe("test image", num_inference_steps=1, height=64, width=64).images[0]
    output_path = os.path.join(os.getcwd(), "install_test_image.png")
    image.save(output_path)
    print(f"   [OK] Test image saved to: {output_path}")
    print("\n--- INSTALLATION COMPLETE: You can use Spidy to generate images now. ---")

except Exception as e:
    print(f"\n[CRITICAL ERROR] Model Setup Failed: {e}")
    print("Check your internet connection if downloading failed.")
