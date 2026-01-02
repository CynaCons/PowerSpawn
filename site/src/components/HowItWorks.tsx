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
            Layered Supervision: User → Coordinator → Python → Sub-agents
          </p>
          <p className="text-sm text-gray-500 mt-2">
            The IAC.md pattern provides file-based inter-agent communication
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

          {/* Two-Mode Architecture Labels */}
          <div className="flex justify-center gap-8 mb-4">
            <div className="text-center">
              <div className="text-sm font-mono text-emerald-400 mb-2">CLI AGENTS</div>
              <div className="text-xs text-gray-500">Full File Access</div>
            </div>
            <div className="text-center">
              <div className="text-sm font-mono text-orange-400 mb-2">API AGENTS</div>
              <div className="text-xs text-gray-500">Text Response Only</div>
            </div>
          </div>

          {/* Arrow down split - 4 arrows for 4 agent types */}
          <div className="flex justify-center gap-12 mb-8">
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
              className="text-emerald-500 text-2xl"
            >
              ↓
            </motion.div>
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
              className="text-emerald-500 text-2xl"
            >
              ↓
            </motion.div>
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.6 }}
              className="text-orange-500 text-2xl"
            >
              ↓
            </motion.div>
            <motion.div
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: 0.8 }}
              className="text-orange-500 text-2xl"
            >
              ↓
            </motion.div>
          </div>

          {/* Sub-agents - CLI and API */}
          <div className="flex justify-center gap-4 flex-wrap">
            {/* CLI Agents */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.4 }}
              className="px-4 py-3 bg-emerald-600/20 border border-emerald-500 rounded-xl text-center"
            >
              <div className="text-emerald-400 font-bold mb-1">CODEX</div>
              <div className="text-xs text-gray-400">GPT-5.1</div>
              <div className="text-xs text-emerald-500/70 mt-1">CLI</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.45 }}
              className="px-4 py-3 bg-indigo-600/20 border border-indigo-500 rounded-xl text-center"
            >
              <div className="text-indigo-400 font-bold mb-1">CLAUDE</div>
              <div className="text-xs text-gray-400">Sonnet/Opus</div>
              <div className="text-xs text-emerald-500/70 mt-1">CLI</div>
            </motion.div>

            {/* API Agents */}
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="px-4 py-3 bg-orange-600/20 border border-orange-500 rounded-xl text-center"
            >
              <div className="text-orange-400 font-bold mb-1">GROK</div>
              <div className="text-xs text-gray-400">grok-3</div>
              <div className="text-xs text-orange-500/70 mt-1">API</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 15 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.55 }}
              className="px-4 py-3 bg-orange-600/20 border border-orange-500 rounded-xl text-center"
            >
              <div className="text-orange-400 font-bold mb-1">GEMINI</div>
              <div className="text-xs text-gray-400">2.0 Flash</div>
              <div className="text-xs text-orange-500/70 mt-1">API</div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={isInView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.6 }}
              className="px-4 py-3 bg-orange-600/20 border border-orange-500 rounded-xl text-center"
            >
              <div className="text-orange-400 font-bold mb-1">MISTRAL</div>
              <div className="text-xs text-gray-400">Large</div>
              <div className="text-xs text-orange-500/70 mt-1">API</div>
            </motion.div>
          </div>

          {/* Mode explanation */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.7 }}
            className="mt-8 flex justify-center gap-6 text-xs"
          >
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
              <span className="text-gray-400">CLI: Writes files directly</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span className="text-gray-400">API: Returns text to coordinator</span>
            </div>
          </motion.div>
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
