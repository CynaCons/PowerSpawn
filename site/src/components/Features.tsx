import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const features = [
  {
    icon: '🔀',
    title: 'Dual-Mode Architecture',
    description: 'CLI Agents (Claude, Codex, Copilot, Gemini) have full file access. API Agents (Grok, Gemini, Mistral) return text responses that the coordinator applies.',
  },
  {
    icon: '🔌',
    title: 'Uses Your CLI Subscriptions',
    description: 'CLI agents use your existing subscriptions. API agents need API keys. Mix and match based on your setup.',
  },
  {
    icon: '🎯',
    title: 'Deterministic, Not Hopeful',
    description: 'Python MCP wraps CLIs (Claude, Codex, Copilot) and APIs (Grok, Gemini, Mistral), logging ALL inputs and outputs automatically. Great for reuse, transparency, and review.',
  },
  {
    icon: '⚖️',
    title: 'Load Balancing',
    description: 'Hit Claude rate limit? Spawn Codex or Copilot. One Copilot CLI gives you GPT, Claude, AND Gemini models.',
  },
  {
    icon: '👁️',
    title: 'Full Oversight',
    description: 'IAC.md (Inter Agent Context) tracks running agents, logs all inputs/outputs, and maintains complete audit trail.',
  },
  {
    icon: '💾',
    title: 'Session Resilience',
    description: 'File-based state survives process restarts, context window exhaustion, crashes, and days between sessions. Pick up exactly where you left off.',
  },
  {
    icon: '🚀',
    title: 'Parallel Execution',
    description: 'Multiple agents work simultaneously on different tasks. File-based architecture prevents conflicts.',
  },
  {
    icon: '📐',
    title: 'Extend Your Context Window',
    description: 'Sub-agents return concise summaries, not raw data. Your coordinator stays lean — enabling longer sessions and more complex tasks within model limits.',
  },
]

function FeatureCard({ feature, index }: { feature: typeof features[0], index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="group p-6 rounded-xl bg-[var(--ps-bg-card)] border border-gray-800 hover:border-indigo-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-indigo-500/10"
    >
      <div className="text-4xl mb-4 transform group-hover:scale-110 transition-transform duration-300">
        {feature.icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">
        {feature.title}
      </h3>
      <p className="text-gray-400 leading-relaxed">
        {feature.description}
      </p>
    </motion.div>
  )
}

export function Features() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="py-24 px-4" id="features">
      <div className="max-w-6xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Why PowerSpawn?
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Built for developers who need reliable, observable multi-agent orchestration
          </p>
        </motion.div>

        {/* Core Principle Callout */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mb-12 p-6 rounded-xl bg-gradient-to-r from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 max-w-3xl mx-auto"
        >
          <div className="text-center">
            <div className="text-indigo-400 font-mono text-sm mb-2">THE DETERMINISM PRINCIPLE</div>
            <blockquote className="text-xl md:text-2xl text-white font-medium italic">
              "Everything that CAN be done deterministically SHALL be done deterministically."
            </blockquote>
            <p className="mt-4 text-gray-400 text-sm">
              The Python MCP wraps CLIs (Claude, Codex, Copilot, Gemini) and APIs (Grok, Gemini, Mistral), capturing every input and output deterministically.
              <br />
              <span className="text-gray-500">Complete transparency. Easy reuse. Full audit trail for review.</span>
            </p>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <FeatureCard key={feature.title} feature={feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}
