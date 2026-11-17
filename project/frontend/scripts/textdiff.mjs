/**
 * Compares the visible text of the original prototype with the migrated app,
 * screen by screen. Catches copy differences that a pixel diff can miss.
 *
 * Usage: node scripts/textdiff.mjs <originalUrl> <migrationUrl>
 */
import { launch, sleep } from './cdp.mjs'

const [originalUrl, migrationUrl] = process.argv.slice(2)
if (!originalUrl || !migrationUrl) {
  console.error('usage: node scripts/textdiff.mjs <originalUrl> <migrationUrl>')
  process.exit(1)
}

const STEPS = [
  { name: 'welcome', go: null },
  { name: 'home', journey: 'Home dashboard' },
  { name: 'story', journey: 'Financial story' },
  { name: 'plan', journey: 'My financial plan' },
  { name: 'milestones', journey: 'Goals & milestones' },
  { name: 'journey', journey: 'Progress overview' },
  { name: 'checkin', journey: 'Check-in' },
  { name: 'mentor', journey: 'AI mentor' },
]

async function dump(url, port) {
  const page = await launch({ port })
  await page.goto(url)
  await sleep(600)
  const result = {}
  for (const step of STEPS) {
    if (step.journey) {
      await page.evaluate(
        `(() => {
          const el = [...document.querySelectorAll('.flow ol li button')]
            .find((node) => node.textContent.trim().includes(${JSON.stringify(step.journey)}))
          if (el) el.click()
        })()`,
      )
      await sleep(500)
    }
    result[step.name] = await page.evaluate(
      `document.body.innerText.replace(/\\r/g, '').split('\\n').map((l) => l.trim()).filter(Boolean).join('\\n')`,
    )
  }
  // Design system page
  await page.evaluate(
    `(() => {
      const el = [...document.querySelectorAll('.proto-bar .seg button')]
        .find((node) => node.textContent.trim() === 'Design system')
      if (el) el.click()
    })()`,
  )
  await sleep(500)
  result['design-system'] = await page.evaluate(
    `document.body.innerText.replace(/\\r/g, '').split('\\n').map((l) => l.trim()).filter(Boolean).join('\\n')`,
  )
  page.close()
  return result
}

const original = await dump(originalUrl, 9341)
const migration = await dump(migrationUrl, 9342)

let failures = 0
for (const key of Object.keys(original)) {
  const a = original[key].split('\n')
  const b = (migration[key] ?? '').split('\n')
  const max = Math.max(a.length, b.length)
  const diffs = []
  for (let i = 0; i < max; i++) {
    if (a[i] !== b[i]) diffs.push({ line: i + 1, original: a[i], migration: b[i] })
  }
  if (diffs.length === 0) {
    console.log(`${key.padEnd(16)} text identical (${a.length} lines)`)
  } else {
    failures++
    console.log(`${key.padEnd(16)} TEXT DIFFERS (${diffs.length} lines)`)
    for (const d of diffs.slice(0, 12)) {
      console.log(`   line ${d.line}`)
      console.log(`     original : ${JSON.stringify(d.original)}`)
      console.log(`     migration: ${JSON.stringify(d.migration)}`)
    }
    if (diffs.length > 12) console.log(`   ... ${diffs.length - 12} more`)
  }
}
console.log(failures === 0 ? '\nAll screens have identical visible text.' : `\n${failures} screen(s) differ.`)
