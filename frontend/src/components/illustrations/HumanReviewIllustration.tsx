export function HumanReviewIllustration() {
  return (
    <svg
      className="illustration human-review-illustration"
      viewBox="0 0 700 360"
      role="img"
      aria-labelledby="human-review-title human-review-description"
    >
      <title id="human-review-title">Human-controlled review workflow</title>
      <desc id="human-review-description">
        An evidence panel assists an analyst who chooses a bounded action and
        records an audit confirmation.
      </desc>
      <g className="review-evidence">
        <rect x="44" y="56" width="222" height="226" rx="20" />
        <text x="70" y="90">
          Evidence panel
        </text>
        <rect x="70" y="112" width="170" height="14" rx="7" />
        <rect x="70" y="146" width="132" height="14" rx="7" />
        <rect x="70" y="180" width="156" height="14" rx="7" />
        <rect x="70" y="218" width="108" height="28" rx="10" />
        <text x="84" y="237">
          Model assists
        </text>
      </g>
      <path
        className="illustration-links"
        d="M270 170 C328 170 344 170 388 170"
      />
      <g className="review-analyst">
        <circle cx="444" cy="118" r="35" />
        <path d="M388 245 c8-71 104-71 112 0" />
        <text x="444" y="286">
          Human analyst
        </text>
      </g>
      <g className="review-actions">
        <rect x="530" y="76" width="126" height="42" rx="13" />
        <rect x="530" y="136" width="126" height="42" rx="13" />
        <rect x="530" y="196" width="126" height="42" rx="13" />
        <text x="593" y="101">
          Safe to approve
        </text>
        <text x="593" y="161">
          Verification needed
        </text>
        <text x="593" y="221">
          Review required
        </text>
      </g>
      <g className="review-audit">
        <rect x="364" y="302" width="190" height="34" rx="12" />
        <path d="M384 319 l7 7 13-14" />
        <text x="408" y="324">
          Audit confirmation recorded
        </text>
      </g>
    </svg>
  );
}
