import { LuPhone, LuMail, LuMapPin, LuExternalLink } from "react-icons/lu";

const contacts = [
  { icon: <LuPhone size={18} />, label: "Helpline", value: "1800-425-1477", sub: "Toll-free · Mon–Sat 8am–8pm" },
  { icon: <LuMail size={18} />,  label: "Email",    value: "helpdesk@tnega.tn.gov.in", sub: "Response within 2 working days" },
  { icon: <LuMapPin size={18} />,label: "Address",  value: "TNeGA, Secretariat, Chennai – 600 009", sub: "Tamil Nadu e-Governance Agency" },
];

export default function ContactView() {
  return (
    <div className="view-page">
      <div className="view-header">
        <h2 className="view-title">Contact &amp; Support</h2>
        <p className="view-sub">Reach out to TNeGA e-Sevai support for help with your application.</p>
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
        <LuExternalLink size={14} /> Visit Official Contact Page
      </a>
    </div>
  );
}
