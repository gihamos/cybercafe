import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { LignePanier } from "../api/types";

const CART_KEY = "portail_panier";

interface CartState {
  items: LignePanier[];
  total: number;
  count: number;
  ajouter: (item: Omit<LignePanier, "quantite">, quantite?: number) => void;
  changerQuantite: (type: string, id: number, quantite: number) => void;
  retirer: (type: string, id: number) => void;
  vider: () => void;
}

const Ctx = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<LignePanier[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(CART_KEY) || "[]");
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(items));
  }, [items]);

  function ajouter(item: Omit<LignePanier, "quantite">, quantite = 1) {
    setItems((prev) => {
      const existant = prev.find((i) => i.type === item.type && i.id === item.id);
      if (existant) {
        return prev.map((i) =>
          i.type === item.type && i.id === item.id ? { ...i, quantite: i.quantite + quantite } : i
        );
      }
      return [...prev, { ...item, quantite }];
    });
  }

  function changerQuantite(type: string, id: number, quantite: number) {
    setItems((prev) =>
      quantite <= 0
        ? prev.filter((i) => !(i.type === type && i.id === id))
        : prev.map((i) => (i.type === type && i.id === id ? { ...i, quantite } : i))
    );
  }

  function retirer(type: string, id: number) {
    setItems((prev) => prev.filter((i) => !(i.type === type && i.id === id)));
  }

  function vider() {
    setItems([]);
  }

  const total = items.reduce((acc, i) => acc + i.prix * i.quantite, 0);
  const count = items.reduce((acc, i) => acc + i.quantite, 0);

  return (
    <Ctx.Provider value={{ items, total, count, ajouter, changerQuantite, retirer, vider }}>{children}</Ctx.Provider>
  );
}

export function useCart(): CartState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useCart hors du provider");
  return ctx;
}
