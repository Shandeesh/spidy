import os
import sys
import base64
import io

# Flag to track if dependencies are ready
DEPENDENCIES_INSTALLED = False
IMPORT_ERROR = None

try:
    import torch
    from diffusers import StableDiffusionPipeline
    # Also verify transformers and accelerate which are implicit deps
    import transformers
    import accelerate 
    DEPENDENCIES_INSTALLED = True
except Exception as e:
    IMPORT_ERROR = str(e)
    sys.stderr.write(f"[WARN] Local SD Import Failed: {e}\n")
    pass

class LocalSD:
    def __init__(self):
        self.pipe = None
        self.model_id = "runwayml/stable-diffusion-v1-5"
        self.device = "cuda" if (DEPENDENCIES_INSTALLED and torch.cuda.is_available()) else "cpu"
        
    def initialize(self):
        """Loads the model. This is heavy, so call only when needed."""
        """Loads the model. This is heavy, so call only when needed."""
        if not DEPENDENCIES_INSTALLED:
            return f"Error: Missing dependencies. Reason: {IMPORT_ERROR}. FIX: pip install torch diffusers transformers accelerate"
            
        if not self.pipe:
            print(f"[INFO] Loading Stable Diffusion ({self.device})...")
            try:
                # Use float16 for GPU to save memory
                if self.device == "cuda":
                    self.pipe = StableDiffusionPipeline.from_pretrained(
                        self.model_id, 
                        torch_dtype=torch.float16,
                        use_safetensors=True
                    )
                    self.pipe = self.pipe.to("cuda")
                else:
                    self.pipe = StableDiffusionPipeline.from_pretrained(self.model_id, use_safetensors=True)
                    self.pipe = self.pipe.to("cpu")
                    
                # Enable memory slicing for lower VRAM usage
                self.pipe.enable_attention_slicing()
                print("[INFO] Model Loaded Successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to load SD Model: {e}")
                return str(e)
        return True

    def generate(self, prompt):
        """Generates an image and returns Base64 string."""
        init_status = self.initialize()
        if init_status is not True:
            return init_status

        try:
            print(f"[INFO] Generating Local Image: {prompt}")
            
            # Optimization Settings based on Device
            if self.device == "cuda":
                # Smart Fallback Strategy for Resolution
                resolutions = [
                     (1920, 1080, "1080p FHD"), 
                     (1280, 720, "720p HD"), 
                     (512, 512, "512p Standard")
                ]
                
                image = None
                last_error = None
                
                for width, height, label in resolutions:
                    try:
                        print(f"[INFO] Attempting Generation at {label} ({width}x{height})...")
                        # 30 steps for high quality
                        image = self.pipe(prompt, num_inference_steps=30, height=height, width=width).images[0]
                        print(f"[INFO] Success at {label}!")
                        break # Success
                    except Exception as e:
                        last_error = e
                        print(f"[WARN] Failed at {label}. Error: {e}")
                        # Clear cache to try and free VRAM for next attempt
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            import gc
                            gc.collect()
                        continue
                
                if image is None:
                    raise Exception(f"All resolution attempts failed. Last error: {last_error}")
                    
            else:
                # CPU: Low Quality, Fast-ish
                steps = 12
                res = 320
                image = self.pipe(prompt, num_inference_steps=steps, height=res, width=res).images[0]
            
            # Convert to Base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # MEMORY MANAGEMENT
            # If on CPU, unload immediately to prevent lag.
            # If on GPU, keep loaded for speed (user has 6GB VRAM, sufficient for fp16 512x512)
            if self.device == "cpu":
                del self.pipe
                self.pipe = None
                import gc
                gc.collect()
                print("[INFO] Model Unloaded from RAM (CPU Mode).")
            else:
                # Optional: Could implement a timer to unload after X minutes of inactivity
                # For now, keep it loaded as requested for speed.
                print("[INFO] Model kept in VRAM for fast subsequent generation.")
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            # Ensure cleanup on error
            if self.pipe:
                 del self.pipe
                 self.pipe = None
                 if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                 import gc
                 gc.collect()
            return f"Generation Failed: {e}"

# Singleton instance
local_sd_engine = LocalSD()
