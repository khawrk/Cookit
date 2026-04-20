"use client";

import Link from "next/link";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { useDeleteFridgeItem, useFridgeItems, useUpdateFridgeItem } from "@/lib/hooks/useFridge";
import type { FridgeItem } from "@/types/fridge";

const categoryColors: Record<string, "green" | "blue" | "yellow" | "red" | "gray"> = {
  produce: "green",
  dairy: "blue",
  protein: "red",
  condiment: "yellow",
  leftover: "gray",
  beverage: "blue",
  other: "gray",
};

function FridgeItemCard({ item }: { item: FridgeItem }) {
  const { t } = useTranslation();
  const [editOpen, setEditOpen] = useState(false);
  const [quantity, setQuantity] = useState(String(item.quantity ?? ""));
  const [unit, setUnit] = useState(item.unit ?? "");
  const updateMutation = useUpdateFridgeItem();
  const deleteMutation = useDeleteFridgeItem();

  async function handleSave() {
    await updateMutation.mutateAsync({
      id: item.id,
      payload: {
        quantity: quantity ? parseFloat(quantity) : undefined,
        unit: unit || undefined,
      },
    });
    setEditOpen(false);
  }

  return (
    <>
      <Card padding="sm" className="flex items-center justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-slate-900 truncate capitalize">{item.item_name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {item.category && (
              <Badge variant={categoryColors[item.category] ?? "gray"}>{item.category}</Badge>
            )}
            {item.quantity != null && (
              <span className="text-xs text-slate-400">
                {item.quantity} {item.unit}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button variant="ghost" size="sm" onClick={() => setEditOpen(true)}>
            {t("fridge.editButton")}
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate(item.id)}
          >
            {t("fridge.removeButton")}
          </Button>
        </div>
      </Card>

      <Modal open={editOpen} onClose={() => setEditOpen(false)} title={t("fridge.editModalTitle", { name: item.item_name })}>
        <div className="flex flex-col gap-4">
          <Input
            label={t("fridge.quantityLabel")}
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
          <Input
            label={t("fridge.unitLabel")}
            type="text"
            placeholder={t("fridge.unitPlaceholder")}
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setEditOpen(false)}>{t("fridge.cancelButton")}</Button>
            <Button loading={updateMutation.isPending} onClick={handleSave}>{t("fridge.saveButton")}</Button>
          </div>
        </div>
      </Modal>
    </>
  );
}

export default function FridgePage() {
  const { t } = useTranslation();
  const { data: items, isLoading, error } = useFridgeItems();

  return (
    <div className="min-h-[calc(100vh-56px)] bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 py-6">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h1 className="text-2xl font-bold text-slate-900">{t("fridge.title")}</h1>
          <div className="flex gap-2">
            <Link href="/fridge/scan">
              <Button size="sm">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {t("fridge.scanButton")}
              </Button>
            </Link>
            <Link href="/fridge/manual">
              <Button variant="secondary" size="sm">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                {t("fridge.addItemButton")}
              </Button>
            </Link>
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner />
          </div>
        )}

        {/* Error */}
        {error && (
          <Card className="text-center py-8 border-red-100">
            <p className="text-red-500 text-sm">{t("fridge.loadError")}</p>
          </Card>
        )}

        {/* Empty state */}
        {items && items.length === 0 && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <svg className="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10" />
              </svg>
            </div>
            <p className="text-slate-600 font-medium mb-1">{t("fridge.emptyTitle")}</p>
            <p className="text-slate-400 text-sm mb-6">{t("fridge.emptySubtitle")}</p>
            <div className="flex justify-center gap-3">
              <Link href="/fridge/scan">
                <Button>{t("fridge.scanCta")}</Button>
              </Link>
              <Link href="/fridge/manual">
                <Button variant="secondary">{t("fridge.addManuallyCta")}</Button>
              </Link>
            </div>
          </div>
        )}

        {/* Items list */}
        {items && items.length > 0 && (
          <>
            <div className="flex flex-col gap-2">
              {items.map((item) => (
                <FridgeItemCard key={item.id} item={item} />
              ))}
            </div>

            {/* Sticky CTA at bottom */}
            <div className="mt-6 sticky bottom-4">
              <Link href="/recipes">
                <Button size="lg" className="w-full shadow-lg shadow-green-200">
                  {t("fridge.recipesCta")}
                  <svg className="h-4 w-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
