import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const roadmapItems = [
  // Completed
  { version: 'v0.1', title: 'Core Spawner', desc: 'spawn_claude, spawn_codex with IAC.md logging', status: 'completed' },
  { version: 'v0.2', title: 'MCP Server', desc: 'Full MCP protocol, wait_for_agents, context handling', status: 'completed' },
  { version: 'v0.3', title: 'Landing Page', desc: 'powerspawn.com with React + Tailwind', status: 'completed' },
  { version: 'v0.4', title: 'Copilot Integration', desc: 'spawn_copilot with GPT, Claude, and Gemini models', status: 'completed' },
  { version: 'v0.5', title: 'API Agents', desc: 'spawn_grok, spawn_gemini, spawn_mistral - Text-response agents via API', status: 'completed' },
  // Current
  { version: 'v0.6', title: 'Two-Mode Architecture', desc: 'CLI agents (file access) + API agents (text response) unified', status: 'current' },
  // Upcoming
  { version: 'v0.7', title: 'MCP Registry', desc: 'Submit to official MCP server registry', status: 'upcoming' },
  { version: 'v0.8', title: 'Reusable Contexts', desc: 'Spawn agents with previous session I/O. Chain agent generations with full context history in IAC', status: 'upcoming' },
  { version: 'v0.9', title: 'Test Suite', desc: 'Unit and integration tests with CI/CD', status: 'upcoming' },
  { version: 'v1.0', title: 'Stable Release', desc: 'Production-ready with full documentation', status: 'upcoming' },
]

export function Roadmap() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="py-24 px-4" id="roadmap">
      <div className="max-w-3xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Roadmap
          </h2>
          <p className="text-xl text-gray-400">
            From multi-agent spawner to production platform
          </p>
        </motion.div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-700" />

          <div className="space-y-6">
            {roadmapItems.map((item, index) => (
              <motion.div
                key={item.version}
                initial={{ opacity: 0, x: -20 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{ duration: 0.4, delay: 0.2 + index * 0.08 }}
                className={`relative pl-16 ${item.status === 'upcoming' ? 'opacity-50' : ''}`}
              >
                {/* Status indicator */}
                <div className={`absolute left-4 w-5 h-5 rounded-full border-2 flex items-center justify-center
                  ${item.status === 'completed' ? 'bg-green-500 border-green-500' : ''}
                  ${item.status === 'current' ? 'bg-orange-500 border-orange-500 animate-pulse' : ''}
                  ${item.status === 'upcoming' ? 'bg-transparent border-gray-600' : ''}
                `}>
                  {item.status === 'completed' && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>

                {/* Content */}
                <div className={`p-4 rounded-lg ${item.status === 'current' ? 'bg-orange-500/10 border border-orange-500/30' : ''}`}>
                  <div className="flex items-center gap-3 mb-1">
                    <span className={`text-sm font-mono ${
                      item.status === 'completed' ? 'text-green-400' :
                      item.status === 'current' ? 'text-orange-400' :
                      'text-gray-500'
                    }`}>
                      {item.version}
                    </span>
                    <span className={`font-semibold ${
                      item.status === 'current' ? 'text-orange-300' : 'text-white'
                    }`}>
                      {item.title}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm">
                    {item.desc}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
