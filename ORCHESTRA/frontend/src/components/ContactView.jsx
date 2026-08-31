import { LuPhone, LuMail, LuMapPin, LuExternalLink } from "react-icons/lu";

export default function ContactView({ currentLanguage = "en" }) {
  const isTa = currentLanguage === "ta";

  const contacts = [
    { icon: <LuPhone size={18} />, label: isTa ? "கட்டணமில்லா எண்" : "Helpline", value: "1800-425-1477", sub: isTa ? "கட்டணமில்லா · திங்கள்-சனி காலை 8-இரவு 8" : "Toll-free · Mon–Sat 8am–8pm" },
    { icon: <LuMail size={18} />,  label: isTa ? "மின்னஞ்சல்" : "Email",    value: "helpdesk@tnega.tn.gov.in", sub: isTa ? "2 வேலை நாட்களுக்குள் பதில் பெறலாம்" : "Response within 2 working days" },
    { icon: <LuMapPin size={18} />,label: isTa ? "முகவரி" : "Address",  value: "TNeGA, Secretariat, Chennai – 600 009", sub: isTa ? "தமிழ்நாடு மின்னாளுமை முகமை" : "Tamil Nadu e-Governance Agency" },
  ];

  return (
    <div className="view-page">
      <div className="view-header">
        <h2 className="view-title">{isTa ? "தொடர்பு & உதவி மையம்" : "Contact & Support"}</h2>
        <p className="view-sub">{isTa ? "உங்கள் விண்ணப்ப உதவிக்கு TNeGA இ-சேவை ஆதரவு குழுவைத் தொடர்பு கொள்ளவும்." : "Reach out to TNeGA e-Sevai support for help with your application."}</p>
      </div>

      <div className="contact-cards">
        {contacts.map((c, i) => (
          <div key={i} className="contact-card">
            <div className="contact-card-icon">{c.icon}</div>
            <div>
              <div className="contact-card-label">{c.label}</div>
              <div className="contact-card-value">{c.value}</div>
              <div className="contact-card-sub">{c.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <a
        className="btn-primary"
        href="https://www.tnesevai.tn.gov.in/contactus"
        target="_blank"
        rel="noreferrer"
        style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem", marginTop: "1.5rem", textDecoration: "none" }}
      >
        <LuExternalLink size={14} /> {isTa ? "அதிகாரப்பூர்வ தொடர்பு பக்கத்திற்குச் செல்லவும்" : "Visit Official Contact Page"}
      </a>
    </div>
  );
}
