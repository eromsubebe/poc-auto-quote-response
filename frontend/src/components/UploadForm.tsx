"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { uploadRFQ } from "@/lib/api";
import { Button } from "./ui/button";
import { Upload, FileText, Loader2 } from "lucide-react";

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith(".eml")) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError("Please upload an .eml file");
      }
    }
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.name.endsWith(".eml")) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError("Please upload an .eml file");
      }
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const result = await uploadRFQ(file);
      router.push(`/rfqs/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : file
            ? "border-green-500 bg-green-50"
            : "border-gray-300 hover:border-gray-400"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          accept=".eml"
          onChange={handleChange}
          className="hidden"
        />
        <label
          htmlFor="file-upload"
          className="cursor-pointer flex flex-col items-center gap-2"
        >
          {file ? (
            <>
              <FileText className="w-12 h-12 text-green-500" />
              <span className="font-medium text-green-700">{file.name}</span>
              <span className="text-sm text-green-600">
                {(file.size / 1024).toFixed(1)} KB
              </span>
            </>
          ) : (
            <>
              <Upload className="w-12 h-12 text-gray-400" />
              <span className="font-medium text-gray-700">
                Drop your .eml file here
              </span>
              <span className="text-sm text-gray-500">
                or click to browse
              </span>
            </>
          )}
        </label>
      </div>

      {error && (
        <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">
          {error}
        </div>
      )}

      <Button
        type="submit"
        disabled={!file || uploading}
        className="w-full"
      >
        {uploading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Upload className="w-4 h-4 mr-2" />
            Upload and Process RFQ
          </>
        )}
      </Button>

      {file && !uploading && (
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={() => {
            setFile(null);
            setError(null);
          }}
        >
          Clear
        </Button>
      )}
    </form>
  );
}
