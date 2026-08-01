import type { InstrumentIdentity } from "./types/instrument";
import { CN_BROAD_INDEX_CATALOG } from "./marketInstruments";


export const COMPARISON_MIN_INSTRUMENTS = 2;
export const COMPARISON_MAX_INSTRUMENTS = 8;
export const BOARD_STORAGE_KEY = "chan-quant.comparison-boards.v1";

export type BoardInstrument = Pick<
  InstrumentIdentity,
  "symbol" | "name" | "exchange" | "asset_type" | "price_precision"
>;

export interface BuiltInBoard {
  id: string;
  name: string;
  version: string;
  description: string;
  confirmed_at: string;
  identity_source: "sina-undocumented-suggest";
  instruments: BoardInstrument[];
}

export interface StoredBoardV1 {
  version: 1;
  id: string;
  name: string;
  instruments: BoardInstrument[];
}

export interface BoardStorageIssue {
  code: "CORRUPTED_STORAGE" | "UNSUPPORTED_VERSION" | "INVALID_ENTRIES" | "STORAGE_UNAVAILABLE";
  message: string;
}

export interface LoadBoardsResult {
  boards: StoredBoardV1[];
  issue: BoardStorageIssue | null;
}

interface BoardStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): unknown;
  removeItem(key: string): unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeInstrument(value: unknown): BoardInstrument | null {
  if (!isRecord(value)) return null;
  const symbol = typeof value.symbol === "string" ? value.symbol.trim().toUpperCase() : "";
  const name = typeof value.name === "string" ? value.name.trim() : "";
  const exchange = value.exchange;
  const assetType = value.asset_type;
  const pricePrecision = value.price_precision;
  if (!/^\d{6}\.(SZ|SH)$/.test(symbol) || !name) return null;
  if (exchange !== "SZ" && exchange !== "SH") return null;
  if (!symbol.endsWith(`.${exchange}`)) return null;
  if (assetType !== "ETF" && assetType !== "UNKNOWN") return null;
  if (!Number.isInteger(pricePrecision) || Number(pricePrecision) < 0 || Number(pricePrecision) > 6) {
    return null;
  }
  return {
    symbol,
    name,
    exchange,
    asset_type: assetType,
    price_precision: Number(pricePrecision),
  };
}

function normalizeInstruments(value: unknown): BoardInstrument[] | null {
  if (!Array.isArray(value)) return null;
  const instruments: BoardInstrument[] = [];
  const seen = new Set<string>();
  for (const candidate of value) {
    const instrument = normalizeInstrument(candidate);
    if (instrument === null) return null;
    if (seen.has(instrument.symbol)) continue;
    seen.add(instrument.symbol);
    instruments.push(instrument);
  }
  if (
    instruments.length < COMPARISON_MIN_INSTRUMENTS ||
    instruments.length > COMPARISON_MAX_INSTRUMENTS
  ) return null;
  return instruments;
}

export function prepareBoardSelection(instruments: BoardInstrument[]): BoardInstrument[] {
  const normalized = normalizeInstruments(instruments);
  if (normalized === null) throw new Error("板块必须包含 2–8 个不同的规范标的");
  return normalized;
}

function normalizeStoredBoard(value: unknown): StoredBoardV1 | null {
  if (!isRecord(value) || value.version !== 1) return null;
  const id = typeof value.id === "string" ? value.id.trim() : "";
  const name = typeof value.name === "string" ? value.name.trim() : "";
  const instruments = normalizeInstruments(value.instruments);
  if (!id || !name || instruments === null) return null;
  return { version: 1, id, name, instruments };
}

export const BUILT_IN_BOARDS: BuiltInBoard[] = [
  {
    id: "cn-broad-indices",
    name: "宽基指数",
    version: "2026-08-01",
    description: "覆盖沪深主要宽基与代表性指数；成员代码和名称于 2026-08-01 通过现有证券搜索适配器逐项确认。",
    confirmed_at: "2026-08-01",
    identity_source: "sina-undocumented-suggest",
    instruments: CN_BROAD_INDEX_CATALOG.map(({
      symbol,
      name,
      exchange,
      asset_type,
      price_precision,
    }) => ({ symbol, name, exchange, asset_type, price_precision })),
  },
];


export function createBoardStore(storage: BoardStorage, createId: () => string) {
  const readStoredValues = (): unknown[] => {
    const raw = storage.getItem(BOARD_STORAGE_KEY);
    if (raw === null) return [];
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) throw new TypeError("stored boards must be an array");
    return value;
  };

  const readStoredValuesForWrite = (): unknown[] => {
    try {
      return readStoredValues();
    } catch {
      throw new Error("自定义板块存储已损坏，请先清除后再保存");
    }
  };

  const load = (): LoadBoardsResult => {
    try {
      const value = readStoredValues();
      const boards: StoredBoardV1[] = [];
      const seenIds = new Set<string>();
      let hasUnsupportedVersion = false;
      let hasInvalidEntries = false;
      for (const candidate of value) {
        if (isRecord(candidate) && candidate.version !== 1) {
          hasUnsupportedVersion = true;
          continue;
        }
        const board = normalizeStoredBoard(candidate);
        if (board === null || seenIds.has(board.id)) {
          hasInvalidEntries = true;
          continue;
        }
        seenIds.add(board.id);
        boards.push(board);
      }
      if (hasUnsupportedVersion) {
        return {
          boards,
          issue: {
            code: "UNSUPPORTED_VERSION",
            message: "部分自定义板块来自未知版本，已跳过；其余有效板块仍可使用。",
          },
        };
      }
      if (hasInvalidEntries) {
        return {
          boards,
          issue: {
            code: "INVALID_ENTRIES",
            message: "部分自定义板块身份或数量无效，已跳过；其余有效板块仍可使用。",
          },
        };
      }
      return { boards, issue: null };
    } catch {
      return {
        boards: [],
        issue: {
          code: "CORRUPTED_STORAGE",
          message: "自定义板块存储已损坏，已隔离且未加载。可清除后重新保存。",
        },
      };
    }
  };

  return {
    load,
    save(nameValue: string, instrumentValues: BoardInstrument[]): StoredBoardV1 {
      const name = nameValue.trim();
      const instruments = normalizeInstruments(instrumentValues);
      if (!name) throw new Error("板块名称不能为空");
      if (instruments === null) throw new Error("自定义板块必须包含 2–8 个不同的规范标的");
      const current = readStoredValuesForWrite();
      const board: StoredBoardV1 = {
        version: 1,
        id: createId(),
        name,
        instruments,
      };
      storage.setItem(BOARD_STORAGE_KEY, JSON.stringify([...current, board]));
      return board;
    },
    remove(id: string): void {
      const remaining = readStoredValuesForWrite().filter((candidate) => (
        !isRecord(candidate) || candidate.version !== 1 || candidate.id !== id
      ));
      storage.setItem(BOARD_STORAGE_KEY, JSON.stringify(remaining));
    },
    clear(): void {
      storage.removeItem(BOARD_STORAGE_KEY);
    },
  };
}
