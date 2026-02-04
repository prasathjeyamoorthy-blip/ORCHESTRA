export default function ChatBubble({ sender, message }) {
  const formatMessage = (text) => {
    // Split lines
    const lines = text.split(/\n|•|\d+\./).map(l => l.trim()).filter(Boolean);

    // If looks like a list, render bullets
    if (lines.length > 3) {
      return (
        <ul className="chat-list">
          {lines.map((line, idx) => (
            <li key={idx}>{line}</li>
          ))}
        </ul>
      );
    }

    // Otherwise normal text
    return <p>{text}</p>;
  };

  return (
    <div className={`chat-bubble ${sender}`}>
      {formatMessage(message)}
    </div>
  );
}
