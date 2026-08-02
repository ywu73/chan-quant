import { describe, expect, it } from "vitest";

import {
  BOARD_STORAGE_KEY,
  BUILT_IN_BOARDS,
  COMPARISON_MAX_INSTRUMENTS,
  createBoardStore,
  prepareBoardSelection,
} from "./comparisonBoards";


function createMemoryStorage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}


describe("comparison boards", () => {
  it("provides versioned built-in presets with auditable canonical membership", () => {
    expect(COMPARISON_MAX_INSTRUMENTS).toBe(8);
    expect(BUILT_IN_BOARDS[0]).toEqual(
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
        instruments: [
          { symbol: "000001.SH", name: "上证指数", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "399001.SZ", name: "深证成指", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "399006.SZ", name: "创业板指", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "000300.SH", name: "沪深300", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "000905.SH", name: "中证500", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "000852.SH", name: "中证1000", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "000688.SH", name: "科创50", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
          { symbol: "000016.SH", name: "上证50", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2 },
        ],
      },
    );

    expect(BUILT_IN_BOARDS.slice(1).map((board) => ({
      id: board.id,
      name: board.name,
      version: board.version,
      confirmed_at: board.confirmed_at,
      identity_source: board.identity_source,
      membership_evidence: board.membership_evidence,
      instruments: board.instruments.map(({ symbol, name, exchange, asset_type, price_precision }) => ({
        symbol,
        name,
        exchange,
        asset_type,
        price_precision,
      })),
    }))).toEqual([
      {
        id: "csi-399997-top8",
        name: "中证白酒前 8 权重",
        version: "2026-07-31",
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
    ]);

    for (const board of BUILT_IN_BOARDS) {
      expect(board.instruments).toHaveLength(8);
      expect(new Set(board.instruments.map((instrument) => instrument.symbol)).size).toBe(8);
    }
  });

  it("isolates malformed storage and exposes a recoverable issue", () => {
    const storage = createMemoryStorage({ [BOARD_STORAGE_KEY]: "{" });
    const store = createBoardStore(storage, () => "unused");

    const result = store.load();

    expect(result).toEqual({
      boards: [],
      issue: {
        code: "CORRUPTED_STORAGE",
        message: "自定义板块存储已损坏，已隔离且未加载。可清除后重新保存。",
      },
    });
    expect(() => store.save("不能覆盖", BUILT_IN_BOARDS[0].instruments.slice(0, 2)))
      .toThrow("自定义板块存储已损坏，请先清除后再保存");
    expect(storage.getItem(BOARD_STORAGE_KEY)).toBe("{");
  });

  it("keeps valid v1 boards while rejecting unknown stored versions", () => {
    const storage = createMemoryStorage({
      [BOARD_STORAGE_KEY]: JSON.stringify([
        {
          version: 1,
          id: "valid-board",
          name: "有效板块",
          instruments: BUILT_IN_BOARDS[0].instruments.slice(0, 2),
        },
        {
          version: 2,
          id: "future-board",
          name: "未来版本",
          instruments: BUILT_IN_BOARDS[0].instruments.slice(0, 2),
        },
      ]),
    });

    const result = createBoardStore(storage, () => "unused").load();

    expect(result.boards.map((board) => board.id)).toEqual(["valid-board"]);
    expect(result.issue?.code).toBe("UNSUPPORTED_VERSION");
  });

  it("preserves unknown-version records when saving a new v1 board", () => {
    const futureBoard = {
      version: 2,
      id: "future-board",
      name: "未来版本",
      instruments: BUILT_IN_BOARDS[0].instruments.slice(0, 2),
      future_field: "must survive",
    };
    const storage = createMemoryStorage({
      [BOARD_STORAGE_KEY]: JSON.stringify([futureBoard]),
    });
    const store = createBoardStore(storage, () => "new-board");

    store.save("新板块", BUILT_IN_BOARDS[0].instruments.slice(0, 2));

    expect(JSON.parse(storage.getItem(BOARD_STORAGE_KEY) ?? "[]")[0]).toEqual(futureBoard);
    expect(store.load().boards.map((board) => board.id)).toEqual(["new-board"]);
    expect(store.load().issue?.code).toBe("UNSUPPORTED_VERSION");
  });

  it("saves a trimmed board with full canonical identities and removes duplicate symbols", () => {
    const storage = createMemoryStorage();
    const store = createBoardStore(storage, () => "board-1");
    const first = BUILT_IN_BOARDS[0].instruments[0];
    const second = BUILT_IN_BOARDS[0].instruments[1];

    const saved = store.save("  我的宽基  ", [
      first,
      { ...first, symbol: "000001.sh" },
      second,
    ]);

    expect(saved).toEqual({
      version: 1,
      id: "board-1",
      name: "我的宽基",
      instruments: [first, second],
    });
    expect(store.load()).toEqual({ boards: [saved], issue: null });
  });

  it("deletes one custom board without affecting the others", () => {
    const storage = createMemoryStorage();
    const ids = ["board-1", "board-2"];
    const store = createBoardStore(storage, () => ids.shift() ?? "unexpected");
    const instruments = BUILT_IN_BOARDS[0].instruments.slice(0, 2);
    store.save("第一组", instruments);
    store.save("第二组", instruments);

    store.remove("board-1");

    expect(store.load().boards.map((board) => board.id)).toEqual(["board-2"]);
  });

  it("clears isolated storage so the user can recover from corruption", () => {
    const storage = createMemoryStorage({ [BOARD_STORAGE_KEY]: "not-json" });
    const store = createBoardStore(storage, () => "unused");
    expect(store.load().issue?.code).toBe("CORRUPTED_STORAGE");

    store.clear();

    expect(store.load()).toEqual({ boards: [], issue: null });
  });

  it("prepares a board load by deduplicating and rejects more than eight members", () => {
    const members = BUILT_IN_BOARDS[0].instruments;
    expect(prepareBoardSelection([members[0], members[0], members[1]])).toEqual([
      members[0],
      members[1],
    ]);
    expect(() => prepareBoardSelection([
      ...members,
      { symbol: "100001.SZ", name: "测试标的", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2 },
    ])).toThrow("板块必须包含 2–8 个不同的规范标的");
  });

  it("loads only the first board when stored ids are duplicated", () => {
    const duplicate = {
      version: 1,
      id: "same-id",
      name: "重复 ID",
      instruments: BUILT_IN_BOARDS[0].instruments.slice(0, 2),
    };
    const storage = createMemoryStorage({
      [BOARD_STORAGE_KEY]: JSON.stringify([duplicate, { ...duplicate, name: "后出现" }]),
    });

    const result = createBoardStore(storage, () => "unused").load();

    expect(result.boards.map((board) => board.name)).toEqual(["重复 ID"]);
    expect(result.issue?.code).toBe("INVALID_ENTRIES");
  });
});
