import { useEffect, useMemo, useState } from 'react'

/**
 * Reveals a text word by word while `active` is true, and shows all of it
 * once it is false.
 *
 * @param text      Text to reveal.
 * @param active    Whether the reveal is currently running.
 * @param msPerWord Time between words, in milliseconds.
 * @param startWord Number of words visible before the reveal starts.
 */
export function useTypewriter(
  text: string,
  active: boolean,
  msPerWord = 45,
  startWord = 0,
): string {
  const words = useMemo(() => text.split(' '), [text])
  const [revealed, setRevealed] = useState(startWord)
  const [tracked, setTracked] = useState({ text, active, startWord })

  // Restart the reveal when the text changes, or when the run starts or stops.
  if (
    tracked.text !== text ||
    tracked.active !== active ||
    tracked.startWord !== startWord
  ) {
    setTracked({ text, active, startWord })
    setRevealed(active ? startWord : words.length)
  }

  useEffect(() => {
    if (!active || revealed >= words.length) return
    const timer = setTimeout(() => {
      setRevealed((value) => value + 1)
    }, msPerWord * 4)
    return () => clearTimeout(timer)
  }, [revealed, active, words.length, msPerWord])

  return words.slice(0, revealed).join(' ')
}
