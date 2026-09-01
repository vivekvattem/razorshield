export function HeroNetworkIllustration() {
  return (
    <svg
      className="illustration hero-network-illustration"
      viewBox="0 0 620 430"
      role="img"
      aria-labelledby="hero-network-title hero-network-description"
    >
      <title id="hero-network-title">Connected refund-risk network</title>
      <desc id="hero-network-description">
        Customer profiles connect through tokenized device, payment and address
        identities to a central RazorShield risk assessment.
      </desc>
      <defs>
        <linearGradient id="hero-core-gradient" x1="0" x2="1" y1="0" y2="1">
          <stop stopColor="var(--rs-cyan)" />
          <stop offset="1" stopColor="var(--rs-blue)" />
        </linearGradient>
      </defs>
      <g className="illustration-links hero-links">
        <path d="M130 94 C224 94 245 155 306 194" />
        <path d="M130 212 C213 212 238 201 306 205" />
        <path d="M130 326 C223 326 247 260 306 220" />
        <path d="M236 104 C274 125 286 154 306 194" />
        <path d="M236 212 L306 212" />
        <path d="M236 320 C275 292 292 255 306 225" />
        <path d="M372 208 C420 160 442 138 491 124" />
        <path d="M372 216 C430 216 457 215 491 215" />
        <path d="M372 225 C418 267 449 290 491 309" />
      </g>
      <g className="hero-customer">
        <circle cx="94" cy="94" r="36" />
        <circle cx="94" cy="212" r="36" />
        <circle cx="94" cy="326" r="36" />
        <text x="94" y="100">
          A
        </text>
        <text x="94" y="218">
          B
        </text>
        <text x="94" y="332">
          C
        </text>
        <text className="illustration-label" x="94" y="147">
          Customer A
        </text>
        <text className="illustration-label" x="94" y="265">
          Customer B
        </text>
        <text className="illustration-label" x="94" y="379">
          Customer C
        </text>
      </g>
      <g className="hero-identity">
        <rect x="196" y="72" width="80" height="64" rx="18" />
        <rect x="196" y="180" width="80" height="64" rx="18" />
        <rect x="196" y="288" width="80" height="64" rx="18" />
        <text x="236" y="99">
          Device
        </text>
        <text x="236" y="207">
          Payment
        </text>
        <text x="236" y="315">
          Address
        </text>
        <text className="illustration-token" x="236" y="118">
          dev_token_91
        </text>
        <text className="illustration-token" x="236" y="226">
          pay_token_42
        </text>
        <text className="illustration-token" x="236" y="334">
          addr_token_07
        </text>
      </g>
      <g className="hero-core">
        <circle cx="338" cy="212" r="62" />
        <path d="M338 172 l25 10 v27 c0 26-16 40-25 45-9-5-25-19-25-45v-27z" />
        <path className="hero-check" d="M326 212 l8 8 17-20" />
        <text x="338" y="291">
          Risk assessment
        </text>
      </g>
      <g className="hero-score-card hero-score-card-one">
        <rect x="458" y="74" width="126" height="88" rx="16" />
        <text x="476" y="103">
          Network signal
        </text>
        <text className="hero-score" x="476" y="138">
          82
        </text>
      </g>
      <g className="hero-score-card hero-score-card-two">
        <rect x="458" y="258" width="126" height="88" rx="16" />
        <text x="476" y="287">
          Recommended action
        </text>
        <text className="hero-action" x="476" y="319">
          Review required
        </text>
      </g>
    </svg>
  );
}
