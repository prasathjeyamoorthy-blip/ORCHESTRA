import cv2
import os

def verify_human_photograph_local(image_path: str) -> bool:
    """
    Uses OpenCV's pre-trained Haar Cascades to detect if a human face is present
    in the provided image file. Returns True if at least one face is found.
    """
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return False
        
    try:
        # Load the image
        img = cv2.imread(image_path)
        if img is None:
            print("Failed to load image with cv2.")
            return False
            
        # Convert to grayscale for Haar Cascade
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load the default predefined face detector cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Execute detection
        # scaleFactor determines how much the image size is reduced at each image scale
        # minNeighbors determines how many neighbors each candidate rectangle should have to retain it
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        
        if len(faces) > 0:
            print(f"[FaceValidator] Detected {len(faces)} human face(s) in {image_path}.")
            return True
        else:
            print(f"[FaceValidator] No human face detected in {image_path}.")
            return False
            
    except Exception as e:
        print(f"[FaceValidator] Exception during face validation: {e}")
        return False
