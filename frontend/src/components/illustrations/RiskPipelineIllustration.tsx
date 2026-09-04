const stages = [
  ["Connect", "Tokenized activity"],
  ["Analyse", "Point-in-time signals"],
  ["Route safely", "Three bounded actions"],
  ["Audit", "Versioned evidence"],
];

export function RiskPipelineIllustration() {
  return (
    <svg
      className="illustration pipeline-illustration"
      viewBox="0 0 900 230"
      role="img"
      aria-labelledby="pipeline-title pipeline-description"
    >
      <title id="pipeline-title">RazorShield risk pipeline</title>
      <desc id="pipeline-description">
        Four stages connect activity, analyse risk, route safely and preserve an
        audit trail.
      </desc>
      {stages.map(([title, caption], index) => {
        const x = 40 + index * 220;
        return (
          <g key={title} className="pipeline-stage">
            {index < stages.length - 1 && (
              <path
                className="pipeline-link"
                d={`M${x + 144} 104 H${x + 205}`}
              />
            )}
            <rect x={x} y="54" width="144" height="100" rx="20" />
            <circle cx={x + 34} cy="84" r="14" />
            <path d={`M${x + 28} 84 h12 M${x + 34} 78 v12`} />
            <text x={x + 72} y="90">
              {title}
            </text>
            <text className="pipeline-caption" x={x + 72} y="119">
              {caption}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
