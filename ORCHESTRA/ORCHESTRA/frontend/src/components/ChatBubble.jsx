export default function ChatBubble({ sender, message }) {
  const parseSections = (text) => {
    const lines = text.split("\n").map(l => l.trim()).filter(Boolean);

    const sections = [];
    let currentSection = null;

    lines.forEach((line) => {
      // Detect section heading
      if (line.endsWith(":")) {
        currentSection = {
          title: line.replace(":", ""),
          items: []
        };
        sections.push(currentSection);
      }
      // Detect bullet
      else if (
        line.startsWith("-") ||
        line.startsWith("•") ||
        /^\d+\./.test(line)
      ) {
        if (currentSection) {
          currentSection.items.push(
            line.replace(/^[-•]|\d+\./, "").trim()
          );
        }
      }
      // Intro / normal text
      else {
        sections.push({
          text: line
        });
      }
    });

    return sections;
  };

  const renderMessage = () => {
    const sections = parseSections(message);

    return sections.map((section, idx) => {
      // Intro text
      if (section.text) {
        return (
          <p key={idx} className="chat-intro">
            {section.text}
          </p>
        );
      }

      // Section with list
      return (
        <div key={idx} className="chat-section">
          <h4 className="chat-section-title">{section.title}</h4>
          <ul className="chat-list">
            {section.items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      );
    });
  };

  return (
    <div className={`chat-bubble ${sender}`}>
      {renderMessage()}
    </div>
  );
}
