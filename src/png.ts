const FONT: Record<string, string[]> = {
  '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
  '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
  '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
  '3': ['11110', '00001', '00001', '01110', '00001', '00001', '11110'],
  '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
  '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
  '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
  '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
  '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
  '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
  '.': ['00000', '00000', '00000', '00000', '00000', '01100', '01100'],
  '%': ['11001', '11010', '00010', '00100', '01000', '01011', '10011'],
  '/': ['00001', '00010', '00010', '00100', '01000', '01000', '10000']
}

type RGB = [number, number, number]

class Canvas {
  w: number
  h: number
  px: Uint8Array
  constructor(w: number, h: number, bg: RGB) {
    this.w = w
    this.h = h
    this.px = new Uint8Array(w * h * 3)
    for (let i = 0; i < w * h; i++) this.px.set(bg, i * 3)
  }
  rect(x0: number, y0: number, x1: number, y1: number, c: RGB) {
    const xa = Math.max(0, Math.floor(x0)), xb = Math.min(this.w, Math.ceil(x1))
    const ya = Math.max(0, Math.floor(y0)), yb = Math.min(this.h, Math.ceil(y1))
    for (let y = ya; y < yb; y++) for (let x = xa; x < xb; x++) this.px.set(c, (y * this.w + x) * 3)
  }
  roundRect(x0: number, y0: number, x1: number, y1: number, r: number, c: RGB, fromY = 0) {
    for (let y = Math.max(0, y0, fromY); y < Math.min(this.h, y1); y++) {
      for (let x = Math.max(0, x0); x < Math.min(this.w, x1); x++) {
        const dx = x < x0 + r ? x0 + r - x : x > x1 - r ? x - (x1 - r) : 0
        const dy = y < y0 + r ? y0 + r - y : y > y1 - r ? y - (y1 - r) : 0
        if (dx * dx + dy * dy <= r * r) this.px.set(c, (y * this.w + x) * 3)
      }
    }
  }
  text(s: string, x: number, y: number, scale: number, c: RGB) {
    let cx = x
    for (const ch of s) {
      const g = FONT[ch]
      if (g) for (let r = 0; r < 7; r++) for (let k = 0; k < 5; k++) if (g[r][k] === '1') this.rect(cx + k * scale, y + r * scale, cx + (k + 1) * scale, y + (r + 1) * scale, c)
      cx += 6 * scale
    }
  }
}

function crc32(buf: Uint8Array): number {
  let c = ~0
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i]
    for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xedb88320 : c >>> 1
  }
  return ~c >>> 0
}

function chunk(type: string, data: Uint8Array): Uint8Array {
  const out = new Uint8Array(12 + data.length)
  const dv = new DataView(out.buffer)
  dv.setUint32(0, data.length)
  for (let i = 0; i < 4; i++) out[4 + i] = type.charCodeAt(i)
  out.set(data, 8)
  dv.setUint32(8 + data.length, crc32(out.subarray(4, 8 + data.length)))
  return out
}

async function zlib(data: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([data]).stream().pipeThrough(new CompressionStream('deflate'))
  return new Uint8Array(await new Response(stream).arrayBuffer())
}

async function encode(cv: Canvas): Promise<Uint8Array> {
  const raw = new Uint8Array((cv.w * 3 + 1) * cv.h)
  for (let y = 0; y < cv.h; y++) {
    raw[y * (cv.w * 3 + 1)] = 0
    raw.set(cv.px.subarray(y * cv.w * 3, (y + 1) * cv.w * 3), y * (cv.w * 3 + 1) + 1)
  }
  const ihdr = new Uint8Array(13)
  const dv = new DataView(ihdr.buffer)
  dv.setUint32(0, cv.w)
  dv.setUint32(4, cv.h)
  ihdr.set([8, 2, 0, 0, 0], 8)
  const parts = [new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', await zlib(raw)), chunk('IEND', new Uint8Array())]
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0))
  let o = 0
  for (const p of parts) { out.set(p, o); o += p.length }
  return out
}

export async function progressCard(percent: number, milestones: { ratio: number }[], done: number, total: number): Promise<Uint8Array> {
  const W = 600, H = 315
  const ink: RGB = [43, 30, 18], paper: RGB = [233, 220, 192], gold: RGB = [176, 132, 52], sea: RGB = [38, 92, 104], seaLight: RGB = [86, 146, 150], glass: RGB = [208, 214, 196]
  const cv = new Canvas(W, H, paper)
  cv.rect(10, 10, W - 10, 14, gold)
  cv.rect(10, H - 14, W - 10, H - 10, gold)
  const bx0 = 40, by0 = 70, bx1 = 420, by1 = 250
  cv.roundRect(bx0 - 6, by0 - 6, bx1 + 6, by1 + 6, 60, ink)
  cv.roundRect(bx0, by0, bx1, by1, 56, glass)
  cv.roundRect(bx1 - 4, 128, bx1 + 60, 192, 10, ink)
  cv.roundRect(bx1, 134, bx1 + 54, 186, 8, [150, 104, 60])
  const p = Math.max(0, Math.min(100, percent)) / 100
  const innerTop = by0 + 8, innerBot = by1 - 8
  const sea0 = innerBot - Math.round((innerBot - innerTop) * p)
  if (p > 0) {
    cv.roundRect(bx0, by0, bx1, by1, 56, sea, sea0)
    cv.rect(bx0 + 24, sea0, bx1 - 24, sea0 + 3, seaLight)
  }
  const hullTop = Math.min(innerBot - 30, Math.max(innerTop + 80, sea0 - 10))
  const hx0 = bx0 + 70, hx1 = bx1 - 70
  for (let y = hullTop; y < hullTop + 24; y++) {
    const inset = Math.round(((y - hullTop) / 24) * 22)
    cv.rect(hx0 + inset, y, hx1 - inset, y + 1, [90, 58, 34])
  }
  cv.rect(hx0, hullTop, hx1, hullTop + 3, ink)
  const n = Math.max(1, milestones.length)
  const span = (hx1 - hx0) / n
  milestones.forEach((m, i) => {
    const cx = Math.round(hx0 + span * (i + 0.5))
    cv.rect(cx - 2, hullTop - 78, cx + 2, hullTop, ink)
    const h = Math.round(18 + 52 * m.ratio)
    const w = Math.min(Math.floor(span / 2) - 6, 30)
    cv.rect(cx - w, hullTop - 8 - h, cx + w, hullTop - 8, m.ratio >= 1 ? gold : [244, 236, 214])
    cv.rect(cx - w, hullTop - 8 - h, cx + w, hullTop - 6 - h, ink)
  })
  cv.text(`${percent.toFixed(1)}%`, 40, 24, 5, ink)
  const t = `${done}/${total}`
  cv.text(t, W - 40 - t.length * 30, 24, 5, gold)
  return encode(cv)
}
