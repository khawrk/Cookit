"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { useAddFridgeItem, useCondimentsCatalog } from "@/lib/hooks/useFridge";

export default function ManualAddPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { data: catalog, isLoading: catalogLoading } = useCondimentsCatalog();
  const addMutation = useAddFridgeItem();

  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("count");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Derived inside component so t() is available
  const UNIT_OPTIONS = [
    { value: "count", label: t("manual.units.count") },
    { value: "g", label: t("manual.units.g") },
    { value: "ml", label: t("manual.units.ml") },
    { value: "bottle", label: t("manual.units.bottle") },
    { value: "jar", label: t("manual.units.jar") },
    { value: "pack", label: t("manual.units.pack") },
    { value: "tbsp", label: t("manual.units.tbsp") },
    { value: "tsp", label: t("manual.units.tsp") },
    { value: "cup", label: t("manual.units.cup") },
    { value: "bunch", label: t("manual.units.bunch") },
  ];

  const filteredCatalog = catalog?.filter((c) =>
    c.name.toLowerCase().includes(catalogSearch.toLowerCase())
  );

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!itemName.trim()) return;
    setError(null);
    try {
      await addMutation.mutateAsync({
        item_name: itemName.trim().toLowerCase(),
        quantity: quantity ? parseFloat(quantity) : undefined,
        unit: unit || undefined,
        source: "manual",
      });
      setSuccess(true);
      setItemName("");
      setQuantity("");
      setUnit("count");
      setCatalogSearch("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("login.somethingWentWrong"));
    }
  }

  function selectFromCatalog(name: string, defaultUnit: string | null) {
    setItemName(name);
    if (defaultUnit) setUnit(defaultUnit);
    setCatalogSearch(name);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-lg mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{t("manual.title")}</h1>
        <p className="text-gray-500 mb-6">{t("manual.subtitle")}</p>

        {/* Condiment catalogue search */}
        <Card className="mb-6">
          <h2 className="font-semibold text-gray-800 mb-3">{t("manual.catalogueTitle")}</h2>
          {catalogLoading ? (
            <div className="flex justify-center py-4">
              <Spinner size="sm" />
            </div>
          ) : (
            <>
              <Input
                placeholder={t("manual.catalogueSearch")}
                value={catalogSearch}
                onChange={(e) => setCatalogSearch(e.target.value)}
                className="mb-3"
              />
              <ul className="max-h-48 overflow-y-auto flex flex-col gap-1">
                {filteredCatalog?.slice(0, 30).map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => selectFromCatalog(item.name, item.default_unit)}
                      className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-green-50 hover:text-green-700 capitalize"
                    >
                      {item.name}
                      {item.default_unit && (
                        <span className="text-gray-400 ml-1">({item.default_unit})</span>
                      )}
                    </button>
                  </li>
                ))}
                {filteredCatalog?.length === 0 && (
                  <p className="text-sm text-gray-400 px-2 py-2">{t("manual.noMatches")}</p>
                )}
              </ul>
            </>
          )}
        </Card>

        {/* Manual form */}
        <Card>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label={t("manual.itemNameLabel")}
              id="item_name"
              placeholder={t("manual.itemNamePlaceholder")}
              value={itemName}
              required
              onChange={(e) => setItemName(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={t("manual.quantityLabel")}
                id="quantity"
                type="number"
                min="0"
                step="any"
                placeholder="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
              <Select
                label={t("manual.unitLabel")}
                id="unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                options={UNIT_OPTIONS}
              />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            {success && (
              <p className="text-sm text-green-600">{t("manual.successMessage")}</p>
            )}
            <div className="flex gap-2">
              <Button variant="secondary" type="button" onClick={() => router.push("/fridge")}>
                {t("manual.backButton")}
              </Button>
              <Button type="submit" loading={addMutation.isPending} className="flex-1">
                {t("manual.addButton")}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
