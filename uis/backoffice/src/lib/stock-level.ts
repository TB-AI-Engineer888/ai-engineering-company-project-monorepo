/**
 * Stock bands on the medical supply list.
 * Healthy stock is 11 units or more.
 * Low stock is 1 through 10 units.
 * Out of stock is 0 units.
 */
export const LOW_STOCK_AT_OR_BELOW = 10;

export type StockBand = "healthy" | "low" | "out";

export function stockBand(currentStock: number): StockBand {
  if (currentStock <= 0) return "out";
  if (currentStock <= LOW_STOCK_AT_OR_BELOW) return "low";
  return "healthy";
}

export function quantityExceedsStock(quantity: number, currentStock: number): boolean {
  return Number.isFinite(quantity) && quantity > currentStock;
}

const BAND_RANK: Record<StockBand, number> = {
  out: 0,
  low: 1,
  healthy: 2,
};

export function compareSuppliesByNeed(
  left: { name: string; current_stock: number },
  right: { name: string; current_stock: number },
): number {
  const byBand = BAND_RANK[stockBand(left.current_stock)] - BAND_RANK[stockBand(right.current_stock)];
  if (byBand !== 0) return byBand;
  return left.name.localeCompare(right.name);
}
