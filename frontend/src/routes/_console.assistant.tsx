import { useEffect, useRef, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus, Send, Trash2, Sparkles, Search, Loader2 } from "lucide-react";
import { chat } from "@/lib/api/chat";
import { useAuth } from "@/lib/auth";
import { PageHeader, Tag } from "@/components/app/primitives";
import { ActionButton, OperationError } from "@/components/app/operation-fields";

import { ChatMessage } from "@/components/app/chat-message";

export const Route = createFileRoute("/_console/assistant")({
  component: Assistant,
  head: () => ({ meta: [{ title: "Assistant — IntelliStock" }] }),
});

function Assistant() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const request = useRef<{ conversation: string; question: string; request_id: string } | null>(
    null,
  );
  const status = useQuery({ queryKey: ["chat-status"], queryFn: chat.status });
  const conversations = useQuery({
    queryKey: ["chat-conversations", user?.userId],
    queryFn: chat.conversations,
  });
  const history = useQuery({
    queryKey: ["chat", user?.userId, selected],
    queryFn: () => chat.get(selected!),
    enabled: Boolean(selected),
  });
  const create = useMutation({
    mutationFn: chat.create,
    onSuccess: async (value) => {
      setSelected(value.id);
      setDraft("");
      request.current = null;
      await queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
    },
  });
  const remove = useMutation({
    mutationFn: chat.remove,
    onSuccess: async () => {
      setSelected(null);
      setDraft("");
      request.current = null;
      queryClient.removeQueries({ queryKey: ["chat"] });
      await queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
    },
  });
  const send = useMutation({
    mutationFn: (input: { conversation: string; question: string; request_id: string }) =>
      chat.ask(input.conversation, inputForApi(input)),
    onSuccess: async () => {
      setDraft("");
      request.current = null;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["chat"] }),
        queryClient.invalidateQueries({ queryKey: ["chat-conversations"] }),
        queryClient.invalidateQueries({ queryKey: ["agents"] }),
      ]);
    },
  });
  const busy = send.isPending || create.isPending || remove.isPending;
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [selected, history.data?.turns.length, send.isPending]);
  const full = (history.data?.turns.length ?? 0) >= (status.data?.max_turns ?? 100);
  return (
    <>
      <PageHeader
        title="Inventory assistant"
        description="Ask about your stock. Read-only answers with database source references."
        actions={
          <Tag tone="primary">
            <MessageSquare className="size-3" />
            Read only
          </Tag>
        }
      />
      <details className="mb-4 rounded-lg border px-4 py-2 text-xs text-muted-foreground">
        <summary className="cursor-pointer">Privacy, saved history & AI configuration</summary>
        <p className="mb-1 font-medium text-foreground">
          {status.data?.provider_ready
            ? `AI routing configured (${status.data.provider}); connection not verified`
            : "Local / fallback mode · external AI not ready"}
        </p>
        <p>{status.data?.data_policy ?? "Loading provider policy…"}</p>
        <p className="mt-1">
          Conversations are private to your account and stored until you delete them. Do not paste
          passwords or API keys. Old answers are snapshots; ask again for current data.
        </p>
        <p className="mt-1">
          Follow-ups use the previous product/query context, not full conversation memory. Up to 50
          conversations per account.
        </p>
      </details>
      <OperationError
        error={
          status.error ||
          conversations.error ||
          history.error ||
          create.error ||
          remove.error ||
          send.error
        }
      />
      <div className="grid overflow-hidden rounded-2xl border bg-background shadow-sm md:grid-cols-[230px_minmax(0,1fr)]">
        <aside
          aria-label="Chat history"
          className="border-b bg-sidebar p-4 md:border-b-0 md:border-r"
        >
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              send.reset();
              create.mutate();
            }}
            className="mb-4 flex w-full items-center gap-2 rounded-xl border bg-background px-3 py-2.5 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            <Plus className="size-4" /> New chat
          </button>
          <label className="relative mb-4 block">
            <span className="sr-only">Search conversations</span>
            <Search className="absolute left-3 top-3 size-3 text-muted-foreground" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search chats"
              className="h-9 w-full rounded-lg border bg-background pl-8 pr-2 text-xs"
            />
          </label>
          <p className="mb-3 text-[10px] uppercase tracking-widest text-muted-foreground">
            Your conversations
          </p>
          <div className="max-h-36 md:max-h-[55vh] space-y-2 overflow-y-auto">
            {conversations.isLoading && <p className="text-xs">Loading…</p>}
            {!conversations.isLoading && !conversations.data?.length && (
              <p className="text-xs text-muted-foreground">Create a conversation to begin.</p>
            )}
            {conversations.data
              ?.filter((item) => item.title.toLowerCase().includes(search.toLowerCase()))
              .map((item) => (
                <button
                  key={item.id}
                  disabled={busy}
                  onClick={() => {
                    setSelected(item.id);
                    setDraft("");
                    request.current = null;
                    send.reset();
                  }}
                  className={`w-full rounded-lg p-3 text-left text-xs ${selected === item.id ? "bg-accent text-foreground" : "hover:bg-accent"}`}
                >
                  <p className="truncate font-medium">{item.title}</p>
                  <p className="mt-1 text-muted-foreground">
                    {item.turn_count} turns · {new Date(item.updated_at).toLocaleDateString()}
                  </p>
                </button>
              ))}
          </div>
          {search &&
            conversations.data &&
            !conversations.data.some((item) =>
              item.title.toLowerCase().includes(search.toLowerCase()),
            ) && <p className="text-xs text-muted-foreground">No matching chats.</p>}
          <p className="mt-4 border-t pt-3 text-[11px] text-muted-foreground">
            History is saved to your account.
          </p>
        </aside>
        <section className="flex min-w-0 flex-col">
          <header className="flex items-center justify-between border-b px-5 py-3">
            <p className="truncate text-sm font-medium">
              {history.data?.title ?? "IntelliStock Assistant"}
            </p>
            {selected && (
              <button
                type="button"
                aria-label="Delete this conversation"
                disabled={busy}
                onClick={() =>
                  window.confirm("Permanently delete this conversation and its messages?") &&
                  remove.mutate(selected)
                }
                className="rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-critical disabled:opacity-50"
              >
                <Trash2 className="size-4" />
              </button>
            )}
          </header>
          <div
            className="h-[45vh] min-h-64 space-y-8 overflow-y-auto px-5 py-6 sm:px-8 md:h-[50vh]"
            aria-live="polite"
            aria-busy={send.isPending}
          >
            {history.isLoading && selected && <p className="text-sm">Loading messages…</p>}
            {(!selected ||
              (!history.isLoading && !history.data?.turns.length && !history.isError)) && (
              <div className="mx-auto max-w-xl py-6">
                <Sparkles className="mb-4 size-8 text-primary" />
                <h2 className="text-2xl font-semibold tracking-tight">
                  What’s happening on your shelves?
                </h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Explore stock, alerts and recent changes with answers grounded in your inventory
                  records.
                </p>
                {!selected && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Choose New chat to begin, or reopen a saved conversation.
                  </p>
                )}
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {[
                    "Inventory summary",
                    "Show low stock",
                    "Show active alerts",
                    "Show history for the last 7 days",
                  ].map((example) => (
                    <button
                      type="button"
                      key={example}
                      disabled={!selected || busy || full || history.isLoading || history.isError}
                      onClick={() => {
                        setDraft(example);
                        composer.current?.focus();
                      }}
                      className="rounded-xl border p-4 text-left text-sm hover:bg-accent disabled:opacity-40"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {history.data?.turns.map((turn) => (
              <div className="mx-auto max-w-3xl" key={turn.id}>
                <ChatMessage turn={turn} />
              </div>
            ))}
            {send.isPending && (
              <div className="mx-auto max-w-3xl space-y-6">
                <p className="ml-auto max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-secondary px-5 py-3 text-sm">
                  {send.variables?.question}
                </p>
                <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 motion-safe:animate-spin" />
                  Reading current records…
                </p>
              </div>
            )}
            <div ref={bottom} />
          </div>
          {full && (
            <p role="status" className="px-5 text-xs text-muted-foreground">
              Conversation limit reached. Start a new chat to continue.
            </p>
          )}
          <form
            className="mx-4 mb-4 mt-auto space-y-2 rounded-2xl border bg-surface p-3 shadow-sm focus-within:border-primary/50"
            onSubmit={(event) => {
              event.preventDefault();
              const question = draft.trim();
              if (!selected || !question || busy || full || history.isLoading || history.isError)
                return;
              if (
                !request.current ||
                request.current.question !== question ||
                request.current.conversation !== selected
              )
                request.current = {
                  conversation: selected,
                  question,
                  request_id: crypto.randomUUID(),
                };
              send.mutate(request.current);
            }}
          >
            <label htmlFor="chat-question" className="sr-only">
              Your question
            </label>
            <textarea
              ref={composer}
              id="chat-question"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              disabled={!selected || busy}
              maxLength={2000}
              required
              rows={2}
              placeholder={
                'Try: Inventory for SKU ABC-123, or History for "Milk" in the last 7 days'
              }
              className="max-h-40 min-h-14 w-full resize-y bg-transparent p-1 text-sm leading-6 outline-none disabled:opacity-50"
            />
            <div className="flex items-center justify-between">
              <p className="text-[11px] text-muted-foreground">
                Enter to send · Shift+Enter for new line · {draft.length}/2000 ·{" "}
                {status.data?.max_turns ?? 100} turns per conversation
              </p>
              <ActionButton
                type="submit"
                disabled={
                  !selected || busy || full || history.isLoading || history.isError || !draft.trim()
                }
              >
                <span className="inline-flex items-center gap-2">
                  <Send className="size-3" />
                  {send.isError ? "Retry question" : "Ask assistant"}
                </span>
              </ActionButton>
            </div>
          </form>
        </section>
      </div>
    </>
  );
}

function inputForApi(input: { question: string; request_id: string }) {
  return { question: input.question, request_id: input.request_id };
}
