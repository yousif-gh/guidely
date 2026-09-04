// Renders the answer text, turning [1] [2] citations into clickable chips
// that scroll to the matching source card.
export default function AnswerCard({ answer, onCiteClick }) {
  const parts = answer.split(/(\[\d+\])/g);
  return (
    <div className="answer-card">
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (!match) return <span key={i}>{part}</span>;
        const n = Number(match[1]);
        return (
          <button
            key={i}
            className="cite-chip"
            onClick={() => onCiteClick(n)}
            aria-label={`Jump to source ${n}`}
          >
            {n}
          </button>
        );
      })}
    </div>
  );
}
