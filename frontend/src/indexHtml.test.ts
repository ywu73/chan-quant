import { describe, expect, it } from "vitest"
import indexHtml from "../index.html?raw"

describe("frontend identity contract", () => {
  it("keeps the stable Chan Quant application marker in the source document", () => {
    expect(indexHtml).toContain('<meta name="chan-quant-app" content="frontend-v1" />')
  })
})
