import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  email: string | null;
  setTokens: (accessToken: string, refreshToken: string, email?: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      email: null,
      setTokens: (accessToken, refreshToken, email) =>
        set({ accessToken, refreshToken, email: email ?? null }),
      logout: () => set({ accessToken: null, refreshToken: null, email: null }),
    }),
    { name: "legal-docs-auth" },
  ),
);
