export interface FridgeItem {
  id: string;
  item_name: string;
  category: string | null;
  quantity: number | null;
  unit: string | null;
  source: "vision" | "manual";
  confidence: number | null;
  updated_at: string;
}

export interface DetectedItem {
  item_name: string;
  category: string;
  quantity: number;
  unit: string;
  confidence: number;
}

export interface ScanResponse {
  detected: DetectedItem[];
  saved_count: number;
}

export interface CondimentCatalogItem {
  id: string;
  name: string;
  category: string | null;
  default_unit: string | null;
}

export interface FridgeItemIn {
  item_name: string;
  category?: string;
  quantity?: number;
  unit?: string;
  source?: string;
}

export interface FridgeItemUpdate {
  quantity?: number;
  unit?: string;
  category?: string;
}
