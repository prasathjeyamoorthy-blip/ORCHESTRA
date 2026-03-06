import time
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from PIL import Image, ImageTk
from playwright.sync_api import sync_playwright

class TNeSevaiBot:
    def __init__(self, root):
        self.root = root
        self.root.title("TNeSevai Automation Assistant")
        self.root.geometry("400x800")  # Slightly taller for DOB

        # --- Variables ---
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.can_var = tk.StringVar()
        self.aadhar_var = tk.StringVar()
        self.dob_var = tk.StringVar()       # <--- ADDED BACK
        self.captcha_input_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready to start")
        
        # Threading Events
        self.captcha_submitted_event = threading.Event()

        # --- UI Layout ---
        self.create_widgets()

    def create_widgets(self):
        # Title
        tk.Label(self.root, text="TNeSevai Login", font=("Arial", 16, "bold")).pack(pady=10)
        tk.Label(self.root, textvariable=self.status_var, fg="blue", wraplength=350).pack(pady=5)

        # Credentials Section
        frame_creds = tk.Frame(self.root, padx=20, pady=10)
        frame_creds.pack(fill="x")

        tk.Label(frame_creds, text="Username:").pack(anchor="w")
        tk.Entry(frame_creds, textvariable=self.username_var).pack(fill="x", pady=5)

        tk.Label(frame_creds, text="Password:").pack(anchor="w")
        tk.Entry(frame_creds, textvariable=self.password_var, show="*").pack(fill="x", pady=5)

        # CAN Number Input
        tk.Label(frame_creds, text="CAN Number (for Search):").pack(anchor="w", pady=(10, 0))
        tk.Entry(frame_creds, textvariable=self.can_var).pack(fill="x", pady=5)

        # Aadhaar Input
        tk.Label(frame_creds, text="Aadhaar Number (for OTP):").pack(anchor="w", pady=(5, 0))
        tk.Entry(frame_creds, textvariable=self.aadhar_var).pack(fill="x", pady=5)

        # --- DOB Input (Restored) ---
        tk.Label(frame_creds, text="Applicant DOB (DD/MM/YYYY):").pack(anchor="w", pady=(5, 0))
        tk.Entry(frame_creds, textvariable=self.dob_var).pack(fill="x", pady=5)

        # Start Button
        self.btn_start = tk.Button(self.root, text="Start Browser", bg="green", fg="white", command=self.start_automation_thread)
        self.btn_start.pack(pady=10, fill="x", padx=20)

        # Separator
        tk.Frame(self.root, height=2, bd=1, relief="sunken").pack(fill="x", padx=10, pady=10)

        # Captcha Section
        self.frame_captcha = tk.Frame(self.root)
        self.lbl_captcha_img = tk.Label(self.frame_captcha, text="[Captcha will appear here]")
        self.lbl_captcha_img.pack(pady=5)
        
        tk.Label(self.frame_captcha, text="Enter Captcha Text:").pack()
        self.entry_captcha = tk.Entry(self.frame_captcha, textvariable=self.captcha_input_var, font=("Arial", 12))
        self.entry_captcha.pack(pady=5)
        
        self.btn_submit_captcha = tk.Button(self.frame_captcha, text="Submit Captcha", bg="orange", command=self.submit_captcha)
        self.btn_submit_captcha.pack(pady=10, fill="x")

    def log(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def show_captcha_section(self, image_path):
        try:
            img = Image.open(image_path)
            img = img.resize((200, 60), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.lbl_captcha_img.config(image=photo, text="")
            self.lbl_captcha_img.image = photo 
            self.frame_captcha.pack(fill="x", padx=20)
            self.entry_captcha.focus_set()
        except Exception as e:
            self.log(f"Error loading captcha image: {e}")

    def submit_captcha(self):
        if not self.captcha_input_var.get():
            messagebox.showwarning("Input Required", "Please enter the captcha text.")
            return
        self.captcha_submitted_event.set()

    def start_automation_thread(self):
        if not self.username_var.get() or not self.password_var.get():
            messagebox.showerror("Error", "Please enter username/password")
            return
        if not self.can_var.get() or not self.dob_var.get():
            messagebox.showerror("Error", "Please enter CAN and DOB")
            return
            
        self.btn_start.config(state="disabled")
        self.captcha_submitted_event.clear()
        t = threading.Thread(target=self.run_playwright_logic)
        t.daemon = True 
        t.start()

    def format_date_for_injection(self, date_str):
        """Converts 25/02/2026 or 25-02-2026 to 25-Feb-2026"""
        try:
            # Try parsing with slashes or dashes
            for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    # Convert to DD-Mon-YYYY (e.g. 25-Feb-2026)
                    return dt.strftime("%d-%b-%Y")
                except ValueError:
                    continue
            return date_str # Return original if parse fails (fallback)
        except:
            return date_str

    def run_playwright_logic(self):
        try:
            with sync_playwright() as playwright:
                self.log("Launching Browser...")
                browser = playwright.chromium.launch(headless=False, slow_mo=500)
                context = browser.new_context()
                page = context.new_page()

                # --- Login ---
                self.log("Navigating to TNeSevai...")
                page.goto("https://www.tnesevai.tn.gov.in/")
                page.get_by_role("link", name="English Version").click()
                page.get_by_role("button", name="Citizen Login").click()

                page.get_by_role("textbox", name="User Name").fill(self.username_var.get())
                page.get_by_role("textbox", name="Password").fill(self.password_var.get())

                # --- Captcha ---
                self.log("Locating Captcha...")
                try:
                    captcha_img_element = page.locator("#captcha_image, img[src*='Captcha'], img[src*='captcha']").first
                    captcha_path = "temp_captcha.png"
                    captcha_img_element.screenshot(path=captcha_path)
                    
                    self.log("Waiting for user captcha input...")
                    self.root.after(0, lambda: self.show_captcha_section(captcha_path))
                    self.captcha_submitted_event.wait()

                    self.log("Submitting Captcha...")
                    user_captcha = self.captcha_input_var.get()
                    page.get_by_role("textbox", name="Enter Captcha Code").fill(user_captcha)
                    self.root.after(0, self.frame_captcha.pack_forget)
                except Exception as e:
                    print(e)
                    self.captcha_submitted_event.wait()

                with page.expect_navigation(timeout=60000):
                    page.get_by_role("button", name="Login").click()

                # --- Navigation ---
                self.log("Navigating to Revenue Dept...")
                page.wait_for_load_state("networkidle")
                page.get_by_role("link", name="Revenue Department").click()
                page.get_by_role("link", name="2", exact=True).click()
                
                with page.expect_popup() as page1_info:
                    page.get_by_role("link", name="REV-116 Residence certificate").click()
                
                page1 = page1_info.value
                page1.wait_for_load_state("domcontentloaded")
                
                self.log("Waiting for popup to stabilize...")
                time.sleep(2) 

                self.log("Processing Residence Certificate...")
                page1.get_by_role("button", name="Proceed").click()
                
                # --- CAN Search ---
                self.log("Searching CAN Number...")
                page1.locator("[id=\"statusform:aadhar\"]").click()
                page1.locator("[id=\"statusform:aadhar\"]").fill(self.can_var.get()) 
                page1.get_by_role("button", name="Search").click()
                page1.wait_for_timeout(2000) 
                
                try:
                    page1.get_by_label("").check() 
                except:
                    pass 

                # --- Aadhaar Fill ---
                self.log("Filling Aadhaar...")
                page1.locator("[id=\"statusform:citAadharNo\"]").click()
                page1.locator("[id=\"statusform:citAadharNo\"]").fill(self.aadhar_var.get())
                
                # --- ⚡ DATE INJECTION START ⚡ ---
                self.log("Injecting DOB...")
                
                # 1. Format the date correctly (DD-Mon-YYYY)
                raw_dob = self.dob_var.get()
                formatted_dob = self.format_date_for_injection(raw_dob)
                print(f"Injecting DOB: {formatted_dob}")

                # 2. Inject using the ID from your screenshot
                page1.evaluate(f"""
                    var dobField = document.getElementById('statusform:citAapDOBInputDate');
                    if (dobField) {{
                        dobField.removeAttribute('readonly');
                        dobField.removeAttribute('disabled');
                        dobField.value = '{formatted_dob}';
                        dobField.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        dobField.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }} else {{
                        console.log("DOB Field not found!");
                    }}
                """)
                # --- ⚡ DATE INJECTION END ⚡ ---

                # --- Generate OTP Click ---
                self.log("Clicking Generate OTP...")
                page1.get_by_role("button", name="Generate OTP").click()

                self.log("OTP Requested! Browser closing in 10s...")
                time.sleep(10)
                browser.close()
                self.root.after(0, lambda: self.btn_start.config(state="normal"))

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Automation Error", str(e))
            self.root.after(0, lambda: self.btn_start.config(state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = TNeSevaiBot(root)
    root.mainloop()