/**
 * Exercises the prototype's interactions in a real browser and asserts the
 * outcome. A lightweight substitute for a unit-test suite: no test runner
 * dependency, but the same flows are checked end to end.
 *
 * Usage: node scripts/behaviour.mjs <url>
 */
import { launch, sleep } from './cdp.mjs'

const url = process.argv[2] ?? 'http://localhost:4173/'
const page = await launch({ port: 9343 })

let passed = 0
let failed = 0

const check = (name, condition, detail = '') => {
  if (condition) {
    passed++
    console.log(`  PASS  ${name}`)
  } else {
    failed++
    console.log(`  FAIL  ${name}${detail ? ` — ${detail}` : ''}`)
  }
}

const text = () =>
  page.evaluate(
    `(() => {
      const scope = document.querySelector('.phone__screen') ?? document.body
      return scope.innerText.replace(/\\n+/g, ' | ')
    })()`,
  )

const click = async (selector, textMatch) => {
  const found = await page.evaluate(
    `(() => {
      const nodes = [...document.querySelectorAll(${JSON.stringify(selector)})]
      const el = ${textMatch ? `nodes.find((n) => n.textContent.trim().includes(${JSON.stringify(textMatch)}))` : 'nodes[0]'}
      if (!el) return false
      el.click()
      return true
    })()`,
  )
  if (!found) throw new Error(`could not click ${selector} ${textMatch ?? ''}`)
  await sleep(320)
}

const has = (selector) =>
  page.evaluate(`!!document.querySelector(${JSON.stringify(selector)})`)

await page.goto(url)
await sleep(600)

console.log('\n— Welcome → Story → Home —')
check('opens on the welcome screen', await has('.screen--welcome'))
check('shows the household name', (await text()).includes('Timothy & Melanie'))
await click('.btn', 'Explore my financial plan')
check('advances to the story screen', await has('.screen--story'))
check('story shows four chapters', (await page.evaluate(`document.querySelectorAll('.player__progress .seg-bar').length`)) === 4)
await click('.link-btn', 'Skip')
check('skip lands on the home dashboard', await has('.home-head'))
check('story was recorded as watched', (await text()).includes('Your Financial Story') === false)

console.log('\n— Home —')
check('score card is present', await has('.score-card'))
check('focus tiles are present', (await page.evaluate(`document.querySelectorAll('.focus').length`)) === 3)
check('journey dots are present', (await page.evaluate(`document.querySelectorAll('.jm-dot').length`)) === 5)

console.log('\n— Plan —')
await click('.flow ol li button', 'My financial plan')
check('plan screen is shown', await has('.plan-strip'))
check('plan has six sections', (await page.evaluate(`document.querySelectorAll('.plan-strip .pill').length`)) === 6)
await click('.plan-strip .pill', 'Assets & Investments')
check('a section without case data shows the placeholder', await has('.pending'))
check('placeholder is labelled as sample data', (await text()).includes('PLACEHOLDER'))
await click('.plan-strip .pill', 'Debt management')
check('a section with case data shows a recommendation', await has('.rec'))
await click('.rec__head')
check('a recommendation expands', await has('.rec__body'))
check('the expanded answer has the three questions', (await page.evaluate(`document.querySelectorAll('.qa li').length`)) === 3)
check('the chart is rendered', await has('.rec__chart .chart'))

console.log('\n— Progress —')
await click('.flow ol li button', 'Goals & milestones')
check('milestone list is shown', await has('.ms-list'))
check('five milestones are listed', (await page.evaluate(`document.querySelectorAll('.ms-list > li').length`)) === 5)
await click('.ms__head')
check('a milestone expands', await has('.ms__body'))
await click('.ms__set .seg button', 'Completed')
check('status can be changed to completed', (await text()).includes('Completed'))
check('completion is praised', (await text()).includes("Nice work"))
await click('.flow ol li button', 'Progress overview')
check('journey tab shows the summary', await has('.journey-sum'))
check('completed steps are listed', (await text()).includes('Understand your credit card debt'))

console.log('\n— Check-in —')
await click('.flow ol li button', 'Check-in')
check('check-in screen is shown', await has('.screen--checkin'))
check('step counter starts at 1 of 3', (await text()).includes('1 of 3'))
await click('.choice', "I've made progress.")
check('progress answer advances to step 2', (await text()).includes('2 of 3'))
await click('.choice', "It's complete")
check('reaches the share step', (await text()).includes('3 of 3'))
check('the share preview is shown', await has('.share-preview'))
await click('.toggle input')
check('the share toggle can be switched on', await page.evaluate(`document.querySelector('.toggle input').checked`))
await click('.btn', 'Finish check-in')
check('the check-in completes', await has('.done'))
await click('.btn', 'See my progress')
check('returns to the journey', await has('.journey-sum'))
check('the check-in is recorded', (await text()).includes('Made progress on'))

console.log('\n— Mentor —')
await click('.flow ol li button', 'AI mentor')
check('mentor screen is shown', await has('.screen--mentor'))
check('suggested questions are offered', (await page.evaluate(`document.querySelectorAll('.prompt').length`)) === 4)
await click('.mic-main')
check('the microphone starts the conversation', await has('.screen--mentor.is-listening'))
await sleep(900) // the question is typed out word by word
check('the question is transcribed', (await text()).includes('Why should we worry'))
await click('.mic-main')
check('the mentor moves to thinking', await has('.screen--mentor.is-thinking'))
await sleep(1900)
check('the mentor starts speaking', await has('.screen--mentor.is-speaking'))
check('the answer is transcribed', (await text()).includes("That's a fair"))
await click('.mic-main')
check('speaking can be interrupted', await has('.screen--mentor.is-interrupted'))
await click('.ctl--end')
check('ending the session returns home', await has('.home-head'))

console.log('\n— Prototype controls —')
await page.evaluate(`(() => {
  const select = document.querySelector('#fam')
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set
  setter.call(select, 'carter')
  select.dispatchEvent(new Event('change', { bubbles: true }))
})()`)
await sleep(400)
check('changing household resets to the welcome screen', await has('.screen--welcome'))
check('the new household is shown', (await text()).includes('Welcome, Michael.'))

await click('.flow ol li button', 'Goals & milestones')
await click('.ms__head')
await click('.ms__set .seg button', 'Completed')
await click('.btn--ghost', 'Reset demo')
check('reset returns to the welcome screen', await has('.screen--welcome'))

console.log('\n— Design system —')
await click('.proto-bar .seg button', 'Design system')
check('the design system page is shown', await has('.ds'))
check('colour swatches are rendered', (await page.evaluate(`document.querySelectorAll('.sw').length`)) === 16)
check('the reference-status callout is present', (await text()).includes('Reference status'))

console.log(`\n${passed} passed, ${failed} failed`)
page.close()
process.exit(failed === 0 ? 0 : 1)
