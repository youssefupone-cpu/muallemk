import type { FileRejection } from "react-dropzone";
import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { uploadDocument } from "../lib/api";
import { toast } from "sonner";
import { errMsg } from "../lib/utils";

interface Props {
  onUploaded: (count: number) => void;
  onError?: (msg: string) => void;
  accept?: Record<string, string[]>;
  maxFiles?: number;
  maxSize?: number;
}

/**
 * Drag-and-drop upload zone مع التحقق من الحجم/النوع والأثر المرئي
 * (P4-238). يستبدل <input type="file"> البسيط.
 */
export function DragDropUpload({
  onUploaded,
  onError,
  accept = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
      ".docx",
    ],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
      ".xlsx",
    ],
    "text/plain": [".txt", ".md"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
  },
  maxFiles = 10,
  maxSize = 10 * 1024 * 1024, // 10 MB افتراضي
}: Props) {
  const [rejected, setRejected] = useState<FileRejection[]>([]);

  const onDrop = async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setRejected([]);
    try {
      const uploaded = await uploadDocument(acceptedFiles, (pct) => {
        toast(`جارٍ الرفع… ${pct}%`, { id: "upload-progress" });
      });
      toast.success(`تم رفع ${uploaded.length} ملف بنجاح`);
      onUploaded(uploaded.length);
    } catch (err) {
      toast.error(errMsg(err));
      onError?.(errMsg(err));
    }
  };

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
  } = useDropzone({
    onDrop: onDrop,
    accept,
    maxFiles,
    maxSize,
    onDropRejected: (rej) => setRejected(rej),
  });

  const zoneStyle = useMemo(() => {
    if (isDragReject) return "border-red-400 bg-red-50";
    if (isDragAccept) return "border-green-400 bg-green-50";
    if (isDragActive) return "border-blue-400 bg-blue-50";
    return "border-slate-300 bg-slate-50 hover:border-slate-400";
  }, [isDragAccept, isDragReject, isDragActive]);

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-slate-700">
        رفع ملفات (PDF/Word/نص/صورة OCR — حتى {maxFiles} ملفات)
      </label>

      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${zoneStyle}`}
      >
        <input {...getInputProps()} disabled={false} />
        <Upload className="mx-auto h-8 w-8 text-slate-400" />
        {isDragActive ? (
          <p className="mt-2 text-sm text-slate-600">اترك الملفات هنا…</p>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            اسحب الملفات هنا أو انقر للاختيار
          </p>
        )}
        <p className="mt-1 text-xs text-slate-500">
          الحد الأقصى: {(maxSize / 1024 / 1024).toFixed(0)} MB لكل ملف
        </p>
      </div>

      {rejected.length > 0 && (
        <ul className="list-disc list-inside space-y-1 text-sm text-red-600">
          {rejected.map(({ file, errors }) => (
            <li key={file.path}>
              {file.path} — {errors.map((e) => e.message).join("؛ ")}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
