export function HeroNetworkIllustration() {
  return (
    <svg
      className="illustration hero-network-illustration"
      viewBox="0 0 640 440"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Connected refund-risk network showing three customers linked through shared device, payment and address identities"
    >
      <defs>
        <linearGradient id="hero-core-gradient" x1="0" x2="1" y1="0" y2="1">
          <stop stopColor="var(--cyan)" />
          <stop offset="1" stopColor="var(--blue)" />
        </linearGradient>
      </defs>
      <g className="illustration-links hero-links">
        <path d="M120 100 C154 100 171 92 200 92" />
        <path d="M120 220 H200" />
        <path d="M120 340 C154 340 171 348 200 348" />
        <path d="M310 92 C330 92 330 180 326 192" />
        <path d="M310 220 H324" />
        <path d="M310 348 C330 348 330 260 326 248" />
        <path d="M456 205 C472 170 480 142 500 124" />
        <path d="M456 220 H500" />
        <path d="M456 235 C472 270 480 298 500 316" />
      </g>
      <g className="hero-customer">
        <circle cx="86" cy="100" r="34" />
        <circle cx="86" cy="220" r="34" />
        <circle cx="86" cy="340" r="34" />
        <text x="86" y="96">
          <tspan x="86">Customer</tspan>
          <tspan x="86" dy="14">
            A
          </tspan>
        </text>
        <text x="86" y="216">
          <tspan x="86">Customer</tspan>
          <tspan x="86" dy="14">
            B
          </tspan>
        </text>
        <text x="86" y="336">
          <tspan x="86">Customer</tspan>
          <tspan x="86" dy="14">
            C
          </tspan>
        </text>
      </g>
      <g className="hero-identity">
        <rect x="200" y="50" width="110" height="84" rx="18" />
        <rect x="200" y="178" width="110" height="84" rx="18" />
        <rect x="200" y="306" width="110" height="84" rx="18" />
        <text x="255" y="84">
          Device
        </text>
        <text className="illustration-token" x="255" y="107">
          dev_token_91
        </text>
        <text x="255" y="212">
          Payment
        </text>
        <text className="illustration-token" x="255" y="235">
          pay_token_42
        </text>
        <text x="255" y="340">
          Address
        </text>
        <text className="illustration-token" x="255" y="363">
          addr_token_07
        </text>
      </g>
      <g className="hero-core">
        <circle cx="390" cy="220" r="66" />
        <path d="M390 174 l26 10 v28 c0 27-16 42-26 47-10-5-26-20-26-47v-28z" />
        <path className="hero-check" d="M377 215 l9 9 18-22" />
        <text x="390" y="306">
          Risk Assessment
        </text>
      </g>
      <g className="hero-score-card hero-score-card-one">
        <rect x="500" y="70" width="112" height="92" rx="16" />
        <text x="516" y="100">
          Network Signal
        </text>
        <text className="hero-score" x="516" y="138">
          91
        </text>
      </g>
      <g className="hero-score-card hero-score-card-two">
        <rect x="500" y="278" width="112" height="92" rx="16" />
        <text x="516" y="308">
          Recommended Action
        </text>
        <text className="hero-action" x="516" y="338">
          Review Required
        </text>
      </g>
    </svg>
  );
}
