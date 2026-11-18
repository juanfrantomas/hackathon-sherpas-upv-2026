/**
 * Captures the prototype's screens so they can be compared with the original.
 *
 * Usage: node scripts/capture.mjs <url> <outputDir> [label]
 */
import fs from 'node:fs'
import path from 'node:path'
import { launch, sleep } from './cdp.mjs'

const url = process.argv[2]
const outDir = process.argv[3]
const label = process.argv[4] ?? 'capture'
if (!url || !outDir) {
  console.error('usage: node scripts/capture.mjs <url> <outputDir> [label]')
  process.exit(1)
}
fs.mkdirSync(outDir, { recursive: true })

const page = await launch({ port: 9333 })
const errors = []

await page.goto(url)
await sleep(700)

const shot = async (name) => {
  const buffer = await page.screenshot()
  fs.writeFileSync(path.join(outDir, `${name}.png`), buffer)
  console.log(`  ${label}/${name}.png`)
}

const clickText = async (selector, text) => {
  const found = await page.evaluate(
    `(() => {
      const el = [...document.querySelectorAll(${JSON.stringify(selector)})]
        .find((node) => node.textContent.trim() === ${JSON.stringify(text)})
      if (!el) return false
      el.click()
      return true
    })()`,
  )
  if (!found) console.warn(`  ! could not find ${selector} "${text}"`)
  await sleep(450)
}

const clickJourney = async (labelText) => {
  const found = await page.evaluate(
    `(() => {
      const el = [...document.querySelectorAll('.flow ol li button')]
        .find((node) => node.textContent.trim().includes(${JSON.stringify(labelText)}))
      if (!el) return false
      el.click()
      return true
    })()`,
  )
  if (!found) console.warn(`  ! could not find journey step "${labelText}"`)
  await sleep(550)
}

console.log(`capturing ${label} from ${url}`)
await shot('01-welcome')

await clickText('.proto-bar .seg button', 'Design system')
await shot('02-design-system')
await clickText('.proto-bar .seg button', 'Family app')

await clickJourney('Home dashboard')
await shot('03-home')

await clickJourney('Financial story')
await sleep(300)
// Freeze the story on chapter 2 so both apps are captured at the same point.
await page.evaluate(
  `(() => {
    const bars = document.querySelectorAll('.player__progress .seg-bar')
    if (bars[1]) bars[1].click()
    const frame = document.querySelector('.player__frame')
    if (frame) frame.click()
  })()`,
)
await sleep(350)
await shot('04-story')

await clickJourney('My financial plan')
await shot('05-plan')

await clickJourney('Goals & milestones')
await shot('06-milestones')

await clickJourney('Progress overview')
await shot('07-journey')

await clickJourney('Check-in')
await shot('08-checkin')

await clickJourney('AI mentor')
await shot('09-mentor')

const voiceState = async (name) => {
  const found = await page.evaluate(
    `(() => {
      const el = [...document.querySelectorAll('.state-grid button')]
        .find((node) => node.textContent.trim() === ${JSON.stringify(name)})
      if (!el) return false
      el.click()
      return true
    })()`,
  )
  if (!found) console.warn(`  ! could not find voice state "${name}"`)
  await sleep(500)
}
await voiceState('Speaking')
await shot('10-mentor-speaking')

await page.setViewport(1100, 900)
await sleep(300)
await shot('11-responsive-1100')
await page.setViewport(760, 900)
await sleep(300)
await shot('12-responsive-760')

if (errors.length) console.warn('page errors:', errors)
page.close()
