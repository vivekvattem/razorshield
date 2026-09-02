import { useEffect, useRef, useState } from "react";

export function HumanReviewIllustration() {
  const ref = useRef<SVGSVGElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const target = ref.current;
    if (!target) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setRevealed(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        setRevealed(true);
        observer.disconnect();
      },
      { threshold: 0.28 },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  return (
    <svg
      ref={ref}
      className={`illustration human-review-illustration${revealed ? " is-revealed" : ""}`}
      viewBox="0 0 700 430"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Evidence flows to a human analyst, a bounded review recommendation, and a recorded audit history"
    >
      <g className="review-connectors" aria-hidden="true">
        <path d="M236 173 C270 173 284 173 314 173" />
        <path d="M405 203 C438 203 456 217 490 217" />
        <path d="M577 238 C577 276 532 301 500 328" />
      </g>
      <g className="review-evidence">
        <rect x="36" y="58" width="200" height="220" rx="20" />
        <text className="review-eyebrow" x="62" y="88">
          EVIDENCE
        </text>
        <g className="evidence-row">
          <circle cx="68" cy="116" r="6" />
          <text x="82" y="120">
            Shared payment identity
          </text>
          <rect x="190" y="110" width="22" height="6" rx="3" />
        </g>
        <g className="evidence-row">
          <circle cx="68" cy="156" r="6" />
          <text x="82" y="160">
            Return velocity increased
          </text>
          <rect x="184" y="150" width="28" height="6" rx="3" />
        </g>
        <g className="evidence-row">
          <circle cx="68" cy="196" r="6" />
          <text x="82" y="200">
            Connected to 3 accounts
          </text>
          <rect x="188" y="190" width="24" height="6" rx="3" />
        </g>
        <rect
          className="evidence-badge"
          x="62"
          y="226"
          width="148"
          height="26"
          rx="9"
        />
        <text className="evidence-badge-text" x="136" y="243">
          MODEL-GENERATED EVIDENCE
        </text>
      </g>
      <g className="review-analyst">
        <circle className="analyst-avatar" cx="360" cy="128" r="34" />
        <path
          className="analyst-head"
          d="M347 130c0-13 7-21 13-21s13 8 13 21-7 19-13 19-13-6-13-19z"
        />
        <path className="analyst-desk" d="M318 210h84M332 210v18M388 210v18" />
        <circle className="analyst-lens" cx="388" cy="162" r="11" />
        <path className="analyst-lens" d="m396 170 12 12" />
        <text className="analyst-title" x="360" y="254">
          Human analyst
        </text>
        <text className="analyst-support" x="360" y="274">
          Final decision owner
        </text>
      </g>
      <g className="review-actions">
        <text className="review-eyebrow" x="577" y="68">
          BOUNDED RECOMMENDATION
        </text>
        <rect x="490" y="84" width="174" height="38" rx="13" />
        <rect x="490" y="136" width="174" height="38" rx="13" />
        <rect
          className="selected-action"
          x="490"
          y="188"
          width="174"
          height="46"
          rx="14"
        />
        <text x="577" y="108">
          Safe to Approve
        </text>
        <text x="577" y="160">
          Verification Needed
        </text>
        <circle className="selected-indicator" cx="510" cy="211" r="5" />
        <text className="selected-action-text" x="587" y="216">
          Review Required
        </text>
      </g>
      <g className="review-audit">
        <rect x="170" y="330" width="410" height="56" rx="16" />
        <circle cx="202" cy="358" r="13" />
        <path d="m196 358 5 5 9-10" />
        <text className="audit-title" x="226" y="354">
          Decision recorded
        </text>
        <text className="audit-support" x="226" y="373">
          Model, policy and analyst action preserved
        </text>
      </g>
    </svg>
  );
}
