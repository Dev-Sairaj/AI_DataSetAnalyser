import { useState } from "react";
import { useReport } from "../hooks/useReport";
import BarList from "../components/charts/BarList";
import BoxPlotChart from "../components/charts/BoxPlotChart";
import CorrelationHeatmap from "../components/charts/CorrelationHeatmap";
import HistogramChart from "../components/charts/HistogramChart";
import { Alert, Button, Card, Section, Table, Td, Th } from "../components/ui";
import { fmtInt, fmtNum } from "../lib/format";

const INITIAL = 6;

function ShowMore({ shown, total, onClick }: { shown: number; total: number; onClick: () => void }) {
  if (total <= shown) return null;
  return (
    <Button variant="secondary" onClick={onClick}>
      Show all {total}
    </Button>
  );
}

export default function EdaPage() {
  const { report } = useReport();
  const { eda, charts } = report;
  const [allHist, setAllHist] = useState(false);
  const [allBox, setAllBox] = useState(false);
  const [allCats, setAllCats] = useState(false);

  const hists = allHist ? charts.histograms : charts.histograms.slice(0, INITIAL);
  const boxes = allBox ? charts.boxplots : charts.boxplots.slice(0, INITIAL);
  const cats = Object.entries(charts.category_frequencies);
  const shownCats = allCats ? cats : cats.slice(0, INITIAL);
  const corr = charts.correlation;

  return (
    <div className="space-y-10">
      {eda.numeric.length > 0 && (
        <Section title="Descriptive statistics" subtitle="Numeric columns.">
          <Card className="p-0">
            <Table>
              <thead>
                <tr>
                  <Th>Column</Th>
                  <Th>Mean</Th>
                  <Th>Std</Th>
                  <Th>Min</Th>
                  <Th>Median</Th>
                  <Th>Max</Th>
                  <Th>Skewness</Th>
                  <Th>Shape</Th>
                </tr>
              </thead>
              <tbody>
                {eda.numeric.map((s) => (
                  <tr key={s.column}>
                    <Td className="font-medium">{s.column}</Td>
                    <Td>{fmtNum(s.mean)}</Td>
                    <Td>{fmtNum(s.std)}</Td>
                    <Td>{fmtNum(s.min)}</Td>
                    <Td>{fmtNum(s.median)}</Td>
                    <Td>{fmtNum(s.max)}</Td>
                    <Td>{fmtNum(s.skewness)}</Td>
                    <Td className="text-slate-500">{s.shape}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </Section>
      )}

      {hists.length > 0 && (
        <Section title="Distributions" subtitle="Histograms of numeric columns.">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {hists.map((h) => (
              <HistogramChart key={h.column} hist={h} />
            ))}
          </div>
          <ShowMore shown={hists.length} total={charts.histograms.length} onClick={() => setAllHist(true)} />
        </Section>
      )}

      {boxes.length > 0 && (
        <Section title="Box plots" subtitle="Median, quartiles, whiskers and outliers.">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {boxes.map((b) => (
              <BoxPlotChart key={b.column} box={b} />
            ))}
          </div>
          <ShowMore shown={boxes.length} total={charts.boxplots.length} onClick={() => setAllBox(true)} />
        </Section>
      )}

      {shownCats.length > 0 && (
        <Section title="Category distributions" subtitle="Most frequent values per categorical column.">
          <div className="grid gap-4 md:grid-cols-2">
            {shownCats.map(([column, values]) => {
              const stats = eda.categorical.find((c) => c.column === column);
              return (
                <Card key={column}>
                  <div className="flex items-baseline justify-between">
                    <span className="font-medium">{column}</span>
                    {stats && (
                      <span className="text-xs text-slate-500">{fmtInt(stats.unique)} unique</span>
                    )}
                  </div>
                  <BarList data={values.map((v) => ({ name: v.value, value: v.count }))} />
                </Card>
              );
            })}
          </div>
          <ShowMore shown={shownCats.length} total={cats.length} onClick={() => setAllCats(true)} />
        </Section>
      )}

      {corr && (
        <Section
          title="Correlation analysis"
          subtitle={`Pearson correlation between numeric columns. Highlighted pairs have |r| ≥ ${corr.threshold}.`}
        >
          {corr.sampled && (
            <Alert tone="blue">Computed on a random sample of {fmtInt(corr.n_rows_used)} rows.</Alert>
          )}
          {corr.columns_truncated && (
            <Alert tone="blue">Only the first 40 numeric columns are shown.</Alert>
          )}
          <Card>
            <CorrelationHeatmap data={corr} />
          </Card>
          {corr.high_pairs.length > 0 ? (
            <Card className="p-0">
              <Table>
                <thead>
                  <tr>
                    <Th>Column A</Th>
                    <Th>Column B</Th>
                    <Th>Pearson r</Th>
                  </tr>
                </thead>
                <tbody>
                  {corr.high_pairs.map((p) => (
                    <tr key={`${p.column_a}-${p.column_b}`}>
                      <Td>{p.column_a}</Td>
                      <Td>{p.column_b}</Td>
                      <Td className="font-mono">{p.coefficient}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          ) : (
            <p className="text-sm text-slate-500">No column pairs exceed the threshold.</p>
          )}
        </Section>
      )}

      {eda.numeric.length === 0 && cats.length === 0 && (
        <Alert tone="amber">No numeric or categorical columns were available for analysis.</Alert>
      )}
    </div>
  );
}