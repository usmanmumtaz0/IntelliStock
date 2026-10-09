import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "@tanstack/react-router";
import { api, clearAccessToken, getAccessToken, setAccessToken, type AuthUser } from "./api";

interface AuthContextValue {
  ready: boolean;
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const clearSession = useCallback(() => {
    clearAccessToken();
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const existingToken = getAccessToken();
    if (!existingToken) {
      setReady(true);
      return;
    }
    setToken(existingToken);
    api
      .verify()
      .then((verified) => {
        setUser({
          userId: verified.user_id,
          username: verified.username,
          email: verified.email,
          role: verified.role,
        });
      })
      .catch(clearSession)
      .finally(() => setReady(true));
  }, [clearSession]);

  useEffect(() => {
    const onUnauthorized = () => clearSession();
    window.addEventListener("intellistock:unauthorized", onUnauthorized);
    return () => window.removeEventListener("intellistock:unauthorized", onUnauthorized);
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.login(email, password);
    setAccessToken(response.access_token);
    setToken(response.access_token);
    setUser({
      userId: response.user_id,
      username: response.username,
      email: response.email,
      role: response.role,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      if (getAccessToken()) await api.logout();
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ ready, user, token, login, logout }),
    [ready, user, token, login, logout],
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
  return children;
}
