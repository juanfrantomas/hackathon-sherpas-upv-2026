/**
 * Renders two screenshots side by side, cropped to a region, so differences
 * can be inspected by eye.
 *
 * Usage: node scripts/sidebyside.mjs <a.png> <b.png> <out.png> [x,y,w,h]
 */
import fs from 'node:fs'
import { launch } from './cdp.mjs'

const [aFile, bFile, outFile, rect] = process.argv.slice(2)
const clip = rect ? rect.split(',').map(Number) : null

const page = await launch({ port: 9335, width: 900, height: 600 })

const toDataUrl = (file) => `data:image/png;base64,${fs.readFileSync(file).toString('base64')}`

const result = await page.evaluate(
  `(async () => {
    const load = (src) => new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = reject
      img.src = src
    })
    const [ia, ib] = await Promise.all([load(${JSON.stringify(toDataUrl(aFile))}), load(${JSON.stringify(toDataUrl(bFile))})])
    const clip = ${clip ? JSON.stringify(clip) : 'null'}
    const x = clip ? clip[0] : 0
    const y = clip ? clip[1] : 0
    const w = clip ? clip[2] : Math.min(ia.width, ib.width)
    const h = clip ? clip[3] : Math.min(ia.height, ib.height)
    const canvas = document.createElement('canvas')
    canvas.width = w * 2 + 24
    canvas.height = h + 40
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(ia, x, y, w, h, 0, 40, w, h)
    ctx.drawImage(ib, x, y, w, h, w + 24, 40, w, h)
    ctx.fillStyle = '#111'
    ctx.font = 'bold 15px sans-serif'
    ctx.fillText('ORIGINAL', 8, 24)
    ctx.fillText('MIGRATION', w + 32, 24)
    ctx.strokeStyle = '#e11'
    ctx.lineWidth = 2
    ctx.strokeRect(24.5, 40.5, w - 1, h - 1)
    ctx.strokeRect(w + 24.5, 40.5, w - 1, h - 1)
    return canvas.toDataURL('image/png')
  })()`,
)

fs.writeFileSync(outFile, Buffer.from(result.split(',')[1], 'base64'))
console.log('wrote', outFile)
page.close()
