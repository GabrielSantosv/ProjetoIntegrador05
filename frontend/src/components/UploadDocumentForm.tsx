import { Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { PdfPreviewModal } from "@/components/PdfPreviewModal";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { detectDocumentType } from "@/lib/api";

export interface ConfirmedUploadValues {
  file: File;
  originalFilename: string;
  finalDocumentName: string;
  detectedDocumentType: string;
  finalDocumentType: string;
  documentTypeWasEdited: boolean;
  documentNameWasEdited: boolean;
}

interface Props {
  onUpload: (values: ConfirmedUploadValues) => Promise<void>;
}

const UNKNOWN_TYPE = "Tipo desconhecido";

export function UploadDocumentForm({ onUpload }: Props) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [documentName, setDocumentName] = useState("");
  const [detectedDocumentType, setDetectedDocumentType] = useState(UNKNOWN_TYPE);
  const [detectedDocumentTypeCode, setDetectedDocumentTypeCode] = useState(UNKNOWN_TYPE);
  const [selectedDocumentType, setSelectedDocumentType] = useState(UNKNOWN_TYPE);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const replaceInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [selectedFile]);

  async function prepareFile(file: File | undefined) {
    setError(null);
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Selecione um arquivo PDF valido.");
      resetFileInputs();
      return;
    }

    setSelectedFile(file);
    setDocumentName(file.name);
    setDetectedDocumentType(UNKNOWN_TYPE);
    setDetectedDocumentTypeCode(UNKNOWN_TYPE);
    setSelectedDocumentType(UNKNOWN_TYPE);

    console.debug("[UPLOAD_PREVIEW] arquivo selecionado", {
      originalFilename: file.name,
    });

    try {
      setIsDetecting(true);
      const detection = await detectDocumentType(file);
      console.debug("[UPLOAD_PREVIEW] deteccao finalizada", detection);
      setDetectedDocumentType(detection.document_label);
      setDetectedDocumentTypeCode(detection.document_type || UNKNOWN_TYPE);
      setSelectedDocumentType(detection.document_label);
    } catch (err) {
      console.error("[UPLOAD_PREVIEW] falha ao detectar tipo", err);
      // Fallback stays unknown
    } finally {
      setIsDetecting(false);
    }
  }

  async function confirmUpload() {
    if (!selectedFile) return;

    const finalDocumentName = documentName.trim() || selectedFile.name;
    const payload: ConfirmedUploadValues = {
      file: selectedFile,
      originalFilename: selectedFile.name,
      finalDocumentName,
      detectedDocumentType,
      finalDocumentType: selectedDocumentType || UNKNOWN_TYPE,
      documentTypeWasEdited: selectedDocumentType !== detectedDocumentType,
      documentNameWasEdited: finalDocumentName !== selectedFile.name,
    };

    console.debug("[UPLOAD_PREVIEW] confirmando envio", {
      originalFilename: payload.originalFilename,
      finalDocumentName: payload.finalDocumentName,
      detectedDocumentType: payload.detectedDocumentType,
      finalDocumentType: payload.finalDocumentType,
      documentTypeWasEdited: payload.documentTypeWasEdited,
      documentNameWasEdited: payload.documentNameWasEdited,
    });

    try {
      setIsSubmitting(true);
      await onUpload(payload);
      clearPreview();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Nao foi possivel enviar o PDF.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function clearPreview() {
    setSelectedFile(null);
    setDocumentName("");
    setDetectedDocumentType(UNKNOWN_TYPE);
    setDetectedDocumentTypeCode(UNKNOWN_TYPE);
    setSelectedDocumentType(UNKNOWN_TYPE);
    setError(null);
    resetFileInputs();
  }

  function resetFileInputs() {
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (replaceInputRef.current) replaceInputRef.current.value = "";
  }

  return (
    <>
      <Card className="border-2 border-primary/20 transition-all hover:border-primary/40 hover:shadow-lg">
        <CardHeader className="bg-gradient-to-r from-primary/5 to-transparent">
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Novo Processamento
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid gap-4 md:grid-cols-[1fr_auto]">
            <div className="space-y-2">
              <Label htmlFor="file" className="font-semibold text-foreground">
                Selecionar PDF
              </Label>
              <Input
                ref={fileInputRef}
                id="file"
                type="file"
                accept="application/pdf"
                className="file:cursor-pointer file:font-semibold file:text-primary hover:file:text-primary/80"
                onChange={(event) => prepareFile(event.target.files?.[0])}
              />
              {error && !selectedFile && <p className="text-sm font-medium text-destructive">{error}</p>}
            </div>
            <Button className="self-end" type="button" onClick={() => fileInputRef.current?.click()}>
              <Upload className="h-4 w-4" />
              Escolher PDF
            </Button>
          </div>
        </CardContent>
      </Card>

      <input
        ref={replaceInputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(event) => prepareFile(event.target.files?.[0])}
      />

      {selectedFile && previewUrl && (
        <PdfPreviewModal
          file={selectedFile}
          previewUrl={previewUrl}
          detectedDocumentType={isDetecting ? "Detectando..." : detectedDocumentType}
          detectedDocumentTypeCode={isDetecting ? "" : detectedDocumentTypeCode}
          selectedDocumentType={selectedDocumentType}
          documentName={documentName}
          isSubmitting={isSubmitting}
          error={error}
          onChangeDocumentName={setDocumentName}
          onChangeDocumentType={setSelectedDocumentType}
          onCancel={clearPreview}
          onConfirm={confirmUpload}
          onReplaceFile={() => replaceInputRef.current?.click()}
        />
      )}
    </>
  );
}
