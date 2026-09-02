export function HeroRiskCard() {
  return (
    <article
      className="hero-risk-card"
      aria-label="Illustrative RazorShield network risk card"
    >
      <div className="risk-card-topline">
        <span>RAZORSHIELD</span>
        <span>NETWORK RISK CARD</span>
      </div>
      <div className="risk-card-core">
        <div className="risk-card-shield" aria-hidden="true" />
        <div>
          <span>FINAL RISK SCORE</span>
          <strong>78</strong>
        </div>
      </div>
      <div className="risk-card-action">
        <span>RECOMMENDED ACTION</span>
        <b>REVIEW REQUIRED</b>
      </div>
      <div className="risk-card-signals">
        <span>
          MODEL <b>62</b>
        </span>
        <span>
          NETWORK <b>91</b>
        </span>
        <span>
          RULES <b>74</b>
        </span>
      </div>
      <div className="risk-card-case">
        <span>CASE</span>
        <b>RS-2026-0041</b>
      </div>
      <footer>HUMAN DECISION REQUIRED</footer>
    </article>
  );
}
