import * as React from "react";

const HoverButton = React.forwardRef(({ className, children, onClick, ...props }, ref) => {
  const buttonRef = React.useRef(null);
  const [isListening, setIsListening] = React.useState(false);
  const [circles, setCircles] = React.useState([]);
  const lastAddedRef = React.useRef(0);

  const createCircle = React.useCallback((x, y) => {
    const buttonWidth = buttonRef.current?.offsetWidth || 0;
    const xPos = x / buttonWidth;
    const color = `linear-gradient(to right, #a0d9f8 ${xPos * 100}%, #3a5bbf ${xPos * 100}%)`;
    setCircles((prev) => [...prev, { id: Date.now(), x, y, color, fadeState: null }]);
  }, []);

  const handlePointerMove = React.useCallback((e) => {
    if (!isListening) return;
    const now = Date.now();
    if (now - lastAddedRef.current > 100) {
      lastAddedRef.current = now;
      const rect = e.currentTarget.getBoundingClientRect();
      createCircle(e.clientX - rect.left, e.clientY - rect.top);
    }
  }, [isListening, createCircle]);

  React.useEffect(() => {
    circles.forEach((circle) => {
      if (!circle.fadeState) {
        setTimeout(() => setCircles((p) => p.map((c) => c.id === circle.id ? { ...c, fadeState: "in" } : c)), 0);
        setTimeout(() => setCircles((p) => p.map((c) => c.id === circle.id ? { ...c, fadeState: "out" } : c)), 1000);
        setTimeout(() => setCircles((p) => p.filter((c) => c.id !== circle.id)), 2200);
      }
    });
  }, [circles]);

  return (
    <button
      ref={(node) => { buttonRef.current = node; if (typeof ref === "function") ref(node); else if (ref) ref.current = node; }}
      onClick={onClick}
      onPointerMove={handlePointerMove}
      onPointerEnter={() => setIsListening(true)}
      onPointerLeave={() => setIsListening(false)}
      style={{
        position: "relative",
        isolation: "isolate",
        padding: "0.75rem 2rem",
        borderRadius: "9999px",
        color: "#fff",
        fontWeight: 600,
        fontSize: "1rem",
        lineHeight: 1.5,
        backdropFilter: "blur(12px)",
        background: "rgba(43,55,80,0.25)",
        cursor: "pointer",
        overflow: "hidden",
        border: "none",
        outline: "none",
        boxShadow: "inset 0 0 0 1px rgba(170,202,255,0.25), inset 0 0 16px 0 rgba(170,202,255,0.1), inset 0 -3px 12px 0 rgba(170,202,255,0.15), 0 1px 3px 0 rgba(0,0,0,0.5), 0 4px 12px 0 rgba(0,0,0,0.45)",
        letterSpacing: "0.02em",
      }}
      {...props}
    >
      {circles.map(({ id, x, y, color, fadeState }) => (
        <div
          key={id}
          style={{
            position: "absolute",
            width: "0.75rem",
            height: "0.75rem",
            left: x,
            top: y,
            transform: "translate(-50%, -50%)",
            borderRadius: "9999px",
            filter: "blur(8px)",
            pointerEvents: "none",
            zIndex: -1,
            background: color,
            opacity: fadeState === "in" ? 0.75 : 0,
            transition: fadeState === "out" ? "opacity 1.2s" : "opacity 0.3s",
          }}
        />
      ))}
      {children}
    </button>
  );
});

HoverButton.displayName = "HoverButton";
export { HoverButton };
