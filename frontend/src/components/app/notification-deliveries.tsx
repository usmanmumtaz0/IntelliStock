import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { reporting } from "@/lib/api/reporting";
import { useAuth } from "@/lib/auth";
import { Panel, Tag } from "./primitives";
import { ActionButton, OperationError } from "./operation-fields";

export function NotificationDeliveries() {
  const { user } = useAuth();
  const [offset, setOffset] = useState(0);
  const enabled = user?.role === "admin";
  const config = useQuery({
    queryKey: ["notification-config"],
    queryFn: reporting.configuration,
    enabled,
  });
  const deliveries = useQuery({
    queryKey: ["notification-deliveries", offset],
    queryFn: () => reporting.deliveries(offset),
    enabled,
    refetchInterval: 30_000,
  });
  if (!enabled) return null;
  return (
    <Panel title="Email notifications & delivery history" className="xl:col-span-2">
      <OperationError error={config.error || deliveries.error} />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Tag tone={config.data?.ready ? "healthy" : "neutral"}>
          {config.isLoading
            ? "Checking configuration"
            : config.data?.ready
              ? "Configured & enabled"
              : "Delivery disabled / not ready"}
        </Tag>
        <span className="text-xs text-muted-foreground">
          SMTP only · bounded retries · admin access
        </span>
      </div>
      <p className="mb-3 text-xs text-muted-foreground">
        Configure credentials and an approved recipient in the server .env, then start the
        notification worker. No messages are sent from this page. “Accepted” means the SMTP server
        accepted the message, not inbox delivery.
      </p>
      {!!config.data?.missing.length && (
        <p className="mb-3 text-xs text-warning">
          Missing or invalid: {config.data.missing.join(", ")}
        </p>
      )}
      {deliveries.isLoading ? (
        <p className="text-sm">Loading delivery history…</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b">
                <th className="p-2">Alert / recipient</th>
                <th>State</th>
                <th>Attempts</th>
                <th>Last result</th>
              </tr>
            </thead>
            <tbody>
              {deliveries.data?.data.map((row) => (
                <tr key={row.id} className="border-b">
                  <td className="p-2">
                    <p className="font-mono">
                      {row.alert_id.slice(0, 8)} · {row.alert_stage}
                    </p>
                    <p className="text-muted-foreground">{row.recipient}</p>
                  </td>
                  <td>{row.status}</td>
                  <td>
                    {row.attempts} / {config.data?.max_attempts ?? "—"}
                  </td>
                  <td>
                    {row.last_error ??
                      (row.accepted_at ? new Date(row.accepted_at).toLocaleString() : "Pending")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!deliveries.isLoading && !deliveries.error && !deliveries.data?.total && (
        <p className="py-4 text-xs text-muted-foreground">
          No delivery records. Disabled notifications do not queue messages.
        </p>
      )}
      <div className="mt-3 flex items-center gap-2">
        <ActionButton disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 25))}>
          Previous
        </ActionButton>
        <ActionButton
          disabled={!deliveries.data || offset + 25 >= deliveries.data.total}
          onClick={() => setOffset(offset + 25)}
        >
          Next
        </ActionButton>
        <span className="text-xs text-muted-foreground">
          {deliveries.data?.total ?? 0} total records
        </span>
      </div>
    </Panel>
  );
}
