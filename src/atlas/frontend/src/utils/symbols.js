// src/atlas/frontend/src/utils/symbols.js
// Catálogo único de símbolos. MT5 usa sufijo 'z'.
// Universo ventanas: todos los EUR* y USD*, excluyendo BTC.

export const GAP_SYMBOLS = ["XAUUSDz"];

// Lista base (podés agregar/quitar sin romper nada).
// Nota: acá meto los principales majors + cruces EUR más comunes.
// Si tu broker tiene más, los agregás al final y listo.
export const FOREX_SYMBOLS = [
  // EUR*
  "EURUSDz",
  "EURJPYz",
  "EURAUDz",
  "EURCADz",
  "EURCHFz",
  "EURGBpz",
  "EURNZDz",

  // USD*
  "USDJPYz",
  "USDCADz",
  "USDCHFz",
  "USDAUDz",
  "USDNZDz",
  "USDSEKz",
  "USDNOKz",
  "USDMXNz",
];

export function symbolsForWorld(world) {
  switch (world) {
    case "GAP":
      return GAP_SYMBOLS;
    case "PRESESION":
    case "GATILLO":
    case "ATLAS_IA":
    case "BITACORA":
      return FOREX_SYMBOLS;
    default:
      return FOREX_SYMBOLS;
  }
}

// Símbolo por defecto por mundo
export function defaultSymbolForWorld(world) {
  const list = symbolsForWorld(world);
  return list[0] || "EURUSDz";
}
