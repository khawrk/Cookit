"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Spinner } from "@/components/ui/Spinner";
import { useAddFridgeItem, useCondimentsCatalog } from "@/lib/hooks/useFridge";

const UNIT_OPTIONS = [
  { value: "count", label: "count" },
  { value: "g", label: "grams (g)" },
  { value: "ml", label: "ml" },
  { value: "bottle", label: "bottle" },
  { value: "jar", label: "jar" },
  { value: "pack", label: "pack" },
  { value: "tbsp", label: "tablespoon" },
  { value: "tsp", label: "teaspoon" },
  { value: "cup", label: "cup" },
  { value: "bunch", label: "bunch" },
];

export default function ManualAddPage() {
  const router = useRouter();
  const { data: catalog, isLoading: catalogLoading } = useCondimentsCatalog();
  const addMutation = useAddFridgeItem();

  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("count");
  const [catalogSearch, setCatalogSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

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
      setError(err instanceof Error ? err.message : "Failed to add item");
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
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Add Item Manually</h1>
        <p className="text-gray-500 mb-6">Select a condiment from the catalogue or type a custom item.</p>

        {/* Condiment catalogue search */}
        <Card className="mb-6">
          <h2 className="font-semibold text-gray-800 mb-3">Condiments Catalogue</h2>
          {catalogLoading ? (
            <div className="flex justify-center py-4">
              <Spinner size="sm" />
            </div>
          ) : (
            <>
              <Input
                placeholder="Search condiments…"
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
                  <p className="text-sm text-gray-400 px-2 py-2">No matches</p>
                )}
              </ul>
            </>
          )}
        </Card>

        {/* Manual form */}
        <Card>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Item name"
              id="item_name"
              placeholder="e.g. fish sauce"
              value={itemName}
              required
              onChange={(e) => setItemName(e.target.value)}
            />
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Quantity"
                id="quantity"
                type="number"
                min="0"
                step="any"
                placeholder="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
              <Select
                label="Unit"
                id="unit"
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                options={UNIT_OPTIONS}
              />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            {success && (
              <p className="text-sm text-green-600">Item added to your fridge!</p>
            )}
            <div className="flex gap-2">
              <Button variant="secondary" type="button" onClick={() => router.push("/fridge")}>
                Back to Fridge
              </Button>
              <Button type="submit" loading={addMutation.isPending} className="flex-1">
                Add to Fridge
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
