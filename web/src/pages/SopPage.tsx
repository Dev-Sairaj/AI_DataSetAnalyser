import { useReport } from "../hooks/useReport";
import { Badge, Card, Section } from "../components/ui";
import type { SOPAutomation } from "../types/api";
import type { Tone } from "../components/ui";

const AUTOMATION_LABEL: Record<SOPAutomation, string> = {
  automatic: "Automatic",
  user_triggered: "User-triggered",
  automatic_and_user_triggered: "Automatic and user-triggered",
};

const AUTOMATION_TONE: Record<SOPAutomation, Tone> = {
  automatic: "green",
  user_triggered: "blue",
  automatic_and_user_triggered: "indigo",
};

/** Displays the versioned Standard Operating Procedure embedded in the analysis report. */
export default function SopPage() {
  const { report } = useReport();
  const { sop } = report;

  return (
    <div className="space-y-8">
      <Section title={sop.title} subtitle={`Version ${sop.version} — ${sop.scope}`}>
        <div className="space-y-4">
          {sop.stages.map((stage) => (
            <Card key={stage.step} className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-700">
                  {stage.step}
                </div>
                <h3 className="text-lg font-semibold">{stage.name}</h3>
                <Badge tone={AUTOMATION_TONE[stage.automation]}>
                  {AUTOMATION_LABEL[stage.automation]}
                </Badge>
              </div>

              <dl className="grid gap-3 text-sm md:grid-cols-[10rem_1fr]">
                <dt className="font-medium text-slate-500">Purpose</dt>
                <dd>{stage.purpose}</dd>
                <dt className="font-medium text-slate-500">Input</dt>
                <dd>{stage.input}</dd>
                <dt className="font-medium text-slate-500">Method</dt>
                <dd>{stage.method}</dd>
                <dt className="font-medium text-slate-500">Output</dt>
                <dd>{stage.output}</dd>
                <dt className="font-medium text-slate-500">Testing criteria</dt>
                <dd>
                  <ul className="list-disc space-y-1 pl-5">
                    {stage.testing_criteria.map((criterion) => (
                      <li key={criterion}>{criterion}</li>
                    ))}
                  </ul>
                </dd>
              </dl>
            </Card>
          ))}
        </div>
      </Section>
    </div>
  );
}
