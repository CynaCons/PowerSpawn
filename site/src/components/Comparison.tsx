import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const comparisonData = [
  { feature: 'Cross-model spawning', powerSpawn: true, autoGen: false, crewAI: false, langGraph: false },
  { feature: 'Uses CLI subscriptions', powerSpawn: true, autoGen: false, crewAI: false, langGraph: false },
  { feature: 'Deterministic logging', powerSpawn: true, autoGen: false, crewAI: false, langGraph: false },
  { feature: 'File-based persistence', powerSpawn: true, autoGen: false, crewAI: false, langGraph: false },
  { feature: 'Zero infrastructure', powerSpawn: true, autoGen: 'partial', crewAI: 'partial', langGraph: false },
  { feature: 'MCP protocol native', powerSpawn: true, autoGen: false, crewAI: false, langGraph: false },
]

function Cell({ value }: { value: boolean | string }) {
  if (value === true) {
    return <span className="text-green-400 font-bold">✓</span>
  } else if (value === 'partial') {
    return <span className="text-yellow-400">~</span>
  }
  return <span className="text-gray-600">✗</span>
}

export function Comparison() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="py-24 px-4" id="comparison">
      <div className="max-w-4xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Comparison
          </h2>
          <p className="text-xl text-gray-400">
            How PowerSpawn stacks up against other frameworks
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="overflow-x-auto"
        >
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="py-4 px-4 text-left text-gray-400 font-medium">Feature</th>
                <th className="py-4 px-4 text-center text-indigo-400 font-bold">PowerSpawn</th>
                <th className="py-4 px-4 text-center text-gray-400 font-medium">AutoGen</th>
                <th className="py-4 px-4 text-center text-gray-400 font-medium">CrewAI</th>
                <th className="py-4 px-4 text-center text-gray-400 font-medium">LangGraph</th>
              </tr>
            </thead>
            <tbody>
              {comparisonData.map((row, index) => (
                <motion.tr
                  key={row.feature}
                  initial={{ opacity: 0, x: -20 }}
                  animate={isInView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.3, delay: 0.3 + index * 0.05 }}
                  className="border-b border-gray-800 hover:bg-gray-800/30 transition-colors"
                >
                  <td className="py-4 px-4 text-gray-300">{row.feature}</td>
                  <td className="py-4 px-4 text-center bg-indigo-500/10"><Cell value={row.powerSpawn} /></td>
                  <td className="py-4 px-4 text-center"><Cell value={row.autoGen} /></td>
                  <td className="py-4 px-4 text-center"><Cell value={row.crewAI} /></td>
                  <td className="py-4 px-4 text-center"><Cell value={row.langGraph} /></td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="text-center text-gray-500 text-sm mt-6"
        >
          Closest competitor: claude-flow (1k stars) — but Claude-only, no cross-model support
        </motion.p>
      </div>
    </section>
  )
}
