import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { FolderOpen, FolderPlus, Trash2, ChevronRight, Scale } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { createFolder, deleteFolder, fetchFolders } from "@/lib/api";

export function HomePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: folders = [], isLoading } = useQuery({ queryKey: ["folders"], queryFn: fetchFolders });
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const createMutation = useMutation({
    mutationFn: createFolder,
    onSuccess: (folder) => {
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      setNewName("");
      setCreating(false);
      navigate(`/folders/${folder.id}`);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteFolder,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["folders"] }),
  });

  function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    createMutation.mutate(name);
  }

  function handleDelete(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    const confirmed = window.confirm("Excluir esta pasta? Todos os RGs, certidoes e processos vinculados a ela tambem serao apagados.");
    if (!confirmed) return;
    deleteMutation.mutate(id);
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Scale className="h-5 w-5" />
            </span>
            Análise de Precatórios
          </h1>
          <p className="text-sm text-muted-foreground mt-1 ml-13">
            Selecione ou crie uma pasta para iniciar a análise.
          </p>
        </div>
        <Button onClick={() => setCreating(true)} disabled={creating}>
          <FolderPlus className="h-4 w-4" />
          Nova Pasta
        </Button>
      </div>

      {creating && (
        <Card className="border-primary/30 shadow-md">
          <CardContent className="p-4">
            <p className="text-sm font-semibold mb-3 text-foreground">Nome da nova pasta</p>
            <div className="flex gap-2">
              <Input
                autoFocus
                placeholder="Ex: Precatório 001 — João Silva"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreate();
                  if (e.key === "Escape") { setCreating(false); setNewName(""); }
                }}
                className="flex-1"
              />
              <Button onClick={handleCreate} disabled={!newName.trim() || createMutation.isPending}>
                Criar
              </Button>
              <Button
                variant="outline"
                onClick={() => { setCreating(false); setNewName(""); }}
              >
                Cancelar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Carregando pastas...</p>
      ) : folders.length === 0 && !creating ? (
        <div className="flex flex-col items-center justify-center py-24 text-center space-y-4 border-2 border-dashed rounded-xl text-muted-foreground">
          <FolderOpen className="h-14 w-14 opacity-20" />
          <div>
            <p className="font-semibold text-base">Nenhuma pasta criada</p>
            <p className="text-sm mt-1">Clique em "Nova Pasta" para começar uma análise.</p>
          </div>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {folders.map((folder) => (
            <button
              key={folder.id}
              className="group text-left rounded-xl border bg-card p-5 shadow-sm hover:border-primary/40 hover:shadow-md transition-all flex items-center justify-between gap-4"
              onClick={() => navigate(`/folders/${folder.id}`)}
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
                  <FolderOpen className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold text-foreground truncate">{folder.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Criado em {new Date(folder.created_at).toLocaleDateString("pt-BR")}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                  onClick={(e) => handleDelete(e, folder.id)}
                  title="Excluir pasta"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
