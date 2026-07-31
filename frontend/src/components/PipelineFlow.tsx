import { Fragment } from "react";

const STAGES = [
  { title: "Ingest", description: "CSV upload, a generated batch, or a file path." },
  {
    title: "Validate",
    description: "Checks format, ranges, and known references. Bad rows are isolated, not the whole batch.",
  },
  { title: "Diagnose", description: "LLM or heuristic proposes one fix, or declines if none is safe." },
  { title: "Repair", description: "Applies the fix and re-validates, retrying up to a cap." },
];

export default function PipelineFlow() {
  return (
    <div className="pipeline-flow">
      {STAGES.map((stage) => (
        <Fragment key={stage.title}>
          <div className="pipeline-stage">
            <h4>{stage.title}</h4>
            <p className="muted">{stage.description}</p>
          </div>
          <div className="pipeline-arrow" aria-hidden="true">
            &rarr;
          </div>
        </Fragment>
      ))}
      <div className="pipeline-outcomes">
        <div className="pipeline-stage pipeline-outcome-healed">
          <h4>Healed</h4>
          <p className="muted">Rejoins the clean data.</p>
        </div>
        <div className="pipeline-stage pipeline-outcome-quarantined">
          <h4>Quarantined</h4>
          <p className="muted">Held for human review, with the full diagnosis history attached.</p>
        </div>
      </div>
    </div>
  );
}
