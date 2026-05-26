import { useNavigate, useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, FileSearch, IdCard, Scale, ArrowLeft, Construction } from "lucide-react";

import { Button } from "@/components/ui/button";
import { fetchFolder } from "@/lib/api";

interface Module {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  path: string;
  available: boolean;
}

export function FolderPage() {
  const { folderId = "" } = useParams();
  const navigate = useNavigate();
  const { data: folder, isLoading } = useQuery({
    queryKey: ["folder", folderId],
    queryFn: () => fetchFolder(folderId),
    enabled: Boolean(folderId),
    retry: false,
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Carregando pasta...</p>;
  }

  if (!folder) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <p className="text-destructive font-bold">Pasta não encontrada.</p>
        <Button asChild variant="outline">
          <Link to="/">Voltar ao início</Link>
        </Button>
      </div>
    );
  }

  const modules: Module[] = [
    {
      id: "rg",
      title: "Extração de RG",
      description: "Leitura e extração automatizada de dados de documentos de identidade (RG).",
      icon: <IdCard className="h-8 w-8" />,
      path: `/folders/${folderId}/rg`,
      available: true,
    },
    {
      id: "certidao",
      title: "Análise de Certidão",
      description: "Processamento de certidões jurídicas com extração de entidades, score de risco e parecer técnico.",
      icon: <FileSearch className="h-8 w-8" />,
      path: `/folders/${folderId}/certidao`,
      available: true,
    },
    {
      id: "processos",
      title: "Análise de Processos",
      description: "Consulta e análise de processos judiciais extraídos das certidões processadas.",
      icon: <Scale className="h-8 w-8" />,
      path: `/folders/${folderId}/processos`,
      available: true,
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-4">
      <div>
        <Button asChild variant="ghost" size="sm" className="-ml-2 mb-2">
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            Pastas
          </Link>
        </Button>
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
          <span>Pastas</span>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground font-semibold">{folder.name}</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">{folder.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">Selecione o módulo de análise desejado.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {modules.map((mod) => (
          <div
            key={mod.id}
            className={`group relative rounded-xl border bg-card p-6 shadow-sm transition-all flex flex-col gap-4 ${
              mod.available
                ? "hover:border-primary/40 hover:shadow-md cursor-pointer"
                : "opacity-60 cursor-not-allowed"
            }`}
            onClick={() => mod.available && navigate(mod.path)}
          >
            {!mod.available && (
              <span className="absolute top-3 right-3 flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                <Construction className="h-3 w-3" />
                Em breve
              </span>
            )}

            <div className={`flex h-14 w-14 items-center justify-center rounded-xl ${
              mod.available ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
            }`}>
              {mod.icon}
            </div>

            <div className="flex-1 space-y-1">
              <p className="font-bold text-foreground">{mod.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{mod.description}</p>
            </div>

            {mod.available && (
              <div className="flex items-center gap-1 text-xs font-bold text-primary group-hover:gap-2 transition-all">
                Acessar
                <ChevronRight className="h-3.5 w-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
