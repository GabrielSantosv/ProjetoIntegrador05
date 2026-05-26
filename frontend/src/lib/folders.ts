export interface Folder {
  id: string;
  name: string;
  createdAt: string;
}

const STORAGE_KEY = "precatorio_folders";

export function getFolders(): Folder[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Folder[]) : [];
  } catch {
    return [];
  }
}

export function getFolder(id: string): Folder | undefined {
  return getFolders().find((f) => f.id === id);
}

export function createFolder(name: string): Folder {
  const folder: Folder = {
    id: crypto.randomUUID(),
    name: name.trim(),
    createdAt: new Date().toISOString(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...getFolders(), folder]));
  return folder;
}

export function deleteFolder(id: string): void {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(getFolders().filter((f) => f.id !== id)),
  );
}
