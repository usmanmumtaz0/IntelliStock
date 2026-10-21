import { useState } from "react";
import { ArrowUpRight, Copy, Database, Sparkles } from "lucide-react";
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
          <AssistantAnswer answer={turn.answer} />
          <div className="mt-4 flex flex-wrap gap-2" aria-label="Answer sources">
            {turn.sources.map((source) => {
              const href = safeSourceHref(source.href);
              return href ? (
                <a
                  key={`${source.kind}-${source.id}`}
                  href={href}
                  className="group max-w-full break-words rounded-xl border bg-surface/70 px-3.5 py-3 text-xs text-primary transition-colors hover:border-primary/35 hover:bg-primary/[0.04]"
                >
                  <span className="flex items-center gap-2 font-medium">
                    <Database className="size-3.5" />
                    {source.label}
                    <ArrowUpRight className="ml-auto size-3 opacity-50 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                  </span>
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

function AssistantAnswer({ answer }: { answer: string }) {
  return (
    <div className="space-y-2 text-sm leading-7">
      {answer.split("\n").map((line, index) => {
        const key = `${index}-${line.slice(0, 24)}`;
        if (!line.trim()) return <div key={key} className="h-1" aria-hidden="true" />;
        if (line.startsWith("## "))
          return (
            <h3 key={key} className="pt-1 text-lg font-semibold tracking-tight first:pt-0">
              {line.slice(3)}
            </h3>
          );
        if (line.startsWith("### "))
          return (
            <h4
              key={key}
              className="pt-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground"
            >
              {line.slice(4)}
            </h4>
          );
        if (line.startsWith("- "))
          return (
            <div key={key} className="flex gap-2.5 pl-1">
              <span className="mt-[11px] size-1.5 shrink-0 rounded-full bg-primary" />
              <span>{line.slice(2)}</span>
            </div>
          );
        return (
          <p key={key} className="whitespace-pre-wrap break-words">
            {line}
          </p>
        );
      })}
    </div>
  );
}
