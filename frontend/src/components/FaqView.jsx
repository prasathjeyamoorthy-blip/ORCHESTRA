const faqs = [
  { q: "What is a Residence Certificate?", a: "A Residence Certificate is an official document issued by the Tamil Nadu government through TNeGA e-Sevai portals, certifying that a person resides at a particular address in Tamil Nadu." },
  { q: "Who can apply for a Residence Certificate?", a: "Any resident of Tamil Nadu who has been living at their current address can apply. You must have valid address proof documents such as Aadhaar card, Ration card, or Driving License." },
  { q: "What documents are required?", a: "You need: (1) Aadhaar Card, (2) Ration Card, (3) Applicant Photograph, and (4) Driving License as address proof. All documents should be clear and legible." },
  { q: "How long does the process take?", a: "The automated application process typically takes 5–10 minutes once all documents are uploaded. Certificate issuance by the authority may take 3–7 working days." },
  { q: "What is a CAN Number?", a: "CAN (Citizen Account Number) is a unique identifier assigned to citizens on the TNeGA e-Sevai portal. It is optional but helps in faster processing." },
  { q: "What format should my documents be in?", a: "Documents can be uploaded as PDF, JPG, or PNG files. Maximum file size is 5 MB per document. Ensure the document is clearly visible and not blurred." },
  { q: "Is my data secure?", a: "Yes. All data is processed locally and submitted directly to the official TNeGA e-Sevai portal. No personal data is stored on our servers beyond the session." },
  { q: "What if the automation fails?", a: "If automation encounters an error, you will be notified in the chat. You can retry or visit the TNeGA e-Sevai portal directly at www.tnesevai.tn.gov.in." },
];

import { useState } from "react";
import { LuChevronDown, LuChevronUp } from "react-icons/lu";

export default function FaqView() {
  const [open, setOpen] = useState(null);
  return (
    <div className="view-page">
      <div className="view-header">
        <h2 className="view-title">Frequently Asked Questions</h2>
        <p className="view-sub">Everything you need to know about the Residence Certificate process.</p>
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
