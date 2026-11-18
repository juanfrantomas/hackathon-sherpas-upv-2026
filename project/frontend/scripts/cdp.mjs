/**
 * Minimal Chrome DevTools Protocol client.
 *
 * Uses only Node built-ins (Node 22+ ships a global WebSocket), so the
 * project needs no browser-automation dependency.
 */
import { spawn } from 'node:child_process'
import { setTimeout as sleep } from 'node:timers/promises'

const CHROME = process.env.CHROME_PATH ?? '/usr/bin/google-chrome'

export async function launch({ port = 9222, width = 1440, height = 1000 } = {}) {
  const chrome = spawn(
    CHROME,
    [
      '--headless=new',
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--hide-scrollbars',
      '--force-device-scale-factor=1',
      `--window-size=${width},${height}`,
      `--remote-debugging-port=${port}`,
      '--remote-allow-origins=*',
      'about:blank',
    ],
    { stdio: 'ignore' },
  )

  let targets
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/list`)
      targets = await response.json()
      if (targets.length) break
    } catch {
      /* not up yet */
    }
    await sleep(200)
  }
  if (!targets?.length) throw new Error('Chrome DevTools endpoint never came up')

  const page = targets.find((target) => target.type === 'page')
  const socket = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true })
    socket.addEventListener('error', reject, { once: true })
  })

  let nextId = 0
  const pending = new Map()
  const listeners = new Map()

  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data)
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id)
      pending.delete(message.id)
      if (message.error) reject(new Error(`${message.error.message} (${message.error.code})`))
      else resolve(message.result)
      return
    }
    const handler = listeners.get(message.method)
    if (handler) handler(message.params)
  })

  const send = (method, params = {}) => {
    const id = ++nextId
    socket.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
  }

  const once = (method) =>
    new Promise((resolve) => {
      const handler = (params) => {
        listeners.delete(method)
        resolve(params)
      }
      listeners.set(method, handler)
    })

  const on = (method, handler) => {
    listeners.set(method, handler)
    return () => {
      if (listeners.get(method) === handler) listeners.delete(method)
    }
  }

  await send('Page.enable')
  await send('Runtime.enable')
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  })

  return {
    send,
    once,
    on,
    async goto(url) {
      const loaded = once('Page.loadEventFired')
      await send('Page.navigate', { url })
      await loaded
      await sleep(400)
    },
    async evaluate(expression) {
      const result = await send('Runtime.evaluate', {
        expression,
        awaitPromise: true,
        returnByValue: true,
      })
      if (result.exceptionDetails) {
        throw new Error(result.exceptionDetails.text ?? 'evaluation failed')
      }
      return result.result.value
    },
    async screenshot() {
      const { data } = await send('Page.captureScreenshot', { format: 'png' })
      return Buffer.from(data, 'base64')
    },
    async setViewport(width, height) {
      await send('Emulation.setDeviceMetricsOverride', {
        width,
        height,
        deviceScaleFactor: 1,
        mobile: false,
      })
    },
    close() {
      try {
        socket.close()
      } catch {
        /* ignore */
      }
      chrome.kill('SIGTERM')
    },
  }
}

export { sleep }
