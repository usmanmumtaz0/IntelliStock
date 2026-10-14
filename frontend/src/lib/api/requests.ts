import { apiRequest, queryString } from "./client";

export type RequestKind = "physical_count" | "discrepancy" | "restock";
export interface Submission {
  inventory_id: string;
  kind: RequestKind;
  reason: string;
  quantity?: number;
}
export interface OperationalRequest extends Omit<Submission, "quantity"> {
  id: string;
  quantity: number | null;
  submitter_id: string;
  status: "pending" | "approved" | "rejected";
  reviewer_id: string | null;
  review_reason: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}
export interface RequestActivity {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  timestamp: string;
  outcome: string;
}
export const requests = {
  list: (offset = 0) =>
    apiRequest<OperationalRequest[]>(`/requests${queryString({ limit: 50, offset })}`),
  submit: (input: Submission) =>
    apiRequest<OperationalRequest>("/requests", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  review: (id: string, input: { decision: "approved" | "rejected"; reason: string }) =>
    apiRequest<OperationalRequest>(`/requests/${encodeURIComponent(id)}/review`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
  activity: (offset = 0) =>
    apiRequest<RequestActivity[]>(`/operational-audit${queryString({ limit: 50, offset })}`),
};

export const requestLabels: Record<RequestKind, string> = {
  physical_count: "Physical count",
  discrepancy: "Inventory discrepancy",
  restock: "Restock request",
};

export function submissionFromForm(data: FormData, kind: RequestKind): Submission {
  return {
    inventory_id: String(data.get("inventory")),
    kind,
    reason: String(data.get("reason")).trim(),
    ...(kind === "physical_count" ? { quantity: Number(data.get("quantity")) } : {}),
  };
}
