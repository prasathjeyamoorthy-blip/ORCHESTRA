const faqsEn = [
  { q: "What is a Residence Certificate?", a: "A Residence Certificate is an official document issued by the Tamil Nadu government through TNeGA e-Sevai portals, certifying that a person resides at a particular address in Tamil Nadu." },
  { q: "Who can apply for a Residence Certificate?", a: "Any resident of Tamil Nadu who has been living at their current address can apply. You must have valid address proof documents such as Aadhaar card, Ration card, or Driving License." },
  { q: "What documents are required?", a: "You need: (1) Aadhaar Card, (2) Ration Card, (3) Applicant Photograph, and (4) Driving License as address proof. All documents should be clear and legible." },
  { q: "How long does the process take?", a: "The automated application process typically takes 5–10 minutes once all documents are uploaded. Certificate issuance by the authority may take 3–7 working days." },
  { q: "What is a CAN Number?", a: "CAN (Citizen Account Number) is a unique identifier assigned to citizens on the TNeGA e-Sevai portal. It is optional but helps in faster processing." },
  { q: "What format should my documents be in?", a: "Documents can be uploaded as PDF, JPG, or PNG files. Maximum file size is 5 MB per document. Ensure the document is clearly visible and not blurred." },
  { q: "Is my data secure?", a: "Yes. All data is processed locally and submitted directly to the official TNeGA e-Sevai portal. No personal data is stored on our servers beyond the session." },
  { q: "What if the automation fails?", a: "If automation encounters an error, you will be notified in the chat. You can retry or visit the TNeGA e-Sevai portal directly at www.tnesevai.tn.gov.in." },
];

const faqsTa = [
  { q: "குடியிருப்பு சான்றிதழ் என்றால் என்ன?", a: "குடியிருப்பு சான்றிதழ் என்பது தமிழ்நாட்டில் ஒரு குறிப்பிட்ட முகவரியில் ஒருவர் வசிக்கிறார் என்பதைச் சான்றளிக்க TNeGA இ-சேவை மூலம் வழங்கப்படும் அதிகாரப்பூர்வ ஆவணமாகும்." },
  { q: "குடியிருப்பு சான்றிதழுக்கு யார் விண்ணப்பிக்கலாம்?", a: "தற்போதைய முகவரியில் வசிக்கும் தமிழ்நாட்டின் அனைத்து குடிமக்களும் விண்ணப்பிக்கலாம். ஆதார் அட்டை, குடும்ப அட்டை போன்ற செல்லுபடியாகும் முகவரி சான்றுகள் இருக்க வேண்டும்." },
  { q: "என்னென்ன ஆவணங்கள் தேவை?", a: "(1) ஆதார் அட்டை, (2) குடும்ப அட்டை, (3) விண்ணப்பதாரர் புகைப்படம், மற்றும் (4) ஓட்டுநர் உரிமம் ஆகியவை தேவை." },
  { q: "செயலாக்கத்திற்கு எவ்வளவு காலம் ஆகும்?", a: "ஆவணங்கள் பதிவேற்றப்பட்டதும் தானியங்கி முறை 5–10 நிமிடங்களில் முடிவடையும். சான்றிதழ் ஒப்புதல் பெற 3–7 வேலை நாட்கள் ஆகலாம்." },
  { q: "CAN எண் என்றால் என்ன?", a: "CAN (Citizen Account Number) என்பது குடிமக்களுக்கான தனித்துவமான கணக்கு எண் ஆகும்." },
  { q: "ஆவணங்கள் எந்த வடிவத்தில் இருக்க வேண்டும்?", a: "PDF, JPG, அல்லது PNG வடிவில் பதிவேற்றலாம். அதிகபட்ச அளவு 5 MB ஆகும்." },
  { q: "எனது தரவு பாதுகாப்பானதா?", a: "ஆம். அனைத்து தரவுகளும் பாதுகாப்பாக TNeGA இ-சேவை போர்ட்டலில் மட்டுமே சமர்ப்பிக்கப்படுகின்றன." },
  { q: "தானியங்கி முறையில் பிழை ஏற்பட்டால் என்ன செய்வது?", a: "பிழை ஏற்பட்டால் அரட்டையில் அறிவிக்கப்படும். www.tnesevai.tn.gov.in தளத்திலும் நேரடியாகச் செய்ய முடியும்." },
];

import { useState } from "react";
import { LuChevronDown, LuChevronUp } from "react-icons/lu";

export default function FaqView({ currentLanguage = "en" }) {
  const [open, setOpen] = useState(null);
  const faqs = currentLanguage === "ta" ? faqsTa : faqsEn;

  return (
    <div className="view-page">
      <div className="view-header">
        <h2 className="view-title">{currentLanguage === "ta" ? "அடிக்கடி கேட்கப்படும் கேள்விகள்" : "Frequently Asked Questions"}</h2>
        <p className="view-sub">{currentLanguage === "ta" ? "குடியிருப்பு சான்றிதழ் விண்ணப்பம் தொடர்பான சந்தேகங்களுக்கு விரைவு பதில்கள்." : "Everything you need to know about the Residence Certificate process."}</p>
      </div>
      <div className="faq-list">
        {faqs.map((item, i) => (
          <div key={i} className={`faq-item${open === i ? " open" : ""}`}>
            <button className="faq-q" onClick={() => setOpen(open === i ? null : i)}>
              <span>{item.q}</span>
              {open === i ? <LuChevronUp size={16} /> : <LuChevronDown size={16} />}
            </button>
            {open === i && <div className="faq-a">{item.a}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
