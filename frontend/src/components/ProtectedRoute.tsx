import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuthStore } from "@/store/auth";

function isValidJwt(token: string | null): boolean {
  if (!token) return false;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const payload = JSON.parse(atob(parts[1]));
    return typeof payload.exp === "number" && payload.exp > Date.now() / 1000;
  } catch {
    return false;
  }
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((state) => state.accessToken);
  const logout = useAuthStore((state) => state.logout);

  if (!isValidJwt(token)) {
    if (token) logout(); // limpa token inválido/expirado
    return <Navigate to="/login" replace />;
  }

  return children;
}
