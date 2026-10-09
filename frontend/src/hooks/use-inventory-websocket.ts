import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { queryKeys } from "@/lib/query-keys";

export type ConnectionState = "connecting" | "live" | "offline";

const WS_URL = (import.meta.env["VITE_WS_URL"] ?? "ws://127.0.0.1:8000/ws/inventory").replace(
  /\/$/,
  "",
);

export function useInventoryWebSocket(): ConnectionState {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [state, setState] = useState<ConnectionState>("offline");

  useEffect(() => {
    if (!token) return;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let stopped = false;
    let attempts = 0;

    const invalidateLiveData = () => {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard }),
        queryClient.invalidateQueries({ queryKey: queryKeys.zones }),
        queryClient.invalidateQueries({ queryKey: queryKeys.inventory }),
        queryClient.invalidateQueries({ queryKey: queryKeys.history }),
        queryClient.invalidateQueries({ queryKey: queryKeys.events }),
        queryClient.invalidateQueries({ queryKey: queryKeys.alerts }),
        queryClient.invalidateQueries({ queryKey: queryKeys.alertStats }),
        queryClient.invalidateQueries({ queryKey: queryKeys.cameras }),
      ]);
    };

    const connect = () => {
      if (stopped) return;
      setState("connecting");
      socket = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
      socket.onopen = () => {
        attempts = 0;
        setState("live");
      };
      socket.onmessage = (event) => {
        if (event.data === "pong") return;
        try {
          JSON.parse(String(event.data));
          invalidateLiveData();
        } catch {
          // Ignore non-JSON control messages.
        }
      };
      socket.onclose = () => {
        setState("offline");
        if (!stopped) {
          const delay = Math.min(30_000, 1_000 * 2 ** attempts++);
          retryTimer = window.setTimeout(connect, delay);
        }
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      stopped = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, [token, queryClient]);

  return state;
}
