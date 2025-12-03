import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

export function HowItWorks() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="py-24 px-4 bg-gradient-to-b from-transparent via-indigo-900/10 to-transparent" id="how-it-works">
      <div className="max-w-5xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            How It Works
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            The IAC.md Pattern — File-based inter-agent communication
          </p>
        </motion.div>

        {/* Architecture diagram */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative"
        >
          {/* Coordinator */}
          <div className="flex justify-center mb-8">
            <div className="px-8 py-4 bg-indigo-600 rounded-xl text-white font-semibold text-center shadow-lg shadow-indigo-500/30">
              <div className="text-sm text-indigo-200 mb-1">COORDINATOR</div>
              <div className="text-lg">Claude Code / Copilot</div>
            </div>
          </div>

          {/* Arrow down */}
          <div className="flex justify-center mb-8">
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-gray-500 text-2xl"
            >
              ↓
            </motion.div>
          </div>

          {/* IAC.md box */}
          <div className="flex justify-center mb-8">
            <div className="px-12 py-6 bg-[var(--ps-bg-card)] rounded-xl border-2 border-cyan-500 text-center max-w-md">
              <div className="text-cyan-400 font-mono font-bold text-xl mb-3">IAC.md</div>
              <div className="space-y-2 text-sm text-gray-400">
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Task assignments
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Agent results
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Human-readable log
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> Git-trackable
                </div>
              </div>
            </div>
          </div>

          {/* Arrow down split */}
          <div className="flex justify-center gap-32 mb-8">
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.3 }}
              className="text-gray-500 text-2xl"
            >
              ↓
            </motion.div>
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.6 }}
              className="text-gray-500 text-2xl"
            >
              ↓
            </motion.div>
          </div>

          {/* Sub-agents */}
          <div className="flex justify-center gap-8 flex-wrap">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="px-6 py-4 bg-emerald-600/20 border border-emerald-500 rounded-xl text-center"
            >
              <div className="text-emerald-400 font-bold mb-1">CODEX</div>
              <div className="text-sm text-gray-400">GPT-5.1 models</div>
              <div className="text-xs text-gray-500 mt-2">Reads AGENTS.md</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="px-6 py-4 bg-indigo-600/20 border border-indigo-500 rounded-xl text-center"
            >
              <div className="text-indigo-400 font-bold mb-1">CLAUDE</div>
              <div className="text-sm text-gray-400">Claude models</div>
              <div className="text-xs text-gray-500 mt-2">Reads CLAUDE.md</div>
            </motion.div>
          </div>
        </motion.div>

        {/* Benefits */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mt-16 grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto"
        >
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[var(--ps-bg-card)]">
            <span className="text-2xl">📋</span>
            <div>
              <div className="font-semibold text-white">Auditable</div>
              <div className="text-sm text-gray-400">Every interaction logged in plain markdown</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[var(--ps-bg-card)]">
            <span className="text-2xl">🔍</span>
            <div>
              <div className="font-semibold text-white">Debuggable</div>
              <div className="text-sm text-gray-400">Read IAC.md to see exactly what happened</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[var(--ps-bg-card)]">
            <span className="text-2xl">💪</span>
            <div>
              <div className="font-semibold text-white">Resilient</div>
              <div className="text-sm text-gray-400">Survives restarts and session timeouts</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-[var(--ps-bg-card)]">
            <span className="text-2xl">🔀</span>
            <div>
              <div className="font-semibold text-white">Version Control</div>
              <div className="text-sm text-gray-400">Git tracks your entire agent history</div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
