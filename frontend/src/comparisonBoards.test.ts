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
  it("provides one versioned broad-index preset with eight verified canonical identities", () => {
    expect(COMPARISON_MAX_INSTRUMENTS).toBe(8);
    expect(BUILT_IN_BOARDS).toEqual([
      {
        id: "cn-broad-indices",
        name: "宽基指数",
        version: "2026-08-01",
        description: "覆盖沪深主要宽基与代表性指数；成员代码和名称于 2026-08-01 通过现有证券搜索适配器逐项确认。",
        confirmed_at: "2026-08-01",
        instruments: [
          { symbol: "000001.SH", name: "上证指数", exchange: "SH", asset_type: "UNKNOWN" },
          { symbol: "399001.SZ", name: "深证成指", exchange: "SZ", asset_type: "UNKNOWN" },
          { symbol: "399006.SZ", name: "创业板指", exchange: "SZ", asset_type: "UNKNOWN" },
          { symbol: "000300.SH", name: "沪深300", exchange: "SH", asset_type: "UNKNOWN" },
          { symbol: "000905.SH", name: "中证500", exchange: "SH", asset_type: "UNKNOWN" },
          { symbol: "000852.SH", name: "中证1000", exchange: "SH", asset_type: "UNKNOWN" },
          { symbol: "000688.SH", name: "科创50", exchange: "SH", asset_type: "UNKNOWN" },
          { symbol: "000016.SH", name: "上证50", exchange: "SH", asset_type: "UNKNOWN" },
        ],
      },
    ]);
  });

  it("isolates malformed storage and exposes a recoverable issue", () => {
    const storage = createMemoryStorage({ [BOARD_STORAGE_KEY]: "{" });

    const result = createBoardStore(storage, () => "unused").load();

    expect(result).toEqual({
      boards: [],
      issue: {
        code: "CORRUPTED_STORAGE",
        message: "自定义板块存储已损坏，已隔离且未加载。可清除后重新保存。",
      },
    });
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
      { symbol: "100001.SZ", name: "测试标的", exchange: "SZ", asset_type: "UNKNOWN" },
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
