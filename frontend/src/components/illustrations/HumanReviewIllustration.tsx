export function HumanReviewIllustration() {
  return (
    <svg
      className="illustration human-review-illustration"
      viewBox="0 0 700 430"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Human analyst reviewing evidence and recording a bounded decision in the audit history"
    >
      <g className="review-evidence">
        <rect x="38" y="58" width="220" height="218" rx="20" />
        <text x="66" y="91">
          Evidence panel
        </text>
        <rect x="66" y="114" width="166" height="14" rx="7" />
        <rect x="66" y="150" width="132" height="14" rx="7" />
        <rect x="66" y="186" width="152" height="14" rx="7" />
        <rect x="66" y="222" width="112" height="30" rx="10" />
        <text x="82" y="242">
          Model assists
        </text>
      </g>
      <path
        className="illustration-links review-link"
        d="M258 174 C304 174 320 174 362 174"
      />
      <g className="review-analyst">
        <circle cx="422" cy="132" r="34" />
        <path d="M362 267 c8-74 112-74 120 0" />
        <text x="422" y="302">
          Human analyst
        </text>
      </g>
      <g className="review-actions">
        <rect x="520" y="82" width="142" height="44" rx="14" />
        <rect x="520" y="148" width="142" height="44" rx="14" />
        <rect x="520" y="214" width="142" height="44" rx="14" />
        <text x="591" y="109">
          Safe to Approve
        </text>
        <text x="591" y="175">
          Verification Needed
        </text>
        <text x="591" y="241">
          Review Required
        </text>
      </g>
      <g className="review-audit">
        <rect x="248" y="348" width="304" height="46" rx="16" />
        <path d="M274 370 l8 8 15-16" />
        <text x="420" y="376">
          Decision recorded in audit history
        </text>
      </g>
    </svg>
  );
}
