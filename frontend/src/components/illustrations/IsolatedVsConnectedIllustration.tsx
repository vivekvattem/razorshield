export function IsolatedVsConnectedIllustration() {
  return (
    <svg
      className="illustration comparison-illustration"
      viewBox="0 0 760 330"
      role="img"
      aria-labelledby="comparison-title comparison-description"
    >
      <title id="comparison-title">
        Individual returns compared with a connected network
      </title>
      <desc id="comparison-description">
        Three harmless-looking returns are viewed independently on the left and
        connected by shared identities on the right.
      </desc>
      <text className="illustration-heading" x="44" y="42">
        Viewed separately
      </text>
      <text className="illustration-heading" x="432" y="42">
        Viewed as a network
      </text>
      <g className="isolated-cards">
        <rect x="44" y="72" width="230" height="50" rx="12" />
        <rect x="44" y="142" width="230" height="50" rx="12" />
        <rect x="44" y="212" width="230" height="50" rx="12" />
        <text x="64" y="102">
          Return A
        </text>
        <text x="207" y="102">
          Low signal
        </text>
        <text x="64" y="172">
          Return B
        </text>
        <text x="207" y="172">
          Low signal
        </text>
        <text x="64" y="242">
          Return C
        </text>
        <text x="207" y="242">
          Low signal
        </text>
      </g>
      <path className="comparison-divider" d="M362 58 V278" />
      <g className="illustration-links comparison-links">
        <path d="M466 100 C542 90 568 133 610 165" />
        <path d="M466 165 L610 165" />
        <path d="M466 230 C542 238 568 197 610 165" />
      </g>
      <g className="connected-cards">
        <rect x="432" y="76" width="88" height="48" rx="14" />
        <rect x="432" y="141" width="88" height="48" rx="14" />
        <rect x="432" y="206" width="88" height="48" rx="14" />
        <text x="476" y="105">
          Return A
        </text>
        <text x="476" y="170">
          Return B
        </text>
        <text x="476" y="235">
          Return C
        </text>
        <rect
          className="comparison-shared"
          x="558"
          y="124"
          width="74"
          height="82"
          rx="18"
        />
        <text x="595" y="153">
          Shared
        </text>
        <text x="595" y="170">
          identities
        </text>
        <circle className="comparison-case" cx="690" cy="165" r="40" />
        <text x="690" y="160">
          Review
        </text>
        <text x="690" y="176">
          case
        </text>
      </g>
      <text className="illustration-caption" x="432" y="292">
        One understandable investigation
      </text>
    </svg>
  );
}
