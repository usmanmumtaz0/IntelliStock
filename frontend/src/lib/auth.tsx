import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useRef,
  type ReactNode,
} from "react";
import { useNavigate, useLocation } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { api, clearAccessToken, getAccessToken, setAccessToken, type AuthUser } from "./api";
import { authorizationKey, can as hasPermission, canVisit } from "./permissions";

interface AuthContextValue {
  ready: boolean;
  user: AuthUser | null;
  token: string | null;
  can: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const generation = useRef(0);
  const userRef = useRef<AuthUser | null>(null);
  const acceptUser = useCallback(
    (next: AuthUser) => {
      if (authorizationKey(userRef.current) !== authorizationKey(next)) {
        void queryClient.cancelQueries();
        queryClient.clear();
      }
      userRef.current = next;
      setUser(next);
    },
    [queryClient],
  );

  const clearSession = useCallback(() => {
    generation.current += 1;
    userRef.current = null;
    clearAccessToken();
    setToken(null);
    setUser(null);
    void queryClient.cancelQueries();
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    if (!token) return;
    let disposed = false;
    let verifying = false;
    const epoch = generation.current;
    const timer = window.setInterval(() => {
      if (verifying) return;
      verifying = true;
      void api
        .verify()
        .then(
          (verified) =>
            !disposed &&
            epoch === generation.current &&
            acceptUser({
              userId: verified.user_id,
              username: verified.username,
              email: verified.email,
              role: verified.role,
              permissions: verified.permissions ?? [],
            }),
        )
        .catch(() => {
          // The central 401 handler clears revoked sessions; transient failures do not.
        })
        .finally(() => {
          verifying = false;
        });
    }, 30_000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [token, acceptUser]);

  useEffect(() => {
    const existingToken = getAccessToken();
    if (!existingToken) {
      setReady(true);
      return;
    }
    setToken(existingToken);
    let disposed = false;
    const epoch = generation.current;
    api
      .verify()
      .then((verified) => {
        if (disposed || epoch !== generation.current) return;
        acceptUser({
          userId: verified.user_id,
          username: verified.username,
          email: verified.email,
          role: verified.role,
          permissions: verified.permissions ?? [],
        });
      })
      .catch(() => {
        if (!disposed && epoch === generation.current) clearSession();
      })
      .finally(() => {
        if (!disposed) setReady(true);
      });
    return () => {
      disposed = true;
    };
  }, [clearSession, acceptUser]);

  useEffect(() => {
    const onUnauthorized = () => clearSession();
    window.addEventListener("intellistock:unauthorized", onUnauthorized);
    return () => window.removeEventListener("intellistock:unauthorized", onUnauthorized);
  }, [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const epoch = ++generation.current;
      const response = await api.login(email, password);
      if (epoch !== generation.current) return;
      setAccessToken(response.access_token);
      setToken(response.access_token);
      acceptUser({
        userId: response.user_id,
        username: response.username,
        email: response.email,
        role: response.role,
        permissions: response.permissions ?? [],
      });
    },
    [acceptUser],
  );

  const logout = useCallback(async () => {
    try {
      if (getAccessToken()) await api.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const can = useCallback((permission: string) => hasPermission(user, permission), [user]);
  const value = useMemo(
    () => ({ ready, user, token, can, login, logout }),
    [ready, user, token, can, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { ready, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (ready && !user) void navigate({ to: "/", replace: true });
  }, [ready, user, navigate]);

  if (!ready)
    return (
      <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">
        Restoring your session…
      </div>
    );
  if (!user) return null;
  if (!canVisit(user, location.pathname)) return <AccessDenied />;
  return (
    <div key={authorizationKey(user)} className="contents">
      {children}
    </div>
  );
}

export function AccessDenied() {
  return (
    <section role="alert" className="mx-auto max-w-lg space-y-3 rounded-xl border p-6">
      <h1 className="text-xl font-semibold">Access denied</h1>
      <p>
        Your account does not have permission to open this page. Contact an administrator if you
        need access.
      </p>
      <a href="/settings" className="text-primary underline">
        Go to your account
      </a>
    </section>
  );
}
