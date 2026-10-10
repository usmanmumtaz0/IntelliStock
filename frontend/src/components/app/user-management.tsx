import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { operations, type AccountDto } from "@/lib/api/operations";
import { useAuth } from "@/lib/auth";
import type { UserRole } from "@/lib/api";
import { Panel, Tag } from "./primitives";
import { ActionButton, Field, OperationError } from "./operation-fields";

export function UserManagement() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: operations.accounts,
    enabled: user?.role === "admin",
  });
  const [adding, setAdding] = useState(false);
  const create = useMutation({
    mutationFn: operations.createAccount,
    onSuccess: async () => {
      setAdding(false);
      create.reset();
      toast.success("Account created");
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
  if (user?.role !== "admin") return null;
  return (
    <Panel
      title="User access · administrator only"
      className="xl:col-span-2"
      action={
        <ActionButton
          onClick={() => {
            create.reset();
            setAdding(!adding);
          }}
        >
          Add user
        </ActionButton>
      }
    >
      <p className="mb-4 text-xs text-muted-foreground">
        Single-store access: staff read data; managers configure stock and cameras; administrators
        also manage accounts. Your own administrator role is protected.
      </p>
      <OperationError error={accounts.error} />
      {accounts.isLoading && <p className="text-sm">Loading accounts…</p>}
      <div className="space-y-3">
        {accounts.data?.map((account) => (
          <AccountRow
            key={`${account.id}-${account.role}-${account.is_active}-${account.signup_pending}`}
            account={account}
            self={account.id === user.userId}
          />
        ))}
      </div>
      {adding && (
        <form
          className="mt-4 grid gap-3 rounded-md border p-4 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            create.mutate({
              email: String(data.get("email")),
              username: String(data.get("username")),
              password: String(data.get("password")),
              role: data.get("role") as UserRole,
            });
          }}
        >
          <Field label="Email" name="email" type="email" required autoComplete="off" />
          <Field label="Username" name="username" required maxLength={255} autoComplete="off" />
          <Field
            label="Initial password (12–128 characters)"
            name="password"
            type="password"
            minLength={12}
            maxLength={128}
            required
            autoComplete="new-password"
          />
          <RoleSelect defaultValue="staff" />
          <OperationError error={create.error} />
          <ActionButton type="submit" disabled={create.isPending}>
            Create account
          </ActionButton>
        </form>
      )}
    </Panel>
  );
}

function RoleSelect({
  defaultValue,
  disabled = false,
}: {
  defaultValue: UserRole;
  disabled?: boolean;
}) {
  return (
    <label className="grid gap-1 text-xs text-muted-foreground">
      Role
      <select
        name="role"
        defaultValue={defaultValue}
        disabled={disabled}
        className="h-9 rounded-md border bg-background px-2 text-foreground"
      >
        <option value="staff">Staff</option>
        <option value="manager">Manager</option>
        <option value="admin">Admin</option>
      </select>
    </label>
  );
}

function AccountRow({ account, self }: { account: AccountDto; self: boolean }) {
  const queryClient = useQueryClient();
  const approve = useMutation({
    mutationFn: () => operations.approveSignup(account.id),
    onSuccess: async () => {
      toast.success("Signup approved with Staff access");
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
  const update = useMutation({
    mutationFn: (input: { role: UserRole; is_active: boolean }) =>
      operations.updateAccount(account.id, input),
    onSuccess: async () => {
      toast.success("Access updated");
      await queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });
  return (
    <form
      className="flex flex-wrap items-end gap-3 rounded-md border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        update.mutate({
          role: data.get("role") as UserRole,
          is_active: data.get("active") === "on",
        });
      }}
    >
      <div className="mr-auto">
        <p className="text-sm font-medium">
          {account.username} {self && "(you)"}
        </p>
        <p className="text-xs text-muted-foreground">{account.email}</p>
        <Tag tone={account.is_active ? "healthy" : "neutral"}>
          {account.signup_pending ? "Pending approval" : account.is_active ? "Active" : "Disabled"}
        </Tag>
      </div>
      <RoleSelect
        defaultValue={account.role}
        disabled={self || update.isPending || account.signup_pending}
      />
      <label className="flex h-9 items-center gap-2 text-xs">
        <input
          type="checkbox"
          name="active"
          defaultChecked={account.is_active}
          disabled={self || update.isPending || account.signup_pending}
        />
        Active
      </label>
      {account.signup_pending && (
        <ActionButton
          type="button"
          disabled={approve.isPending}
          onClick={() => {
            if (
              window.confirm(
                `Approve Staff access for ${account.email}? Verify this person's identity first.`,
              )
            )
              approve.mutate();
          }}
        >
          Approve signup
        </ActionButton>
      )}
      <ActionButton type="submit" disabled={self || update.isPending || account.signup_pending}>
        Save access
      </ActionButton>
      <OperationError error={update.error} />
      <OperationError error={approve.error} />
    </form>
  );
}
