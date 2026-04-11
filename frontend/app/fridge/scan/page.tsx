"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useScanFridge } from "@/lib/hooks/useFridge";
import type { DetectedItem } from "@/types/fridge";

const MAX_DIMENSION = 2048;

function isHeic(file: File): boolean {
  return (
    file.type === "image/heic" ||
    file.type === "image/heif" ||
    /\.(heic|heif)$/i.test(file.name)
  );
}

async function convertHeicToJpeg(file: File): Promise<File> {
  const heic2any = (await import("heic2any")).default;
  const blob = await heic2any({ blob: file, toType: "image/jpeg", quality: 0.9 }) as Blob;
  return new File([blob], file.name.replace(/\.(heic|heif)$/i, ".jpg"), { type: "image/jpeg" });
}

async function prepareImage(file: File): Promise<File> {
  // Convert HEIC first — browsers can't decode it natively
  const source = isHeic(file) ? await convertHeicToJpeg(file) : file;

  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(source);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const { width, height } = img;
      if (width <= MAX_DIMENSION && height <= MAX_DIMENSION) {
        resolve(source);
        return;
      }
      const scale = Math.min(MAX_DIMENSION / width, MAX_DIMENSION / height);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => resolve(new File([blob!], source.name, { type: "image/jpeg" })),
        "image/jpeg",
        0.9
      );
    };
    img.src = url;
  });
}

export default function ScanPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [detectedItems, setDetectedItems] = useState<DetectedItem[] | null>(null);
  const scanMutation = useScanFridge();

  // Auto-scroll to results as soon as they arrive — fixes the "can't see results" bug on mobile
  useEffect(() => {
    if (detectedItems !== null) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [detectedItems]);

  // Also scroll to analyzing spinner so user knows something is happening
  const analyzeRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (scanMutation.isPending) {
      analyzeRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [scanMutation.isPending]);

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const prepared = await prepareImage(file);
    setPreview(URL.createObjectURL(prepared));
    setDetectedItems(null);

    const result = await scanMutation.mutateAsync(prepared);
    setDetectedItems(result.detected);
  }

  function handleRetake() {
    setPreview(null);
    setDetectedItems(null);
    scanMutation.reset();
  }

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50">
      <div className="max-w-lg mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Scan Your Fridge</h1>
          <p className="text-slate-500 mt-1 text-sm">AI will detect everything visible in your photo.</p>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept="image/*,.heic,.heif"
          capture="environment"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Step 1 — Upload prompt */}
        {!preview && (
          <button
            onClick={() => inputRef.current?.click()}
            className="w-full rounded-2xl border-2 border-dashed border-slate-300 bg-white hover:border-green-400 hover:bg-green-50 transition-colors cursor-pointer py-16 flex flex-col items-center gap-4 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
          >
            <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center">
              <svg className="h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div className="text-center">
              <p className="font-semibold text-slate-800">Take or upload a photo</p>
              <p className="text-sm text-slate-400 mt-1">Camera, gallery, or AirDrop HEIC — all supported</p>
            </div>
          </button>
        )}

        {/* Step 2 — Preview + results */}
        {preview && (
          <div className="flex flex-col gap-4">
            {/* Thumbnail — smaller once scanning starts so results fit on screen */}
            <div className="relative">
              <img
                src={preview}
                alt="Fridge photo"
                className={[
                  "rounded-xl w-full object-cover transition-all duration-300",
                  detectedItems || scanMutation.isPending ? "max-h-44" : "max-h-72",
                ].join(" ")}
              />
              <button
                onClick={handleRetake}
                className="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white text-xs px-2.5 py-1 rounded-full transition-colors"
              >
                Retake
              </button>
            </div>

            {/* Analyzing state */}
            {scanMutation.isPending && (
              <div ref={analyzeRef}>
                <Card className="flex items-center gap-3 bg-green-50 border-green-200">
                  <Spinner size="sm" />
                  <div>
                    <p className="text-sm font-medium text-green-800">Analysing your fridge…</p>
                    <p className="text-xs text-green-600">This takes about 5–10 seconds</p>
                  </div>
                </Card>
              </div>
            )}

            {/* Error state */}
            {scanMutation.isError && (
              <Card className="border-red-200 bg-red-50">
                <p className="text-sm font-medium text-red-700">Scan failed</p>
                <p className="text-xs text-red-500 mt-1">{scanMutation.error?.message}</p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-3"
                  onClick={() => inputRef.current?.click()}
                >
                  Try again
                </Button>
              </Card>
            )}

            {/* Results */}
            {detectedItems && (
              <div ref={resultsRef} className="flex flex-col gap-3">
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="font-semibold text-slate-900">
                      {detectedItems.length} item{detectedItems.length !== 1 ? "s" : ""} detected
                    </h2>
                    <Badge variant={detectedItems.length > 0 ? "green" : "gray"}>
                      Saved to fridge
                    </Badge>
                  </div>

                  {detectedItems.length === 0 ? (
                    <p className="text-sm text-slate-500">Nothing detected — try a clearer photo with better lighting.</p>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {detectedItems.map((item, idx) => (
                        <li key={idx} className="flex items-center justify-between py-2.5 first:pt-0 last:pb-0">
                          <div>
                            <span className="capitalize text-sm font-medium text-slate-800">{item.item_name}</span>
                            <span className="text-xs text-slate-400 ml-2">
                              {item.quantity} {item.unit}
                            </span>
                          </div>
                          <Badge variant={item.confidence >= 0.8 ? "green" : "yellow"}>
                            {Math.round(item.confidence * 100)}%
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>

                {/* Next steps — clearly visible */}
                <div className="flex flex-col gap-2">
                  <Button onClick={() => router.push("/recipes")} className="w-full" size="lg">
                    Get Recipe Recommendations
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => router.push("/fridge")}
                    className="w-full"
                  >
                    View My Fridge
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
