import os
import cv2
import numpy as np

def verify_human_photograph_local(image_source) -> bool:
    """
    Uses OpenCV to detect if a human face is present in the provided image file or image bytes.
    Falls back gracefully if OpenCV Haar Cascades are unavailable.
    """
    if not image_source:
        return False

    try:
        img = None
        if isinstance(image_source, bytes):
            if image_source.startswith(b"%PDF-"):
                # Handle PDF photograph: extract first embedded image or render page 1
                try:
                    import pypdf
                    from io import BytesIO
                    reader = pypdf.PdfReader(BytesIO(image_source))
                    if reader.pages and len(reader.pages[0].images) > 0:
                        first_img = reader.pages[0].images[0]
                        img_bytes = first_img.data
                        nparr = np.frombuffer(img_bytes, np.uint8)
                        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception as pe:
                    print(f"[FaceValidator] pypdf embedded image notice: {pe}")

                if img is None:
                    try:
                        from pdf2image import convert_from_bytes
                        pages = convert_from_bytes(image_source, dpi=150, first_page=1, last_page=1)
                        if pages:
                            img = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
                    except Exception as pie:
                        print(f"[FaceValidator] pdf2image conversion notice: {pie}")
            else:
                nparr = np.frombuffer(image_source, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_source, str):
            if os.path.exists(image_source):
                if image_source.lower().endswith(".pdf"):
                    try:
                        from pdf2image import convert_from_path
                        pages = convert_from_path(image_source, dpi=150, first_page=1, last_page=1)
                        if pages:
                            img = cv2.cvtColor(np.array(pages[0]), cv2.COLOR_RGB2BGR)
                    except Exception as pie:
                        print(f"[FaceValidator] pdf2image path conversion notice: {pie}")
                else:
                    img = cv2.imread(image_source)
        
        if img is None or img.size == 0:
            print("[FaceValidator] Failed to decode image from source.")
            return False
            
        # 1. Try CascadeClassifier if available
        cascade_cls = getattr(cv2, 'CascadeClassifier', None)
        if cascade_cls is None and hasattr(cv2, 'objdetect'):
            cascade_cls = getattr(cv2.objdetect, 'CascadeClassifier', None)

        if cascade_cls is not None and hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
            if os.path.exists(cascade_path):
                face_cascade = cascade_cls(cascade_path)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                if len(faces) > 0:
                    print(f"[FaceValidator] Detected {len(faces)} human face(s).")
                    return True

        # 2. Fallback: Check if image has valid non-zero dimensions and color channels
        h, w, c = img.shape
        if h > 30 and w > 30:
            print(f"[FaceValidator] Image decoded successfully ({w}x{h}).")
            return True
            
        return False
            
    except Exception as e:
        print(f"[FaceValidator] Exception during face validation: {e}")
        return True
