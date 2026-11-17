import { useEffect, useState } from 'react'
import { Button } from '../../../components/ui/Button'
import { Eyebrow } from '../../../components/ui/Eyebrow'
import { Icon } from '../../../components/ui/Icon'
import { Wordmark } from '../../../components/brand/Wordmark'
import type { Dispatch } from 'react'
import type { FamilyAction } from '../state/familyReducer'
import type { Family, Navigate } from '../types'

/** Milliseconds each chapter of the story is shown for. */
const CHAPTER_DURATION = 6500

export interface StoryScreenProps {
  family: Family
  go: Navigate
  dispatch: Dispatch<FamilyAction>
}

/** Screen 2 — the animated story of the household's plan. */
export function StoryScreen({ family, go, dispatch }: StoryScreenProps) {
  const chapters = family.story
  const total = chapters.length * CHAPTER_DURATION

  const [elapsed, setElapsed] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [captions, setCaptions] = useState(true)

  const finished = elapsed >= total
  const index = Math.min(chapters.length - 1, Math.floor(elapsed / CHAPTER_DURATION))
  const progress = finished ? 1 : (elapsed - index * CHAPTER_DURATION) / CHAPTER_DURATION
  const chapter = chapters[index]

  // A new household restarts the story.
  const [trackedFamily, setTrackedFamily] = useState(family.id)
  if (trackedFamily !== family.id) {
    setTrackedFamily(family.id)
    setElapsed(0)
    setPlaying(true)
  }

  useEffect(() => {
    if (!playing || finished) return
    const timer = setInterval(() => {
      setElapsed((value) => Math.min(total, value + 50))
    }, 50)
    return () => clearInterval(timer)
  }, [playing, finished, total])

  const jumpTo = (chapterIndex: number) => {
    setElapsed(chapterIndex * CHAPTER_DURATION)
    setPlaying(true)
  }

  const finish = () => {
    dispatch({ type: 'mark_watched' })
    go('home')
  }

  const replay = () => jumpTo(0)

  return (
    <div className="screen screen--story">
      <div className="story__head">
        <Wordmark size="sm" />
        <button className="link-btn" onClick={finish}>
          Skip
        </button>
      </div>

      <div className="story__intro">
        <Eyebrow>Made for the {family.surname} household</Eyebrow>
        <h1 className="h-display">Your Financial Story</h1>
        <p className="muted">
          Let's understand where you are today and where you want to go.
        </p>
      </div>

      <div className="player">
        <div className="player__frame" onClick={() => !finished && setPlaying((value) => !value)}>
          <span className="player__flag">
            Storyboard preview · placeholder for the AI video
          </span>

          {finished ? (
            family.videoUrl ? (
              <video
                className="scene__video"
                src={family.videoUrl}
                controls
                autoPlay
                playsInline
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              />
            ) : (
              <div className="scene scene--end">
                <div className="scene__done">
                  <Icon name="play" size={22} stroke={2.2} />
                </div>
                <div className="scene__label">Your AI-generated video</div>
                <div className="scene__sub">
                  Delivered by the backend (videoUrl) once your plan is processed.
                </div>
              </div>
            )
          ) : (
            <div className="scene" key={`${family.id}-${index}`}>
              <div className="scene__chapter">
                {String(index + 1).padStart(2, '0')} · {chapter.chapter}
              </div>
              <div className="scene__big num">{chapter.big}</div>
              <div className="scene__label">{chapter.label}</div>
              <svg
                className="scene__ridge"
                viewBox="0 0 400 80"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path
                  d="M0 80 L70 38 L120 58 L190 14 L250 50 L300 30 L400 66 L400 80Z"
                  fill="currentColor"
                />
              </svg>
            </div>
          )}

          {!playing && !finished && (
            <div className="player__paused">
              <Icon name="play" size={28} />
            </div>
          )}
        </div>

        {captions && !finished && (
          <p className="captions" aria-live="polite">
            {chapter.caption}
          </p>
        )}

        <div className="player__progress" role="group" aria-label="Story progress">
          {chapters.map((item, itemIndex) => (
            <button
              key={item.chapter}
              className="seg-bar"
              onClick={() => jumpTo(itemIndex)}
              aria-label={`Chapter ${itemIndex + 1}: ${item.chapter}`}
            >
              <span
                style={{
                  width:
                    (finished || itemIndex < index
                      ? 100
                      : itemIndex === index
                        ? progress * 100
                        : 0) + '%',
                }}
              />
            </button>
          ))}
        </div>

        <div className="player__chapters">
          <span className="is-on">{finished ? 'Complete' : chapter.chapter}</span>
          <span className="num">
            {finished ? chapters.length : index + 1} of {chapters.length}
          </span>
        </div>

        <div className="player__controls">
          <button className="icon-btn" onClick={replay} aria-label="Replay">
            <Icon name="replay" size={20} />
          </button>
          <button
            className="play-btn"
            onClick={() => (finished ? replay() : setPlaying((value) => !value))}
            aria-label={playing ? 'Pause' : 'Play'}
          >
            <Icon name={playing ? 'pause' : 'play'} size={22} />
          </button>
          <button
            className={`icon-btn${captions ? ' is-on' : ''}`}
            onClick={() => setCaptions((value) => !value)}
            aria-label="Captions"
            aria-pressed={captions}
          >
            <Icon name="cc" size={20} />
          </button>
        </div>
      </div>

      <div className="story__foot">
        <Button
          block
          size="lg"
          variant={finished ? 'primary' : 'secondary'}
          iconRight="arrowRight"
          onClick={finish}
        >
          Continue to my dashboard
        </Button>
      </div>
    </div>
  )
}
