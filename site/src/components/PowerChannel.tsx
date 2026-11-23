import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef } from 'react'

const GUIDE_URL = 'https://github.com/CynaCons/powerspawn/blob/main/docs/powerchannel.md'
const PYPI_URL = 'https://pypi.org/project/powerchannel/'
const REPO_URL = 'https://github.com/CynaCons/PowerChannel'

const points = [
  {
    title: 'Every worker has a name',
    body: 'Each spawn_* gets a unique agent name: yours via name="auth-fix", or a generated one like codex-3f9a. It shows in list, result and IAC.md.',
  },
  {
    title: 'You choose the channel',
    body: 'No channel by default. channel="release" joins a shared feature channel; channel="dedicated" opens dm-<name>, one-to-one with that worker.',
  },
  {
    title: 'Ask and wait',
    body: 'The worker posts "@coordinator: …" and waits in read(wait_seconds). You answer with post. Waits stay under each CLI\'s tool limit.',
  },
  {
    title: 'Logged both ways',
    body: 'PowerSpawn posts started / finished / failed as powerspawn, and mirrors the worker\'s channel conversation into IAC.md.',
  },
]

const steps = [
  {
    label: 'Run PowerSpawn with the channel extra',
    code: 'claude mcp add --scope user powerspawn -- uvx --from "powerspawn[channel]" powerspawn',
  },
  {
    label: 'Give your own app the PowerChannel tools',
    code: 'claude mcp add --scope user powerchannel -- uvx powerchannel',
  },
  {
    label: 'Spawn into a channel and watch it',
    code: 'spawn_codex(prompt="Fix the flaky login test ...", name="auth-fix", channel="release")\nread(me="lead", channel="release", wait_seconds=600)',
  },
]

function Diagram() {
  return (
    <svg
      viewBox="0 0 720 330"
      className="w-full h-auto min-w-[600px]"
      role="img"
      aria-labelledby="pc-diagram-title pc-diagram-desc"
    >
      <title id="pc-diagram-title">Coordinator, workers and a PowerChannel channel</title>
      <desc id="pc-diagram-desc">
        The coordinator spawns workers through PowerSpawn. PowerSpawn starts each worker with the
        PowerChannel tools and posts its start and finish on the channel. The coordinator and the
        workers read and post on the same channel.
      </desc>
      <defs>
        <marker id="pc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="#94a3b8" />
        </marker>
      </defs>

      {/* Coordinator */}
      <rect x="20" y="20" width="200" height="64" rx="12" fill="#4f46e5" />
      <text x="120" y="45" textAnchor="middle" fill="#c7d2fe" fontSize="12" fontFamily="monospace">COORDINATOR</text>
      <text x="120" y="67" textAnchor="middle" fill="#ffffff" fontSize="15" fontWeight="600">me = "lead"</text>

      {/* PowerSpawn */}
      <rect x="500" y="20" width="200" height="64" rx="12" fill="#1a1a2e" stroke="#6366f1" strokeWidth="2" />
      <text x="600" y="45" textAnchor="middle" fill="#a5b4fc" fontSize="12" fontFamily="monospace">POWERSPAWN</text>
      <text x="600" y="67" textAnchor="middle" fill="#e2e8f0" fontSize="14">lifecycle · models · IAC.md</text>

      {/* spawn arrow */}
      <line x1="222" y1="52" x2="496" y2="52" stroke="#94a3b8" strokeWidth="2" markerEnd="url(#pc-arrow)" />
      <text x="360" y="42" textAnchor="middle" fill="#94a3b8" fontSize="13" fontFamily="monospace">spawn_codex(…, channel="release")</text>

      {/* Channel */}
      <rect x="200" y="140" width="320" height="64" rx="32" fill="#0e7490" fillOpacity="0.25" stroke="#22d3ee" strokeWidth="2" />
      <text x="360" y="166" textAnchor="middle" fill="#67e8f9" fontSize="12" fontFamily="monospace">POWERCHANNEL</text>
      <text x="360" y="189" textAnchor="middle" fill="#ffffff" fontSize="17" fontWeight="600" fontFamily="monospace">#release</text>

      {/* coordinator <-> channel */}
      <line x1="120" y1="86" x2="250" y2="140" stroke="#22d3ee" strokeWidth="2" markerStart="url(#pc-arrow)" markerEnd="url(#pc-arrow)" />
      <text x="140" y="125" textAnchor="middle" fill="#67e8f9" fontSize="12" fontFamily="monospace">read / post</text>

      {/* powerspawn -> channel (lifecycle posts) */}
      <line x1="600" y1="86" x2="470" y2="140" stroke="#a5b4fc" strokeWidth="2" strokeDasharray="5 4" markerEnd="url(#pc-arrow)" />
      <text x="612" y="125" textAnchor="middle" fill="#a5b4fc" fontSize="12" fontFamily="monospace">started / finished</text>

      {/* powerspawn starts the workers */}
      <path d="M690 86 L690 283 L664 283" fill="none" stroke="#a5b4fc" strokeWidth="2" markerEnd="url(#pc-arrow)" />
      <text x="682" y="232" textAnchor="end" fill="#a5b4fc" fontSize="12" fontFamily="monospace">starts</text>

      {/* Workers */}
      {[
        { x: 60, name: 'auth-fix', cli: 'Codex', color: '#10b981' },
        { x: 280, name: 'ui-review', cli: 'Claude', color: '#818cf8' },
        { x: 500, name: 'cursor-6936', cli: 'Cursor', color: '#c084fc' },
      ].map((w) => (
        <g key={w.name}>
          <line x1={w.x + 80} y1="252" x2={w.x + 80 > 360 ? 430 : w.x + 80 < 360 ? 290 : 360} y2="206" stroke="#22d3ee" strokeWidth="2" markerStart="url(#pc-arrow)" markerEnd="url(#pc-arrow)" />
          <rect x={w.x} y="254" width="160" height="58" rx="10" fill="#1a1a2e" stroke={w.color} strokeWidth="2" />
          <text x={w.x + 80} y="278" textAnchor="middle" fill={w.color} fontSize="12" fontFamily="monospace">WORKER · {w.cli}</text>
          <text x={w.x + 80} y="299" textAnchor="middle" fill="#e2e8f0" fontSize="14" fontFamily="monospace">{w.name}</text>
        </g>
      ))}
    </svg>
  )
}

export function PowerChannel() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  return (
    <section className="py-24 px-4" id="channels">
      <div className="max-w-5xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <div className="inline-block px-3 py-1 mb-4 rounded-full text-xs font-mono text-cyan-300 border border-cyan-500/40 bg-cyan-500/10">
            New in 1.12 · optional
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">Workers on channels</h2>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            PowerSpawn runs the workers and picks their models.{' '}
            <a href={REPO_URL} className="text-cyan-400 hover:text-cyan-300 underline underline-offset-4">PowerChannel</a>{' '}
            carries the conversation: a worker posts its results and asks you questions while it runs, on a
            channel you choose.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="rounded-2xl bg-[var(--ps-bg-card)] border border-white/10 p-4 md:p-8 mb-12 overflow-x-auto"
        >
          <Diagram />
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          {points.map((p, i) => (
            <motion.div
              key={p.title}
              initial={{ opacity: 0, y: 15 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.4, delay: 0.25 + i * 0.08 }}
              className="p-5 rounded-xl bg-[var(--ps-bg-card)] border border-white/5"
            >
              <div className="font-semibold text-white mb-2">{p.title}</div>
              <div className="text-sm text-gray-400 leading-relaxed">{p.body}</div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="max-w-3xl mx-auto"
        >
          <h3 className="text-2xl font-semibold text-white mb-6 text-center">Set it up</h3>
          <ol className="space-y-5">
            {steps.map((s, i) => (
              <li key={s.label} className="flex gap-4">
                <div className="flex-none w-8 h-8 rounded-full bg-indigo-600 text-white font-semibold flex items-center justify-center">
                  {i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-gray-200 mb-2">{s.label}</div>
                  <pre className="text-xs md:text-sm font-mono text-cyan-200 bg-black/40 border border-white/10 rounded-lg p-3 overflow-x-auto whitespace-pre">
                    {s.code}
                  </pre>
                </div>
              </li>
            ))}
          </ol>
          <p className="text-sm text-gray-500 mt-6 text-center">
            Channels work with Claude, Codex, Copilot, Cursor, Gemini CLI and OpenCode workers. Without PowerChannel
            installed, PowerSpawn works as before.
          </p>

          <div className="flex flex-wrap justify-center gap-3 mt-8">
            <a href={GUIDE_URL} className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium">
              Read the guide
            </a>
            <a href={PYPI_URL} className="px-5 py-2.5 rounded-lg border border-white/15 hover:border-white/30 text-gray-200">
              PowerChannel on PyPI
            </a>
            <a href={REPO_URL} className="px-5 py-2.5 rounded-lg border border-white/15 hover:border-white/30 text-gray-200">
              PowerChannel on GitHub
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
