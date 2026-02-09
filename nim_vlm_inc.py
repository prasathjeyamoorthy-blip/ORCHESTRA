from pdf2image import convert_from_path
import base64
import requests
import os
from dotenv import load_dotenv
load_dotenv()

POPPLER_PATH = r"C:\poppler-25.12.0\Library\bin"

from io import BytesIO


def pil_to_base64(img):
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()



def extract_from_pdf(pdf_path):
    pages = convert_from_path(
        pdf_path,
        dpi=300,
        poppler_path=POPPLER_PATH
    )

    outputs = []
    for i, page in enumerate(pages):
        print(f"Processing page {i+1}")
        result = run_vlm_from_pil(page)
        outputs.append(result)

    return outputs

def run_vlm_from_pil(image):
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
        "Content-Type": "application/json"
    }

    image_b64 = pil_to_base64(image)

    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "temperature": 0,
        "max_tokens": 800,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are an OCR + document understanding system.\n"
                            "Extract text and return ONLY valid JSON in this schema:\n"
                            "{\n"
                            "  \"certificate_type\": string,\n"
                            "  \"parent_name\": string,\n"
                            "  \"name\": string,\n"
                            "  \"address\": full address as string,\n"
                            "  \ door no\": door no as string,\n"
                            "  \"Street Name\": street name as string,\n"
                            "  \ Area\": area as string,\n"
                            "  \"date of issue\": string,\n"
                            "  \"issuing_authority\": string\n"
                            "  \"issuing_authority_name\": string\n"
                            "  \"Religion\": string\n"
                            "  \"Income\": int\n"
                            "  \"State\": string\n"
                            "  \"Taluk\": string\n"
                            "  \"Revenue Village\": string\n"
                            "  \"District\": string\n"
                            #"  \"Pincode\": int\n"
                            "}\n"
                            "If a field is missing, use null."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(invoke_url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def run_vlm(image_path):
    
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
        "Content-Type": "application/json"
    }

    image_b64 = image_to_base64(image_path)

    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all readable text from this document. "
                            "Then return structured fields like name, parent's name, address, date, certificate type."
                            "Return only required fields and dont return unwanted text"
                        )
                    },
                    {
                        "type": "image",
                        "image_base64": image_b64
                    }
                ]
            }
        ],
        "max_tokens": 800,
        "temperature": 0
    }

    response = requests.post(invoke_url, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    pdf_path = r"C:\Residence proj\agent2\docu\m_income.pdf"

    results = extract_from_pdf(pdf_path)

    print("\n--- EXTRACTED OUTPUT ---\n")
    for r in results:
        print(r)

