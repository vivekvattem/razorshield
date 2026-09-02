export function HeroRiskCard() {
  return (
    <article
      className="hero-risk-card"
      aria-label="Illustrative RazorShield network risk card"
    >
      <div className="risk-card-topline">
        <span>RazorShield</span>
        <span>Network Risk Card</span>
      </div>
      <div className="risk-card-core">
        <div className="risk-card-shield" aria-hidden="true" />
        <div>
          <span>Final Risk Score</span>
          <strong>78</strong>
        </div>
      </div>
      <div className="risk-card-action">
        <span>Recommended action</span>
        <b>Review Required</b>
      </div>
      <div className="risk-card-signals">
        <span>
          Model <b>62</b>
        </span>
        <span>
          Network <b>91</b>
        </span>
        <span>
          Rules <b>74</b>
        </span>
      </div>
      <div className="risk-card-case">
        <span>Case</span>
        <b>RS-2026-0041</b>
      </div>
      <footer>Human decision required</footer>
    </article>
  );
}
