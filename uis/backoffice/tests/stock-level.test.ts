import { compareSuppliesByNeed, quantityExceedsStock, stockBand } from "../src/lib/stock-level";

test("stock at zero is out", () => {
  expect(stockBand(0)).toBe("out");
});

test("stock from 1 through 10 is low", () => {
  expect(stockBand(1)).toBe("low");
  expect(stockBand(10)).toBe("low");
});

test("stock of 11 or more is healthy", () => {
  expect(stockBand(11)).toBe("healthy");
});

test("supplies sort out of stock, then low, then healthy, then by name", () => {
  const rows = [
    { name: "Saline", current_stock: 40 },
    { name: "Gauze", current_stock: 0 },
    { name: "Masks", current_stock: 4 },
    { name: "Gloves", current_stock: 0 },
  ];
  const ordered = [...rows].sort(compareSuppliesByNeed);
  expect(ordered.map((row) => row.name)).toEqual(["Gauze", "Gloves", "Masks", "Saline"]);
});

test("a quantity above available stock is flagged before submit", () => {
  expect(quantityExceedsStock(12, 11)).toBe(true);
  expect(quantityExceedsStock(11, 11)).toBe(false);
});
