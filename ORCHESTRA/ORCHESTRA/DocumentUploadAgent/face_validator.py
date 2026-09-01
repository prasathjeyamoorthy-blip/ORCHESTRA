import cv2
import os
import numpy as np

def verify_human_photograph_local(image_source) -> bool:
    """
    Uses OpenCV's pre-trained Haar Cascades to detect if a human face is present
    in the provided image file or image bytes. Returns True if at least one face is found.
    """
    try:
        img = None
        if isinstance(image_source, bytes):
            nparr = np.frombuffer(image_source, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_source, str):
            if os.path.exists(image_source):
                img = cv2.imread(image_source)
        
        if img is None:
            print("[FaceValidator] Failed to decode image from source.")
            return False
            
        # Convert to grayscale for Haar Cascade
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load default predefined face detector cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        faces = face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        
        if len(faces) > 0:
            print(f"[FaceValidator] Detected {len(faces)} human face(s).")
            return True
        else:
            print("[FaceValidator] No human face detected.")
            return False
            
    except Exception as e:
        print(f"[FaceValidator] Exception during face validation: {e}")
        return False

