/**
 * Compares the original prototype's screenshots with the migrated app's.
 *
 * Uses the browser's own canvas to decode and diff the PNGs, so no image
 * library is needed.
 *
 * Usage: node scripts/compare.mjs <originalDir> <migrationDir> [outputDir]
 */
import fs from 'node:fs'
import path from 'node:path'
import { launch } from './cdp.mjs'

const originalDir = process.argv[2]
const migrationDir = process.argv[3]
const outDir = process.argv[4] ?? null
if (!originalDir || !migrationDir) {
  console.error('usage: node scripts/compare.mjs <originalDir> <migrationDir> [outputDir]')
  process.exit(1)
}

const TOLERANCE = 8

const page = await launch({ port: 9334, width: 800, height: 600 })

const diff = async (aBuf, bBuf) => {
  const a = `data:image/png;base64,${aBuf.toString('base64')}`
  const b = `data:image/png;base64,${bBuf.toString('base64')}`
  return page.evaluate(
    `(async () => {
      const load = (src) => new Promise((resolve, reject) => {
        const img = new Image()
        img.onload = () => resolve(img)
        img.onerror = reject
        img.src = src
      })
      const [ia, ib] = await Promise.all([load(${JSON.stringify(a)}), load(${JSON.stringify(b)})])
      if (ia.width !== ib.width || ia.height !== ib.height) {
        return { sizeMismatch: [ia.width, ia.height, ib.width, ib.height] }
      }
      const w = ia.width, h = ia.height
      const read = (img) => {
        const canvas = document.createElement('canvas')
        canvas.width = w; canvas.height = h
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0)
        return ctx.getImageData(0, 0, w, h).data
      }
      const da = read(ia), db = read(ib)
      const out = document.createElement('canvas')
      out.width = w; out.height = h
      const octx = out.getContext('2d')
      const od = octx.createImageData(w, h)
      const rows = new Array(h).fill(0)
      let differing = 0, maxDelta = 0
      for (let i = 0; i < w * h; i++) {
        const o = i * 4
        const d = Math.max(
          Math.abs(da[o] - db[o]),
          Math.abs(da[o + 1] - db[o + 1]),
          Math.abs(da[o + 2] - db[o + 2]),
        )
        if (d > ${TOLERANCE}) {
          differing++
          rows[Math.floor(i / w)]++
          od[o] = 255; od[o + 1] = 0; od[o + 2] = 0; od[o + 3] = 255
        } else {
          od[o] = da[o]; od[o + 1] = da[o + 1]; od[o + 2] = da[o + 2]; od[o + 3] = 40
        }
        if (d > maxDelta) maxDelta = d
      }
      octx.putImageData(od, 0, 0)
      const top = rows
        .map((count, y) => ({ y, count }))
        .filter((entry) => entry.count > 0)
        .sort((x, y) => y.count - x.count)
        .slice(0, 8)
      return {
        differing,
        total: w * h,
        pct: (differing / (w * h)) * 100,
        maxDelta,
        topRows: top,
        diff: out.toDataURL('image/png'),
      }
    })()`,
  )
}

const names = fs
  .readdirSync(originalDir)
  .filter((file) => file.endsWith('.png'))
  .sort()

let worst = 0
for (const name of names) {
  const migrationFile = path.join(migrationDir, name)
  if (!fs.existsSync(migrationFile)) {
    console.log(`${name.padEnd(26)} MISSING in migration`)
    continue
  }
  const result = await diff(
    fs.readFileSync(path.join(originalDir, name)),
    fs.readFileSync(migrationFile),
  )
  if (result.sizeMismatch) {
    console.log(`${name.padEnd(26)} SIZE MISMATCH ${result.sizeMismatch.join(' vs ')}`)
    worst = 100
    continue
  }
  worst = Math.max(worst, result.pct)
  const status = result.pct < 0.05 ? 'OK  ' : result.pct < 1 ? 'warn' : 'FAIL'
  console.log(
    `${name.padEnd(26)} ${status} ${result.pct.toFixed(3)}%  ` +
      `(${result.differing}/${result.total} px, maxΔ ${result.maxDelta})` +
      (result.topRows.length ? `  rows ${result.topRows.map((r) => r.y).join(',')}` : ''),
  )
  if (outDir && result.pct >= 0.05) {
    fs.mkdirSync(outDir, { recursive: true })
    fs.writeFileSync(
      path.join(outDir, name.replace(/\.png$/, '.diff.png')),
      Buffer.from(result.diff.split(',')[1], 'base64'),
    )
  }
}

console.log(`\nworst screen: ${worst.toFixed(3)}% differing pixels`)
page.close()
