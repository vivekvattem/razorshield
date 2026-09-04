import { useEffect, useRef, useState } from "react";

type WorkflowIconName = "evidence" | "assist" | "decision" | "audit";

function WorkflowIcon({ name }: { name: WorkflowIconName }) {
  return (
    <svg className="human-workflow-icon" viewBox="0 0 24 24" aria-hidden="true">
      {name === "evidence" && (
        <>
          <path d="M14 3H5v18h14V8zM14 3v5h5" />
          <circle cx="11" cy="14" r="3" />
          <path d="m13.2 16.2 2.3 2.3" />
        </>
      )}
      {name === "assist" && (
        <>
          <path d="m12 3 7 3v5c0 5.5-3.4 8.6-7 10-3.6-1.4-7-4.5-7-10V6z" />
          <path d="m8 12 2.4 2.4L16 9" />
        </>
      )}
      {name === "decision" && (
        <>
          <circle cx="12" cy="8" r="3" />
          <path d="M5 20c.6-3.4 3-5 7-5s6.4 1.6 7 5M16 13l2 2 4-4" />
        </>
      )}
      {name === "audit" && (
        <>
          <path d="M5 3h10l4 4v14H5zM15 3v5h4" />
          <path d="m8 15 2.2 2.2L15 12" />
        </>
      )}
    </svg>
  );
}

const workflowCards = [
  {
    eyebrow: "EVIDENCE",
    title: "3 network signals found",
    icon: "evidence" as const,
    details: [
      "Shared payment identity",
      "Elevated return velocity",
      "Linked to 3 accounts",
    ],
  },
  {
    eyebrow: "RISK ASSIST",
    title: "High network risk",
    icon: "assist" as const,
    details: ["Score: 78 / 100", "Model-supported assessment"],
  },
  {
    eyebrow: "HUMAN DECISION",
    title: "Review Required",
    icon: "decision" as const,
    details: ["Analyst remains final decision owner"],
  },
  {
    eyebrow: "AUDIT TRAIL",
    title: "Decision recorded",
    icon: "audit" as const,
    details: ["Model, policy and analyst action preserved"],
  },
];

export function HumanReviewIllustration() {
  const ref = useRef<HTMLDivElement>(null);
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
      { threshold: 0.25 },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`human-review-workflow${revealed ? " is-revealed" : ""}`}
      role="img"
      aria-label="Evidence flows through risk assistance and human decision into an audit trail"
    >
      <div className="human-workflow-track" aria-hidden="true" />
      {workflowCards.map((card) => (
        <article
          className={`human-workflow-card ${card.icon}`}
          key={card.eyebrow}
        >
          <div className="human-workflow-card-head">
            <span className="human-workflow-icon-wrap">
              <WorkflowIcon name={card.icon} />
            </span>
            <span className="human-workflow-eyebrow">{card.eyebrow}</span>
          </div>
          <h3>{card.title}</h3>
          <ul>
            {card.details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}
