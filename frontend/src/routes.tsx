import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { HomePage } from "@/pages/HomePage";
import { FolderPage } from "@/pages/FolderPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DocumentDetailPage } from "@/pages/DocumentDetailPage";
import { RGPage } from "@/pages/RGPage";
import { RGDetailPage } from "@/pages/RGDetailPage";
import { ProcessosPage } from "@/pages/ProcessosPage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <HomePage /> },
      {
        path: "folders/:folderId",
        children: [
          { index: true, element: <FolderPage /> },
          { path: "certidao", element: <DashboardPage /> },
          { path: "certidao/:id", element: <DocumentDetailPage /> },
          { path: "rg", element: <RGPage /> },
          { path: "rg/:rgId", element: <RGDetailPage /> },
          { path: "processos", element: <ProcessosPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
