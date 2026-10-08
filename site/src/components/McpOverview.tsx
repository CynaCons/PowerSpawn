import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

/** MCP tool surface + current model families (powerspawn.com overview). */

const tools = [
  {
    name: 'spawn_claude',
    kind: 'CLI',
    desc: 'Claude Code agent — full file/shell access via your Claude subscription.',
    models: 'sonnet · opus · haiku · fable (aliases)',
  },
  {
    name: 'spawn_codex',
    kind: 'CLI',
    desc: 'OpenAI Codex agent — GPT‑6 Astra / Sol / Luna family.',
    models: 'astra · sol · luna · gpt-5.6 sol/terra/luna',
  },
  {
    name: 'spawn_cursor',
    kind: 'CLI',
    desc: 'Cursor agent CLI — Composer 2.5 plus Claude, GPT, Gemini and Grok.',
    models: 'composer · opus-5.5 · gpt-5.6 · gemini-3.8-flash · grok-4.7',
  },
  {
    name: 'spawn_grok',
    kind: 'CLI',
    desc: 'Grok Build CLI (primary Grok path) — Grok 4.6 by default.',
    models: 'grok-4.6 (default) · grok-4.7 · grok-4.5',
  },
  {
    name: 'spawn_copilot',
    kind: 'CLI',
    desc: 'GitHub Copilot CLI — GPT, Claude, and Gemini from one tool.',
    models: 'claude-opus-5.5 · claude-sonnet-5.5 · gpt-6 · gemini-3.8-flash · grok-4.7',
  },
  {
    name: 'spawn_gemini_cli',
    kind: 'CLI',
    desc: 'Google Gemini CLI agent with workspace tools.',
    models: 'gemini-3.1-pro · 3.8-flash · flash-lite',
  },
  {
    name: 'spawn_grok_api',
    kind: 'API',
    desc: 'Legacy xAI chat API fallback (text-only; needs XAI_API_KEY).',
    models: 'grok-4.7 (default) · 4.6 · 4.5 · 4.3 · 4.20 · grok-build-0.1',
  },
  {
    name: 'spawn_gemini / spawn_mistral',
    kind: 'API',
    desc: 'Text-response API agents — coordinator applies any edits.',
    models: 'Gemini 3.x · Mistral Large 4 / Medium 3.5 / Small 4',
  },
  {
    name: 'list · wait_for_agents',
    kind: 'Control',
    desc: 'Track running workers and block until the fleet settles.',
    models: '—',
  },
]

const modelFamilies = [
  {
    title: 'Codex — GPT‑6',
    badge: 'Astra · Sol · Luna',
    points: [
      { alias: 'astra', role: 'Most capable — complex, long-horizon work' },
      { alias: 'sol', role: 'Near-Astra quality, balanced default' },
      { alias: 'luna', role: 'Fast / cost-efficient' },
    ],
    note: 'Aliases: astra, sol, luna → gpt-6-*; terra → gpt-5.6-terra. Default: gpt-6-sol.',
  },
  {
    title: 'Grok CLI — Grok Build',
    badge: 'grok-4.6',
    points: [
      { alias: 'grok-4.6', role: 'Default headless Grok Build model' },
      { alias: 'grok-4.7', role: 'Latest xAI frontier model' },
      { alias: 'build / composer', role: 'Legacy names map to the default' },
    ],
    note: 'Requires grok on PATH + grok login. force=true applies edits; false = plan mode.',
  },
]

export function McpOverview() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section className="py-24 px-4" id="mcp">
      <div className="max-w-6xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-14"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-mono mb-4">
            MCP TOOL SURFACE
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">
            MCP Overview
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            One Python MCP server. Spawn CLI and API agents from Claude Code, Cursor,
            Codex, Copilot, Grok Build, and more — with full model aliases.
          </p>
        </motion.div>

        {/* Model families highlight */}
        <div className="grid md:grid-cols-2 gap-6 mb-14">
          {modelFamilies.map((fam, i) => (
            <motion.div
              key={fam.title}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: 0.1 + i * 0.1 }}
              className="p-6 rounded-xl bg-gradient-to-br from-indigo-900/40 to-[var(--ps-bg-card)] border border-indigo-500/30"
            >
              <div className="flex items-center justify-between gap-3 mb-4">
                <h3 className="text-lg font-semibold text-white">{fam.title}</h3>
                <span className="text-xs font-mono px-2 py-1 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  {fam.badge}
                </span>
              </div>
              <ul className="space-y-2 mb-4">
                {fam.points.map((p) => (
                  <li key={p.alias} className="flex gap-3 text-sm">
                    <code className="text-cyan-300 font-mono shrink-0">{p.alias}</code>
                    <span className="text-gray-400">{p.role}</span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-500 leading-relaxed">{fam.note}</p>
            </motion.div>
          ))}
        </div>

        {/* Tools table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="overflow-x-auto rounded-xl border border-gray-800 bg-[var(--ps-bg-card)]"
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="px-4 py-3 font-medium">Tool</th>
                <th className="px-4 py-3 font-medium">Mode</th>
                <th className="px-4 py-3 font-medium">What it does</th>
                <th className="px-4 py-3 font-medium">Models</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t) => (
                <tr key={t.name} className="border-b border-gray-800/80 last:border-0 hover:bg-white/5">
                  <td className="px-4 py-3 font-mono text-indigo-300 whitespace-nowrap">{t.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded border ${
                        t.kind === 'CLI'
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : t.kind === 'API'
                            ? 'bg-orange-500/10 text-orange-300 border-orange-500/30'
                            : 'bg-gray-500/10 text-gray-300 border-gray-500/30'
                      }`}
                    >
                      {t.kind}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{t.desc}</td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">{t.models}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        <p className="mt-6 text-center text-sm text-gray-500">
          Models are defined in{' '}
          <code className="text-gray-400">models.json</code> and exposed as MCP tool enums.
          Run unit tests with <code className="text-gray-400">pytest tests/</code>.
        </p>
      </div>
    </section>
  )
}
