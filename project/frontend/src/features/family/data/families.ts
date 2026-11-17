import type { Family } from '../types'

/**
 * The four demo households.
 *
 * Every figure and every line of copy here is transcribed verbatim from the
 * prototype bundle. It is a curated projection of the Sherpas plan data in
 * `cases/` — do not recompute or "correct" these numbers.
 */
export const FAMILIES: Family[] = [
      {
        id: "weah",
        caseId: "timothy-melanie-weah",
        household: "Weah household",
        names: "Timothy & Melanie",
        surname: "Weah",
        initials: "TM",
        score: 60,
        scoreNote:
          "A score of 60 suggests you manage to get by, but you aren't thriving financially yet. Your plan's main question is how to prioritize the money you already have.",
        facts: [
          { label: "Cash", value: "$150,000" },
          { label: "Credit card debt", value: "$18,000", sub: "18% interest" },
          { label: "Children", value: "2" },
        ],
        challenge: "Deciding how to prioritize your money",
        focusAreas: [
          {
            label: "Credit card debt",
            detail: "$18,000 at 18% interest",
            tone: "warn",
          },
          { label: "Cash savings", detail: "$150,000 available", tone: "ok" },
          { label: "Family", detail: "Two children", tone: "neutral" },
        ],
        nextStep: {
          title: "Understand your credit card debt",
          why: "You hold $150,000 in cash while carrying $18,000 on credit cards at 18% interest. Seeing how those two fit together is the first decision in your plan.",
          section: "debt",
          milestone: "w1",
          topic: "Credit card debt",
        },
        story: [
          {
            chapter: "Where you are",
            big: "$150,000",
            label: "in cash",
            caption:
              "Timothy and Melanie, you've built $150,000 in cash. That's a real foundation for your family of four.",
          },
          {
            chapter: "What you're carrying",
            big: "$18,000",
            label: "credit card debt at 18%",
            caption:
              "At the same time, you carry $18,000 in credit card debt at 18% interest.",
          },
          {
            chapter: "Your challenge",
            big: "1 question",
            label: "How should we prioritize our money?",
            caption:
              "Your plan's central question is how to prioritize your money between paying down debt and keeping savings.",
          },
          {
            chapter: "Next steps",
            big: "Step 1",
            label: "Understand your credit card debt",
            caption:
              "Your first step is to understand your credit card debt. Your mentor is here whenever you want to talk it through.",
          },
        ],
        sections: {
          summary: {
            cards: [
              {
                id: "s1",
                title: "Your financial health score is 60",
                what: "Sherpas scored your plan at 60.",
                why: "The score helps you see, at a glance, how your current choices support your family.",
                next: "Start with your main priority: how to use your cash and debt together.",
                chart: "score",
              },
            ],
          },
          debt: {
            cards: [
              {
                id: "d1",
                title: "High-interest credit card debt",
                what: "You carry $18,000 in credit card debt at 18% interest, while holding $150,000 in cash.",
                why: "Credit card interest at 18% is expensive. As simple arithmetic, 18% of $18,000 is $3,240 over a year if the balance stays the same. That's money that can't go toward your family's goals.",
                next: "Understand the debt first, then decide with your plan (or advisor) how much of your cash should go toward it.",
                chart: "cashDebt",
                milestone: "w1",
              },
            ],
          },
          savings: {
            cards: [
              {
                id: "v1",
                title: "A strong cash position",
                what: "You have $150,000 in cash.",
                why: "Cash gives your family security. Your plan's question is how much of it to keep available and how much to put to work.",
                next: "Review your savings strategy once you understand your debt.",
                chart: "cashDebt",
                milestone: "w2",
              },
            ],
          },
          retirement: { pending: true },
          assets: { pending: true },
          protection: { pending: true },
        },
        milestones: [
          {
            id: "w1",
            title: "Understand your credit card debt",
            why: "Credit card debt at 18% interest is expensive to carry.",
            action: "Read the debt section and ask your mentor any question.",
            section: "debt",
            status: "in_progress",
            checkin: "Dec 14",
          },
          {
            id: "w2",
            title: "Review your savings strategy",
            why: "You have $150,000 in cash. Decide how much you want to keep available.",
            action: "Open Savings & Expenses in your plan.",
            section: "savings",
            status: "not_started",
          },
          {
            id: "w3",
            title: "Discuss financial priorities with your partner",
            why: "Prioritizing your money is a decision you make together.",
            action:
              "Use the mentor's summary as a starting point for your conversation.",
            section: "summary",
            status: "not_started",
          },
          {
            id: "w4",
            title: "Review your retirement goals",
            why: "Your plan includes a Retirement & Goals section worth revisiting together.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "w5",
            title: "Review your family's protection",
            why: "With two children, your plan's protection section matters.",
            action: "Open Insurance & Protection in your plan.",
            section: "protection",
            status: "not_started",
          },
        ],
        mentor: {
          topic: "Credit card debt",
          question:
            "Why should we worry about our credit card when we have so much cash?",
          answer:
            "That's a fair question. Your plan shows $150,000 in cash and $18,000 on credit cards at 18% interest. At that rate, the card costs you about $3,240 a year if the balance doesn't change. Your cash is a real strength, so the question isn't whether you're doing badly. It's whether some of that cash should go toward the card while you keep enough set aside for your family. That's the choice your plan asks you to make.",
          prompts: [
            "Can you explain this more simply?",
            "How much cash should we keep available?",
            "What should we focus on this month?",
          ],
        },
        checkinPriority: "understanding your credit card debt",
        advisor: {
          engagement: "Active",
          lastCheckin: "Nov 9",
          shared: [
            {
              kind: "question",
              text: "Why should we worry about our credit card when we have so much cash?",
              date: "Nov 9",
            },
          ],
        },
      },
      {
        id: "carter",
        caseId: "michael-carter",
        household: "Carter household",
        names: "Michael",
        surname: "Carter",
        initials: "MC",
        score: 26,
        scoreNote:
          "Your score shows real pressure in your plan today. You have two large goals close together, and your plan helps you see how they connect.",
        facts: [
          { label: "Home goal", value: "$550,000", sub: "in 2027" },
          { label: "Retirement goal", value: "Age 58" },
        ],
        challenge:
          "Understanding the trade-off between your home and retirement",
        focusAreas: [
          { label: "Buy a home", detail: "$550,000 in 2027", tone: "neutral" },
          { label: "Retire early", detail: "At age 58", tone: "neutral" },
        ],
        nextStep: {
          title: "Understand how your two goals connect",
          why: "Buying a $550,000 home in 2027 and retiring at 58 draw on the same resources. Seeing the trade-off clearly comes before choosing.",
          section: "retirement",
          milestone: "c1",
          topic: "Home vs. retirement",
        },
        story: [
          {
            chapter: "Where you are",
            big: "26",
            label: "financial health score",
            caption:
              "Michael, your financial health score is 26. That's a starting point, not a verdict.",
          },
          {
            chapter: "Your goals",
            big: "2027 \xB7 58",
            label: "a $550,000 home, retirement at 58",
            caption:
              "You want to buy a $550,000 home in 2027 and retire at age 58.",
          },
          {
            chapter: "Your challenge",
            big: "Trade-off",
            label: "Two goals, one set of resources",
            caption:
              "Both goals are meaningful, and they compete for the same money. Your plan helps you see the trade-off.",
          },
          {
            chapter: "Next steps",
            big: "Step 1",
            label: "Understand how your goals connect",
            caption:
              "Your first step is to understand how the home and early retirement affect each other.",
          },
        ],
        sections: {
          summary: {
            cards: [
              {
                id: "s1",
                title: "Your financial health score is 26",
                what: "Sherpas scored your plan at 26.",
                why: "A lower score means your plan has more pressure points. It doesn't mean your goals are out of reach.",
                next: "Start by understanding the trade-off between your two main goals.",
                chart: "score",
              },
            ],
          },
          retirement: {
            cards: [
              {
                id: "r1",
                title: "A home in 2027 and retirement at 58",
                what: "Your plan includes buying a $550,000 home in 2027 and retiring at age 58.",
                why: "Money used for one goal isn't available for the other. Understanding that link helps you choose with confidence.",
                next: "Talk the trade-off through with your mentor, then review both goals.",
                chart: "timelineCarter",
                milestone: "c1",
              },
            ],
          },
          assets: { pending: true },
          debt: { pending: true },
          savings: { pending: true },
          protection: { pending: true },
        },
        milestones: [
          {
            id: "c1",
            title: "Understand the home vs. retirement trade-off",
            why: "Both goals draw on the same resources.",
            action: "Ask your mentor how buying a house affects retirement.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "c2",
            title: "Review your home purchase goal",
            why: "$550,000 in 2027 is your nearest large goal.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "c3",
            title: "Review your retirement goal",
            why: "Retiring at 58 shapes everything else in your plan.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "c4",
            title: "Decide which goal leads",
            why: "A clear order makes each next step simpler.",
            action: "Record your decision in your next check-in.",
            section: "summary",
            status: "not_started",
          },
        ],
        mentor: {
          topic: "Home vs. retirement",
          question: "How does buying a house affect retirement?",
          answer:
            "Your plan has two big goals: a $550,000 home in 2027 and retiring at 58. Money you put toward the home isn't available to build retirement savings, so the two are linked. I can walk you through how your plan describes each goal, so you can decide which one should lead.",
          prompts: [
            "Can you explain this more simply?",
            "What does my score of 26 mean?",
            "What should I focus on this month?",
          ],
        },
        checkinPriority: "understanding your home and retirement trade-off",
        advisor: { engagement: "Invited", lastCheckin: null, shared: [] },
      },
      {
        id: "johnson",
        caseId: "daniel-emily-johnson",
        household: "Johnson household",
        names: "Daniel & Emily",
        surname: "Johnson",
        initials: "DE",
        score: 52,
        scoreNote:
          "Your plan balances two goals that matter to your family: your children's college and your retirement.",
        facts: [
          { label: "Children", value: "2" },
          { label: "Goals", value: "College & retirement" },
        ],
        challenge: "Deciding which financial priorities come first",
        focusAreas: [
          {
            label: "College funding",
            detail: "For your two children",
            tone: "neutral",
          },
          { label: "Retirement", detail: "Your own future", tone: "neutral" },
        ],
        nextStep: {
          title: "Compare your college and retirement goals",
          why: "Both goals compete for the same money. Seeing them side by side is the first step toward deciding what comes first.",
          section: "retirement",
          milestone: "j1",
          topic: "College vs. retirement",
        },
        story: [
          {
            chapter: "Where you are",
            big: "52",
            label: "financial health score",
            caption: "Daniel and Emily, your financial health score is 52.",
          },
          {
            chapter: "Your goals",
            big: "2 goals",
            label: "College funding and retirement",
            caption:
              "You want to fund college for your two children and prepare for retirement.",
          },
          {
            chapter: "Your challenge",
            big: "Order",
            label: "What comes first?",
            caption:
              "Your main challenge is deciding which priority comes first.",
          },
          {
            chapter: "Next steps",
            big: "Step 1",
            label: "Compare both goals",
            caption:
              "Your first step is to see both goals side by side, then talk it through together.",
          },
        ],
        sections: {
          summary: {
            cards: [
              {
                id: "s1",
                title: "Your financial health score is 52",
                what: "Sherpas scored your plan at 52.",
                why: "Your score reflects how well your current choices support both of your goals.",
                next: "Start by comparing your college and retirement goals.",
                chart: "score",
              },
            ],
          },
          retirement: {
            cards: [
              {
                id: "r1",
                title: "College and retirement compete",
                what: "Your plan includes college funding for two children and retirement goals.",
                why: "Both goals draw on the same income and savings, so the order you choose matters.",
                next: "Compare both goals, then discuss priorities together.",
                chart: "twoGoals",
                milestone: "j1",
              },
            ],
          },
          assets: { pending: true },
          debt: { pending: true },
          savings: { pending: true },
          protection: { pending: true },
        },
        milestones: [
          {
            id: "j1",
            title: "Compare your college and retirement goals",
            why: "You can't decide what comes first until you see both clearly.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "completed",
          },
          {
            id: "j2",
            title: "Discuss financial priorities with your partner",
            why: "This is a family decision.",
            action: "Use your mentor's summary to start the conversation.",
            section: "summary",
            status: "in_progress",
            checkin: "Dec 7",
          },
          {
            id: "j3",
            title: "Prepare for upcoming education expenses",
            why: "College funding for two children is one of your main goals.",
            action: "Review the goals section of your plan.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "j4",
            title: "Review your retirement goals",
            why: "Your retirement goal is the other half of the decision.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "not_started",
          },
        ],
        mentor: {
          topic: "College vs. retirement",
          question: "Should we save for college or retirement first?",
          answer:
            "Your plan includes both college funding for your two children and your retirement. They compete for the same money, so the order matters. I can explain how your plan describes each goal. The decision itself is yours, and if you work with an advisor, it's a good one to bring to them.",
          prompts: [
            "Can you explain this more simply?",
            "What should we focus on this month?",
            "How do we talk about this together?",
          ],
        },
        checkinPriority: "discussing your priorities together",
        advisor: {
          engagement: "Active",
          lastCheckin: "Nov 2",
          shared: [
            {
              kind: "update",
              text: "We've compared both goals and are discussing which comes first.",
              date: "Nov 2",
            },
          ],
        },
      },
      {
        id: "lewis",
        caseId: "samantha-lewis",
        household: "Lewis household",
        names: "Samantha",
        surname: "Lewis",
        initials: "SL",
        score: 82,
        scoreNote:
          "A strong score, with no debt. Your plan also shows new commitments ahead, so staying informed now keeps it strong.",
        facts: [
          { label: "Debt", value: "None" },
          { label: "College", value: "Beginning" },
          { label: "Second home", value: "2030" },
        ],
        challenge: "Understanding future commitments despite a strong score",
        focusAreas: [
          {
            label: "College expenses",
            detail: "Beginning now",
            tone: "neutral",
          },
          { label: "Second home", detail: "Planned for 2030", tone: "neutral" },
          { label: "Debt", detail: "None", tone: "ok" },
        ],
        nextStep: {
          title: "Map your upcoming commitments",
          why: "College expenses are beginning and you plan a second home in 2030. A strong score today doesn't show what's coming next.",
          section: "retirement",
          milestone: "l1",
          topic: "Future commitments",
        },
        story: [
          {
            chapter: "Where you are",
            big: "82",
            label: "financial health score",
            caption:
              "Samantha, your financial health score is 82, and you have no debt.",
          },
          {
            chapter: "Your goals",
            big: "2030",
            label: "A second home",
            caption: "You plan to buy a second home in 2030.",
          },
          {
            chapter: "Your challenge",
            big: "Ahead",
            label: "Commitments a score doesn't show",
            caption:
              "College expenses are beginning. Your challenge is understanding future commitments while your score is strong.",
          },
          {
            chapter: "Next steps",
            big: "Step 1",
            label: "Map what's coming",
            caption:
              "Your first step is to map your upcoming commitments in one place.",
          },
        ],
        sections: {
          summary: {
            cards: [
              {
                id: "s1",
                title: "Your financial health score is 82",
                what: "Sherpas scored your plan at 82, and you have no debt.",
                why: "A strong score reflects today. Your plan also includes commitments that are just starting.",
                next: "Map your upcoming commitments.",
                chart: "score",
              },
            ],
          },
          retirement: {
            cards: [
              {
                id: "r1",
                title: "Commitments ahead",
                what: "College expenses are beginning, and you plan to buy a second home in 2030.",
                why: "Both commitments arrive while your score is strong. Planning for them now protects that position.",
                next: "Review each commitment with your mentor.",
                chart: "timelineLewis",
                milestone: "l1",
              },
            ],
          },
          debt: {
            cards: [
              {
                id: "d1",
                title: "No debt",
                what: "Your plan shows no debt.",
                why: "That gives you flexibility as new commitments begin.",
                next: "No action needed here. Focus on what's ahead.",
                chart: null,
              },
            ],
          },
          assets: { pending: true },
          savings: { pending: true },
          protection: { pending: true },
        },
        milestones: [
          {
            id: "l1",
            title: "Map your upcoming commitments",
            why: "College is beginning and a second home is planned for 2030.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "in_progress",
            checkin: "Dec 10",
          },
          {
            id: "l2",
            title: "Prepare for college expenses",
            why: "These expenses are beginning now.",
            action: "Ask your mentor what your plan says about college.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "l3",
            title: "Review your second-home goal",
            why: "2030 is close enough to plan for today.",
            action: "Open Retirement & Goals in your plan.",
            section: "retirement",
            status: "not_started",
          },
          {
            id: "l4",
            title: "Understand what your score covers",
            why: "A strong score is a snapshot, not a forecast.",
            action: "Read the Summary section.",
            section: "summary",
            status: "completed",
          },
        ],
        mentor: {
          topic: "Future commitments",
          question: "My score is 82. Why do I need to think about this now?",
          answer:
            "Your score of 82 and having no debt are real strengths. Your plan also shows college expenses beginning and a second home planned for 2030. A score describes today; those commitments are what's ahead. Understanding them now helps keep your plan strong.",
          prompts: [
            "Can you explain this more simply?",
            "What should I focus on this month?",
            "What does my plan say about 2030?",
          ],
        },
        checkinPriority: "mapping your upcoming commitments",
        advisor: { engagement: "Active", lastCheckin: "Oct 28", shared: [] },
      },
    ]

export const FAMILY_IDS = FAMILIES.map((family) => family.id)

export function getFamily(id: string): Family {
  const family = FAMILIES.find((candidate) => candidate.id === id)
  if (!family) {
    throw new Error(`Unknown family: ${id}`)
  }
  return family
}
