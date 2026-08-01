import { useCallback, useEffect, useRef, useState } from "react";

import {
  createBoardStore,
  type BoardInstrument,
  type BoardStorageIssue,
  type StoredBoardV1,
} from "./comparisonBoards";


function createBoardId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `board-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}


export function useComparisonBoards() {
  const [customBoards, setCustomBoards] = useState<StoredBoardV1[]>([]);
  const [storageIssue, setStorageIssue] = useState<BoardStorageIssue | null>(null);
  const storeRef = useRef<ReturnType<typeof createBoardStore> | null>(null);

  const refresh = useCallback(() => {
    const store = storeRef.current;
    if (store === null) return;
    const result = store.load();
    setCustomBoards(result.boards);
    setStorageIssue(result.issue);
  }, []);

  useEffect(() => {
    try {
      storeRef.current = createBoardStore(window.localStorage, createBoardId);
      refresh();
    } catch {
      setCustomBoards([]);
      setStorageIssue({
        code: "STORAGE_UNAVAILABLE",
        message: "当前浏览器不允许访问本地存储，自定义板块不可用。",
      });
    }
    return () => {
      storeRef.current = null;
    };
  }, [refresh]);

  return {
    customBoards,
    storageIssue,
    save(name: string, instruments: BoardInstrument[]): StoredBoardV1 {
      const store = storeRef.current;
      if (store === null) throw new Error("浏览器本地存储不可用");
      const saved = store.save(name, instruments);
      refresh();
      return saved;
    },
    remove(id: string): void {
      const store = storeRef.current;
      if (store === null) throw new Error("浏览器本地存储不可用");
      store.remove(id);
      refresh();
    },
    clear(): void {
      const store = storeRef.current;
      if (store === null) throw new Error("浏览器本地存储不可用");
      store.clear();
      refresh();
    },
  };
}
