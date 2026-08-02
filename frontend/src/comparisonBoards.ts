import type { InstrumentIdentity } from "./types/instrument";
import { CN_BROAD_INDEX_CATALOG } from "./marketInstruments";


export const COMPARISON_MIN_INSTRUMENTS = 2;
export const COMPARISON_MAX_INSTRUMENTS = 8;
export const BOARD_STORAGE_KEY = "chan-quant.comparison-boards.v1";

export type BoardInstrument = Pick<
  InstrumentIdentity,
  "symbol" | "name" | "exchange" | "asset_type" | "price_precision"
>;

export interface SourceArtifact {
  url: string;
  sha256: string;
}

export interface CsiConstituentEvidence {
  rank: number;
  symbol: string;
  weight_percent: number;
  precise_weight_percent: number;
}

export type BuiltInBoardMembershipEvidence =
  | {
      source: "verified-identity-catalog";
      source_as_of: string;
      selection_rule: "FULL_VERIFIED_SET";
    }
  | {
      source: "csi-official-index";
      source_as_of: string;
      fetched_at: string;
      selection_rule: "TOP_8_BY_OFFICIAL_PRECISE_WEIGHT";
      index_code: string;
      index_name: string;
      weight_source: SourceArtifact;
      constituent_source: SourceArtifact;
      factsheet_source: SourceArtifact & { as_of: string };
      constituents: CsiConstituentEvidence[];
    };

export interface BuiltInBoard {
  id: string;
  name: string;
  version: string;
  description: string;
  confirmed_at: string;
  identity_source: "sina-undocumented-suggest";
  membership_evidence: BuiltInBoardMembershipEvidence;
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
    membership_evidence: {
      source: "verified-identity-catalog",
      source_as_of: "2026-08-01",
      selection_rule: "FULL_VERIFIED_SET",
    },
    instruments: CN_BROAD_INDEX_CATALOG.map(({
      symbol,
      name,
      exchange,
      asset_type,
      price_precision,
    }) => ({ symbol, name, exchange, asset_type, price_precision })),
  },
  {
    id: "csi-399997-top8",
    name: "中证白酒前 8 权重",
    version: "2026-07-31",
    description: "中证白酒指数（399997）官方权重表前 8 名；不是完整指数成分，也不代表官方指数或加权组合。",
    confirmed_at: "2026-08-02",
    identity_source: "sina-undocumented-suggest",
    membership_evidence: {
      source: "csi-official-index",
      source_as_of: "2026-07-31",
      fetched_at: "2026-08-02",
      selection_rule: "TOP_8_BY_OFFICIAL_PRECISE_WEIGHT",
      index_code: "399997",
      index_name: "中证白酒指数",
      weight_source: {
        url: "https://www.csindex.com.cn/csindex-home/index/weight/top10new/399997",
        sha256: "c8d1d32d1dfef27aa40d5a0f6d897a3365eda65d0060953b8600d06600cc6eae",
      },
      constituent_source: {
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/399997cons.xls",
        sha256: "e3a0af78260d22b3c8a123a01b3b7c587fcc0843a8af69e97866a81f1d64d5e5",
      },
      factsheet_source: {
        as_of: "2026-06-30",
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399997factsheet.pdf",
        sha256: "84f286a91fc71d55fb591ef9e9cb666eb91217319e231184bdd50d990bc15bf1",
      },
      constituents: [
        { rank: 1, symbol: "600809.SH", weight_percent: 15.43, precise_weight_percent: 15.428831090540676 },
        { rank: 2, symbol: "000568.SZ", weight_percent: 15.38, precise_weight_percent: 15.38236913472435 },
        { rank: 3, symbol: "600519.SH", weight_percent: 15.3, precise_weight_percent: 15.29708689472685 },
        { rank: 4, symbol: "000858.SZ", weight_percent: 13.95, precise_weight_percent: 13.954126614443497 },
        { rank: 5, symbol: "002304.SZ", weight_percent: 8, precise_weight_percent: 8.004741385532334 },
        { rank: 6, symbol: "603369.SH", weight_percent: 6.65, precise_weight_percent: 6.6482397629260195 },
        { rank: 7, symbol: "000596.SZ", weight_percent: 4.81, precise_weight_percent: 4.805405517638467 },
        { rank: 8, symbol: "000799.SZ", weight_percent: 2.95, precise_weight_percent: 2.9475329560757344 },
      ],
    },
    instruments: [
      { symbol: "600809.SH", name: "山西汾酒", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "000568.SZ", name: "泸州老窖", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "600519.SH", name: "贵州茅台", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "000858.SZ", name: "五粮液", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "002304.SZ", name: "洋河股份", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "603369.SH", name: "今世缘", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "000596.SZ", name: "古井贡酒", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "000799.SZ", name: "酒鬼酒", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
    ],
  },
  {
    id: "csi-931152-top8",
    name: "中证创新药前 8 权重",
    version: "2026-07-31",
    description: "中证创新药产业指数（931152）官方权重表前 8 名；不是完整指数成分，也不代表官方指数或加权组合。",
    confirmed_at: "2026-08-02",
    identity_source: "sina-undocumented-suggest",
    membership_evidence: {
      source: "csi-official-index",
      source_as_of: "2026-07-31",
      fetched_at: "2026-08-02",
      selection_rule: "TOP_8_BY_OFFICIAL_PRECISE_WEIGHT",
      index_code: "931152",
      index_name: "中证创新药产业指数",
      weight_source: {
        url: "https://www.csindex.com.cn/csindex-home/index/weight/top10new/931152",
        sha256: "bb4a359abbb9c18a393792d854f474553aaca3a8f78afb97113f9ed72496dd61",
      },
      constituent_source: {
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/931152cons.xls",
        sha256: "8830b56ee5b1397c522b53101a5e207ace4b5e070d6a5531420d2bb043b0478f",
      },
      factsheet_source: {
        as_of: "2026-06-30",
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931152factsheet.pdf",
        sha256: "cd00f1b524e288ac3e74fa8eac1e81f4e639755401bc36d597ac84c42f72e5f6",
      },
      constituents: [
        { rank: 1, symbol: "603259.SH", weight_percent: 11.24, precise_weight_percent: 11.241136772544513 },
        { rank: 2, symbol: "600276.SH", weight_percent: 9.89, precise_weight_percent: 9.891465119037061 },
        { rank: 3, symbol: "002422.SZ", weight_percent: 4.82, precise_weight_percent: 4.820611784114802 },
        { rank: 4, symbol: "300759.SZ", weight_percent: 3.79, precise_weight_percent: 3.792452008251634 },
        { rank: 5, symbol: "002821.SZ", weight_percent: 3.04, precise_weight_percent: 3.039827265679091 },
        { rank: 6, symbol: "688578.SH", weight_percent: 2.99, precise_weight_percent: 2.9920744852411514 },
        { rank: 7, symbol: "688235.SH", weight_percent: 2.95, precise_weight_percent: 2.947324374166006 },
        { rank: 8, symbol: "600196.SH", weight_percent: 2.94, precise_weight_percent: 2.942594961143083 },
      ],
    },
    instruments: [
      { symbol: "603259.SH", name: "药明康德", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "600276.SH", name: "恒瑞医药", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "002422.SZ", name: "科伦药业", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "300759.SZ", name: "康龙化成", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "002821.SZ", name: "凯莱英", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688578.SH", name: "艾力斯", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688235.SH", name: "百济神州", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "600196.SH", name: "复星医药", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
    ],
  },
  {
    id: "csi-931743-top8",
    name: "半导体材料设备前 8 权重",
    version: "2026-07-31",
    description: "中证半导体材料设备主题指数（931743）官方权重表前 8 名；不是完整指数成分，也不代表官方指数或加权组合。",
    confirmed_at: "2026-08-02",
    identity_source: "sina-undocumented-suggest",
    membership_evidence: {
      source: "csi-official-index",
      source_as_of: "2026-07-31",
      fetched_at: "2026-08-02",
      selection_rule: "TOP_8_BY_OFFICIAL_PRECISE_WEIGHT",
      index_code: "931743",
      index_name: "中证半导体材料设备主题指数",
      weight_source: {
        url: "https://www.csindex.com.cn/csindex-home/index/weight/top10new/931743",
        sha256: "61b90eb34b4e37fa443984b928596b12fcb964a82aeccf3ccd8deeec63b37e53",
      },
      constituent_source: {
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/931743cons.xls",
        sha256: "cd68c61e0b6cba76640ae8f76d6db1dbb1005070821f54966783d899648901c2",
      },
      factsheet_source: {
        as_of: "2026-06-30",
        url: "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931743factsheet.pdf",
        sha256: "65e1e7929741ef82a99a7492d7c4773afeb3e16412c350d50918806625dac21a",
      },
      constituents: [
        { rank: 1, symbol: "688012.SH", weight_percent: 16.28, precise_weight_percent: 16.282013156459556 },
        { rank: 2, symbol: "002371.SZ", weight_percent: 15.27, precise_weight_percent: 15.266593013085771 },
        { rank: 3, symbol: "688072.SH", weight_percent: 8.31, precise_weight_percent: 8.308981004312631 },
        { rank: 4, symbol: "300604.SZ", weight_percent: 7.28, precise_weight_percent: 7.280784196392078 },
        { rank: 5, symbol: "688120.SH", weight_percent: 6.42, precise_weight_percent: 6.422308289832428 },
        { rank: 6, symbol: "688361.SH", weight_percent: 5.36, precise_weight_percent: 5.3645061576800135 },
        { rank: 7, symbol: "688200.SH", weight_percent: 3.17, precise_weight_percent: 3.1709554187218467 },
        { rank: 8, symbol: "688037.SH", weight_percent: 2.99, precise_weight_percent: 2.988252020019651 },
      ],
    },
    instruments: [
      { symbol: "688012.SH", name: "中微公司", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "002371.SZ", name: "北方华创", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688072.SH", name: "拓荆科技", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "300604.SZ", name: "长川科技", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688120.SH", name: "华海清科", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688361.SH", name: "中科飞测", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688200.SH", name: "华峰测控", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
      { symbol: "688037.SH", name: "芯源微", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
    ],
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
