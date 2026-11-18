import type { ReactNode, RefObject } from 'react'
import { PhoneFrame } from '../features/family/components/phone/PhoneFrame'
import { TabBar } from '../features/family/components/TabBar'
import { CheckInScreen } from '../features/family/components/checkin/CheckInScreen'
import { HomeDashboard } from '../features/family/components/HomeDashboard'
import { MentorScreen } from '../features/family/components/MentorScreen'
import { PlanScreen } from '../features/family/components/PlanScreen'
import { ProgressScreen } from '../features/family/components/ProgressScreen'
import { StoryScreen } from '../features/family/components/StoryScreen'
import { WelcomeScreen } from '../features/family/components/WelcomeScreen'
import { useFamilyData, useNavigation } from '../features/family/state/useFamily'
import type { FamilyScreen, MilestoneStatus, NavigationState } from '../features/family/types'

export interface FamilyPhoneProps {
  /** Scroll container of the phone, reset on every screen change. */
  scrollRef: RefObject<HTMLDivElement | null>
}

/** The phone mockup, and the screen that the app is currently showing. */
export function FamilyPhone({ scrollRef }: FamilyPhoneProps) {
  const { family, state, dispatch, milestones, current } = useFamilyData()
  const { screen, nav, voice, screenKey, go, setNav } = useNavigation()

  const showTabBar =
    screen === 'home' || screen === 'plan' || screen === 'progress'

  const setStatus = (milestoneId: string, status: MilestoneStatus) => {
    dispatch({ type: 'set_milestone_status', milestoneId, status })
  }

  const screenContent = (): ReactNode => {
    switch (screen) {
      case 'welcome':
        return <WelcomeScreen family={family} go={go} />
      case 'story':
        return <StoryScreen family={family} go={go} dispatch={dispatch} />
      case 'home':
        return (
          <HomeDashboard
            family={family}
            state={state}
            milestones={milestones}
            current={current}
            go={go}
          />
        )
      case 'plan':
        return <PlanScreen family={family} nav={nav} setNav={setNav} go={go} />
      case 'progress':
        return (
          <ProgressScreen
            state={state}
            milestones={milestones}
            nav={nav}
            setNav={setNav}
            setStatus={setStatus}
            go={go}
          />
        )
      case 'checkin':
        return (
          <CheckInScreen
            family={family}
            milestoneId={current?.id ?? null}
            milestoneTitle={current?.title}
            onCompleteMilestone={(milestoneId) =>
              dispatch({ type: 'complete_milestone', milestoneId })
            }
            onFinish={(payload) => dispatch({ type: 'commit_checkin', payload })}
            go={go}
          />
        )
      case 'mentor':
        return <MentorScreen family={family} nav={nav} voice={voice} go={go} />
    }
  }

  return (
    <div className="phone-wrap">
      <PhoneFrame
        screen={screen as FamilyScreen}
        screenKey={screenKey}
        scrollRef={scrollRef}
        tabBar={showTabBar ? <TabBar active={screen} go={go} /> : undefined}
      >
        {screenContent()}
      </PhoneFrame>
    </div>
  )
}

export type { NavigationState }
