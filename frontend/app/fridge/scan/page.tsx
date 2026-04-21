"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useScanFridge, useSubmitCorrections } from "@/lib/hooks/useFridge";
import type { CorrectionEntry, DetectedItem } from "@/types/fridge";

const MAX_DIMENSION = 2048;

interface EditableItem {
  original: DetectedItem;
  current: DetectedItem;
  isDirty: boolean;
}

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
  const { t } = useTranslation();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [editableItems, setEditableItems] = useState<EditableItem[] | null>(null);
  const scanMutation = useScanFridge();
  const submitCorrectionsMutation = useSubmitCorrections();

  useEffect(() => {
    if (editableItems !== null) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [editableItems]);

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
    setEditableItems(null);

    const result = await scanMutation.mutateAsync(prepared);
    setEditableItems(
      result.detected.map((item) => ({ original: item, current: { ...item }, isDirty: false }))
    );
  }

  function handleRetake() {
    setPreview(null);
    setEditableItems(null);
    scanMutation.reset();
  }

  function updateItem(idx: number, field: keyof DetectedItem, rawValue: string) {
    setEditableItems((prev) => {
      if (!prev) return prev;
      const updated = [...prev];
      const ei = { ...updated[idx] };
      const current = { ...ei.current };

      if (field === "quantity") {
        const parsed = parseFloat(rawValue);
        (current as Record<string, unknown>)[field] = isNaN(parsed) ? 0 : parsed;
      } else {
        (current as Record<string, unknown>)[field] = rawValue;
      }

      ei.current = current;
      ei.isDirty =
        current.item_name !== ei.original.item_name ||
        current.quantity !== ei.original.quantity ||
        current.unit !== ei.original.unit;
      updated[idx] = ei;
      return updated;
    });
  }

  const hasDirtyItems = editableItems?.some((ei) => ei.isDirty) ?? false;
  const dirtyCount = editableItems?.filter((ei) => ei.isDirty).length ?? 0;

  async function handleConfirm() {
    if (hasDirtyItems && editableItems) {
      const corrections: CorrectionEntry[] = editableItems
        .filter((ei) => ei.isDirty)
        .map((ei) => ({
          original_name: ei.original.item_name,
          original_quantity: ei.original.quantity,
          original_unit: ei.original.unit,
          corrected_name: ei.current.item_name,
          corrected_quantity: ei.current.quantity,
          corrected_unit: ei.current.unit,
        }));
      await submitCorrectionsMutation.mutateAsync(corrections);
    }
    router.push("/recipes");
  }

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50">
      <div className="max-w-lg mx-auto px-4 py-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">{t("scan.title")}</h1>
          <p className="text-slate-500 mt-1 text-sm">{t("scan.subtitle")}</p>
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
              <p className="font-semibold text-slate-800">{t("scan.uploadTitle")}</p>
              <p className="text-sm text-slate-400 mt-1">{t("scan.uploadSubtitle")}</p>
            </div>
          </button>
        )}

        {/* Step 2 — Preview + results */}
        {preview && (
          <div className="flex flex-col gap-4">
            <div className="relative">
              <img
                src={preview}
                alt="Fridge photo"
                className={[
                  "rounded-xl w-full object-cover transition-all duration-300",
                  editableItems || scanMutation.isPending ? "max-h-44" : "max-h-72",
                ].join(" ")}
              />
              <button
                onClick={handleRetake}
                className="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white text-xs px-2.5 py-1 rounded-full transition-colors"
              >
                {t("scan.retakeButton")}
              </button>
            </div>

            {/* Analyzing state */}
            {scanMutation.isPending && (
              <div ref={analyzeRef}>
                <Card className="flex items-center gap-3 bg-green-50 border-green-200">
                  <Spinner size="sm" />
                  <div>
                    <p className="text-sm font-medium text-green-800">{t("scan.analysingTitle")}</p>
                    <p className="text-xs text-green-600">{t("scan.analysingSubtitle")}</p>
                  </div>
                </Card>
              </div>
            )}

            {/* Error state */}
            {scanMutation.isError && (
              <Card className="border-red-200 bg-red-50">
                <p className="text-sm font-medium text-red-700">{t("scan.scanFailed")}</p>
                <p className="text-xs text-red-500 mt-1">{scanMutation.error?.message}</p>
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-3"
                  onClick={() => inputRef.current?.click()}
                >
                  {t("scan.tryAgainButton")}
                </Button>
              </Card>
            )}

            {/* Results */}
            {editableItems && (
              <div ref={resultsRef} className="flex flex-col gap-3">
                <Card>
                  <div className="flex items-center justify-between mb-3">
                    <h2 className="font-semibold text-slate-900">
                      {t("scan.itemsDetected", { count: editableItems.length })}
                    </h2>
                    <Badge variant={editableItems.length > 0 ? "green" : "gray"}>
                      {t("scan.savedToFridge")}
                    </Badge>
                  </div>

                  {editableItems.length === 0 ? (
                    <p className="text-sm text-slate-500">{t("scan.nothingDetected")}</p>
                  ) : (
                    <ul className="divide-y divide-slate-100">
                      {editableItems.map((ei, idx) => (
                        <li key={idx} className="py-2.5 first:pt-0 last:pb-0">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              {/* Item name */}
                              <input
                                type="text"
                                value={ei.current.item_name}
                                onChange={(e) => updateItem(idx, "item_name", e.target.value)}
                                className="text-sm font-medium text-slate-800 capitalize bg-transparent border border-transparent rounded px-1 focus:border-slate-300 focus:outline-none focus:bg-white w-full min-w-0"
                              />
                            </div>
                            <div className="flex items-center gap-1 shrink-0">
                              {/* Quantity */}
                              <input
                                type="number"
                                value={ei.current.quantity}
                                onChange={(e) => updateItem(idx, "quantity", e.target.value)}
                                className="text-xs text-slate-500 bg-transparent border border-transparent rounded px-1 focus:border-slate-300 focus:outline-none focus:bg-white w-14 text-right"
                              />
                              {/* Unit */}
                              <input
                                type="text"
                                value={ei.current.unit}
                                onChange={(e) => updateItem(idx, "unit", e.target.value)}
                                className="text-xs text-slate-500 bg-transparent border border-transparent rounded px-1 focus:border-slate-300 focus:outline-none focus:bg-white w-14"
                              />
                              {ei.isDirty ? (
                                <span className="text-xs font-medium text-amber-600 bg-amber-50 rounded px-1.5 py-0.5">
                                  {t("scan.editedLabel")}
                                </span>
                              ) : (
                                <Badge variant={ei.current.confidence >= 0.8 ? "green" : "yellow"}>
                                  {Math.round(ei.current.confidence * 100)}%
                                </Badge>
                              )}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>

                <div className="flex flex-col gap-2">
                  <Button
                    onClick={handleConfirm}
                    className="w-full"
                    size="lg"
                    disabled={submitCorrectionsMutation.isPending}
                  >
                    {submitCorrectionsMutation.isPending ? (
                      <span className="flex items-center gap-2">
                        <Spinner size="sm" />
                        <span>Saving…</span>
                      </span>
                    ) : hasDirtyItems ? (
                      t("scan.confirmWithCorrections", { count: dirtyCount })
                    ) : (
                      t("scan.confirmCta")
                    )}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => router.push("/fridge")}
                    className="w-full"
                  >
                    {t("scan.viewFridgeCta")}
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
