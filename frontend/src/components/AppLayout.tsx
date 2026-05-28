import { FolderOpen, LogOut, Scale } from "lucide-react";
import { Link, Outlet, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth";

export function AppLayout() {
  const logout = useAuthStore((state) => state.logout);
  const email = useAuthStore((state) => state.email);
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-3 font-semibold">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Scale className="h-5 w-5" />
            </span>
            <span>Processamento Juridico</span>
          </Link>
          <div className="flex items-center gap-2">
            {email && <span className="hidden text-sm text-muted-foreground sm:inline">{email}</span>}
            <Button asChild variant="ghost" size="sm">
              <Link to="/">
                <FolderOpen className="h-4 w-4" />
                Pastas
              </Link>
            </Button>
            <Button
              variant="outline"
              size="icon"
              title="Sair"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
