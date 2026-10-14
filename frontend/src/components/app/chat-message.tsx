import { useState } from "react";
import { Copy, Sparkles } from "lucide-react";
import { safeSourceHref, type ChatTurn } from "@/lib/api/chat";

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  const [copyStatus, setCopyStatus] = useState("");
  return (
    <article className="space-y-6">
      <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-secondary px-5 py-3">
        <span className="sr-only">You: </span>
        <p className="whitespace-pre-wrap break-words text-sm leading-7">{turn.question}</p>
      </div>
      <div className="flex gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-xl border bg-primary/10 text-primary">
          <Sparkles className="size-4" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="mb-2 text-sm font-semibold">IntelliStock</p>
          <p className="whitespace-pre-wrap break-words text-sm leading-7">{turn.answer}</p>
          <div className="mt-4 flex flex-wrap gap-2" aria-label="Answer sources">
            {turn.sources.map((source) => {
              const href = safeSourceHref(source.href);
              return href ? (
                <a
                  key={`${source.kind}-${source.id}`}
                  href={href}
                  className="max-w-full break-words rounded-lg border px-3 py-2 text-xs text-primary hover:bg-accent"
                >
                  <span className="block font-medium">{source.label}</span>
                  <span className="block text-muted-foreground">
                    Source: {source.kind === "aggregate" ? "inventory summary" : source.kind}
                    {source.sku ? ` · Product code: ${source.sku}` : ""}
                    {source.shelf ? ` · Shelf: ${source.shelf}` : ""}
                  </span>
                  {source.updated_at && (
                    <span className="block text-muted-foreground">
                      Record updated (UTC): {source.updated_at}
                    </span>
                  )}
                  {source.retrieved_at && (
                    <span className="block text-muted-foreground">
                      Retrieved (UTC): {source.retrieved_at}
                    </span>
                  )}
                </a>
              ) : null;
            })}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
            <button
              type="button"
              aria-label="Copy answer"
              title="Copy answer"
              className="rounded p-1.5 hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(turn.answer);
                  setCopyStatus("Copied");
                } catch {
                  setCopyStatus("Copy unavailable. Select the answer to copy it.");
                }
              }}
            >
              <Copy className="size-3.5" />
            </button>
            <span role="status">{copyStatus}</span>
            <span>
              {turn.mode === "fallback"
                ? "Local fallback · AI unavailable"
                : turn.mode === "local"
                  ? "Local mode"
                  : `${turn.mode === "openrouter" ? "OpenRouter" : "OpenAI"} · database facts`}
            </span>
            <time dateTime={turn.created_at}>{new Date(turn.created_at).toLocaleString()}</time>
          </div>
          {turn.notice && (
            <details className="mt-1 text-xs text-muted-foreground">
              <summary className="cursor-pointer">About this answer</summary>
              <p className="mt-2 leading-relaxed">{turn.notice}</p>
            </details>
          )}
        </div>
      </div>
    </article>
  );
}
