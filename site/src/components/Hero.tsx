import { motion } from 'framer-motion'
import { useState } from 'react'

const terminalLines = [
  { text: '$ claude "Review the authentication module"', delay: 0 },
  { text: '→ Spawning Claude agent (sonnet)...', delay: 0.5, color: 'text-cyan-400' },
  { text: '→ Agent #a3f2 running', delay: 1, color: 'text-green-400' },
  { text: '', delay: 1.2 },
  { text: '$ # Claude is busy? Spawn Codex instead!', delay: 1.5, color: 'text-gray-500' },
  { text: '$ codex "Run the test suite"', delay: 2 },
  { text: '→ Spawning Codex agent...', delay: 2.5, color: 'text-cyan-400' },
  { text: '→ Agent #b7c1 running', delay: 3, color: 'text-green-400' },
  { text: '', delay: 3.2 },
  { text: '✓ Both agents working in parallel!', delay: 3.5, color: 'text-emerald-400' },
]

function AnimatedTerminal() {
  return (
    <div className="bg-[#1e1e2e] rounded-lg border border-gray-700 shadow-2xl overflow-hidden max-w-2xl mx-auto">
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[#181825] border-b border-gray-700">
        <div className="w-3 h-3 rounded-full bg-red-500" />
        <div className="w-3 h-3 rounded-full bg-yellow-500" />
        <div className="w-3 h-3 rounded-full bg-green-500" />
        <span className="ml-4 text-sm text-gray-400 font-mono">powerspawn</span>
      </div>

      {/* Terminal content */}
      <div className="p-4 font-mono text-sm space-y-1 min-h-[280px]">
        {terminalLines.map((line, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: line.delay, duration: 0.3 }}
            className={line.color || 'text-gray-200'}
          >
            {line.text || '\u00A0'}
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button
      onClick={handleCopy}
      className="ml-2 px-2 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

export function Hero() {
  const installCommand = 'git submodule add https://github.com/CynaCons/PowerSpawn.git powerspawn'

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 py-20 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-indigo-900/20 via-transparent to-transparent" />

      {/* Animated background dots */}
      <div className="absolute inset-0 opacity-30">
        {[...Array(50)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-indigo-500 rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
            animate={{
              opacity: [0.2, 0.8, 0.2],
              scale: [1, 1.5, 1],
            }}
            transition={{
              duration: 2 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
          />
        ))}
      </div>

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-sm mb-8"
        >
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          MCP Server for Multi-Agent Orchestration
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-5xl md:text-7xl font-bold mb-6"
        >
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            PowerSpawn
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-xl md:text-2xl text-gray-300 mb-8 max-w-2xl mx-auto"
        >
          Spawn Claude and Codex from one coordinator.
          <br />
          <span className="text-gray-400">Your agents leave a paper trail.</span>
        </motion.p>

        {/* Install command */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex items-center justify-center gap-2 mb-12"
        >
          <code className="px-4 py-3 bg-[var(--ps-bg-card)] rounded-lg border border-gray-700 text-sm md:text-base font-mono text-gray-300">
            {installCommand}
          </code>
          <CopyButton text={installCommand} />
        </motion.div>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16"
        >
          <a
            href="https://github.com/CynaCons/PowerSpawn"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            View on GitHub
          </a>
          <a
            href="#quick-start"
            className="px-8 py-3 border border-gray-600 hover:border-gray-500 rounded-lg font-semibold transition-colors"
          >
            Quick Start →
          </a>
        </motion.div>

        {/* Animated terminal */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
        >
          <AnimatedTerminal />
        </motion.div>
      </div>
    </section>
  )
}
