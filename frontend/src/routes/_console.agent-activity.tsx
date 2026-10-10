import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, XCircle, Gauge, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { ago, confidencePercent, minutesAgo } from "@/lib/view-models";
import { PageHeader, Panel, Tag, EmptyState, SkeletonRow } from "@/components/app/primitives";

export const Route = createFileRoute("/_console/agent-activity")({
  head: () => ({ meta: [{ title: "Agent Activity — IntelliStock" }] }),
  component: AgentActivity,
});

function AgentActivity() {
  const runs = useQuery({
    queryKey: queryKeys.agents,
    queryFn: () => api.agentRuns(24),
    refetchInterval: 30_000,
  });
  const stats = useQuery({
    queryKey: [...queryKeys.agents, "stats"],
    queryFn: () => api.agentStats(24),
    refetchInterval: 30_000,
  });
  const cards = [
    { label: "Runs · 24h", value: stats.data?.total_runs ?? 0, icon: Activity },
    { label: "Completed", value: stats.data?.completed ?? 0, icon: CheckCircle2 },
    { label: "Failed", value: stats.data?.failed ?? 0, icon: XCircle },
    {
      label: "Success rate",
      value: `${Math.round((stats.data?.success_rate ?? 0) * 100)}%`,
      icon: Gauge,
    },
  ];

  return (
    <>
      <PageHeader
        title="Agent activity"
        description="Execution history for insights, notifications and read-only chat. Private chat content is never shown here."
        actions={<Tag tone="primary">Read-only</Tag>}
      />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-lg border bg-surface p-4">
            <div className="flex items-center justify-between text-[12px] text-muted-foreground">
              <span>{card.label}</span>
              <card.icon className="size-4" />
            </div>
            <p className="mt-3 font-mono text-2xl font-semibold">{card.value}</p>
          </div>
        ))}
      </div>
      <Panel title="Recent executions" className="mt-4" bodyClassName="p-0">
        {runs.isLoading ? (
          <div className="space-y-4 p-4">
            {Array.from({ length: 7 }).map((_, index) => (
              <SkeletonRow key={index} />
            ))}
          </div>
        ) : runs.error ? (
          <p role="alert" className="p-4 text-[12px] text-critical">
            {runs.error.message}
          </p>
        ) : runs.data?.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead className="border-b text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  {[
                    "Agent",
                    "Trigger",
                    "Status",
                    "Action",
                    "Confidence",
                    "Duration",
                    "Created",
                  ].map((label) => (
                    <th key={label} className="px-4 py-2 text-left font-medium">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.data.map((run) => (
                  <tr key={run.id} className="border-b last:border-0">
                    <td className="px-4 py-2 font-medium">{run.agent_type}</td>
                    <td className="px-4 py-2 text-muted-foreground">{run.trigger_event ?? "—"}</td>
                    <td className="px-4 py-2">
                      <Tag
                        tone={
                          run.status === "completed"
                            ? "healthy"
                            : run.status === "failed"
                              ? "critical"
                              : "warning"
                        }
                      >
                        {run.status}
                      </Tag>
                    </td>
                    <td className="max-w-xs truncate px-4 py-2">{run.output_action ?? "—"}</td>
                    <td className="px-4 py-2 font-mono">
                      {run.confidence_score == null
                        ? "—"
                        : `${confidencePercent(run.confidence_score)}%`}
                    </td>
                    <td className="px-4 py-2 font-mono">
                      {run.execution_time_ms == null ? "—" : `${run.execution_time_ms}ms`}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2 text-muted-foreground">
                      {ago(minutesAgo(run.created_at))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-6">
            <EmptyState
              icon={Clock}
              title="No agent runs yet"
              description="Agent execution records will appear after inventory events trigger the rule workflow."
            />
          </div>
        )}
      </Panel>
    </>
  );
}
