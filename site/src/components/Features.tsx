import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const features = [
  {
    icon: '🔌',
    title: 'Uses Your CLI Subscriptions',
    description: 'Spawns real CLI agents (Claude Code, Copilot, Codex) you already have. No separate API keys needed.',
  },
  {
    icon: '🎯',
    title: 'Deterministic, Not Hopeful',
    description: 'MCP wraps agents and captures all I/O automatically. No relying on agents to "follow instructions".',
  },
  {
    icon: '⚖️',
    title: 'Load Balancing',
    description: 'Hit Claude rate limit? Spawn Codex instead. Distribute work across multiple AI subscriptions.',
  },
  {
    icon: '👁️',
    title: 'Full Oversight',
    description: 'CONTEXT.md shows running agents. IAC.md logs all inputs/outputs. Complete audit trail.',
  },
  {
    icon: '💾',
    title: 'Persistent Memory',
    description: 'File-based state survives context window exhaustion, crashes, and days between sessions.',
  },
  {
    icon: '🚀',
    title: 'Parallel Execution',
    description: 'Multiple agents work simultaneously on different tasks. File-based architecture prevents conflicts.',
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
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Why PowerSpawn?
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Built for developers who need reliable, observable multi-agent orchestration
          </p>
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
