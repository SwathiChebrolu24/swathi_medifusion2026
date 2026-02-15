"""
Image preprocessing utilities for AI models.
"""
import io
from PIL import Image

# Try to import torch, but don't fail if it's not available
try:
    import torch
    from torchvision import transforms
    TORCH_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Warning: PyTorch not available in preprocessing ({e}). Preprocessing will be skipped.")
    torch = None
    transforms = None
    TORCH_AVAILABLE = False


def preprocess_xray_image(image_bytes: bytes, target_size=(224, 224)):
    """
    Preprocess X-ray image for pneumonia detection model.
    
    Args:
        image_bytes: Raw image bytes
        target_size: Target image size (width, height)
    
    Returns:
        Preprocessed tensor ready for model input
    """
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available, cannot preprocess image")
        return None
    
    # Load image from bytes
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    
    # Define preprocessing transforms
    transform = transforms.Compose([
        transforms.Resize(target_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    # Apply transforms
    tensor = transform(image)
    
    # Add batch dimension
    return tensor.unsqueeze(0)


def preprocess_xray_from_path(image_path: str, target_size=(224, 224)):
    """
    Preprocess X-ray image from file path.
    
    Args:
        image_path: Path to image file
        target_size: Target image size (width, height)
    
    Returns:
        Preprocessed tensor ready for model input
    """
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available, cannot preprocess image")
        return None
    
    # Load image
    image = Image.open(image_path).convert('RGB')
    
    # Define preprocessing transforms
    transform = transforms.Compose([
        transforms.Resize(target_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                           std=[0.229, 0.224, 0.225])
    ])
    
    # Apply transforms
    tensor = transform(image)
    
    # Add batch dimension
    return tensor.unsqueeze(0)
