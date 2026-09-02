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
          <strong>
            78<small>/100</small>
          </strong>
        </div>
        <b className="risk-card-status">HIGH NETWORK RISK</b>
      </div>
      <div className="risk-card-action">
        <div>
          <span>RECOMMENDED ACTION</span>
          <p>This return requires analyst review before an adverse action.</p>
        </div>
        <b>REVIEW REQUIRED</b>
      </div>
      <div className="risk-card-signals">
        <span>
          MODEL SIGNAL <b>62</b>
        </span>
        <span className="is-primary">
          NETWORK SIGNAL <b>91</b>
        </span>
        <span>
          RULE SIGNAL <b>74</b>
        </span>
      </div>
      <div className="risk-card-case">
        <div>
          <span>CASE REFERENCE</span>
          <b>RS-2026-0041</b>
        </div>
        <div>
          <span>POLICY</span>
          <b>operational-demo-v2</b>
        </div>
      </div>
      <footer>HUMAN DECISION REQUIRED</footer>
    </article>
  );
}
