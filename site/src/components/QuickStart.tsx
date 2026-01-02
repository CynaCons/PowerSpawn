import { motion } from 'framer-motion'
import { useInView } from 'framer-motion'
import { useRef, useState } from 'react'

const codeSnippets = {
  install: `# Add PowerSpawn to your project
git submodule add https://github.com/CynaCons/PowerSpawn.git powerspawn

# Install dependencies
pip install mcp`,

  config: `# For Claude Code, create TWO files:

# FILE 1: .mcp.json (project root)
{
  "$schema": "https://raw.githubusercontent.com/anthropics/mcp/main/schema/mcp.json",
  "mcpServers": {
    "agents": {
      "command": "python",
      "args": ["powerspawn/mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}

# FILE 2: .claude/settings.local.json
{
  "permissions": { "allow": [], "deny": [], "ask": [] },
  "enabledMcpjsonServers": ["agents"],
  "enableAllProjectMcpServers": true
}

# Then restart Claude Code to load the MCP server!

# For API agents, set env vars or create api_keys.json:
#   export XAI_API_KEY=...     # for Grok
#   export GEMINI_API_KEY=...  # for Gemini
#   export MISTRAL_API_KEY=... # for Mistral`,

  usage: `User: "Review the auth module and run the tests.
        Get a second opinion from Grok on the architecture."

Coordinator thinking...

spawn_claude("Review authentication module for security issues")
→ Agent #a1b2 running (sonnet) [CLI]

spawn_codex("Run npm test, report any failures")
→ Agent #c3d4 running (gpt-5.1) [CLI]

# Waiting for CLI agents to complete...
wait_for_agents()
✓ Claude: Found 2 potential issues
✓ Codex: All 47 tests passing

# Now getting API agent analysis
spawn_grok("Analyze the auth architecture, suggest improvements")
→ Agent #e5f6 running (grok-3) [API]

wait_for_agents()
✓ Grok: 3 architectural recommendations

# Coordinator synthesizes results and presents to user`,
}

function CodeBlock({ code }: { code: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group">
      <pre className="bg-[#1e1e2e] rounded-lg p-4 overflow-x-auto border border-gray-700">
        <code className="text-sm font-mono text-gray-300">{code}</code>
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded opacity-0 group-hover:opacity-100 transition-opacity"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

export function QuickStart() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  const steps = [
    { title: '1. Install', code: codeSnippets.install },
    { title: '2. Configure', code: codeSnippets.config },
    { title: '3. Use', code: codeSnippets.usage },
  ]

  return (
    <section className="py-24 px-4 bg-gradient-to-b from-transparent via-indigo-900/5 to-transparent" id="quick-start">
      <div className="max-w-4xl mx-auto">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold text-white mb-4">
            Quick Start
          </h2>
          <p className="text-xl text-gray-400">
            Get up and running in under a minute
          </p>
        </motion.div>

        <div className="space-y-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.2 + index * 0.1 }}
            >
              <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-sm">
                  {index + 1}
                </span>
                {step.title.split('. ')[1]}
              </h3>
              <CodeBlock code={step.code} />
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.6 }}
          className="mt-12 text-center"
        >
          <a
            href="https://github.com/CynaCons/PowerSpawn#readme"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-semibold transition-colors"
          >
            Read Full Documentation →
          </a>
        </motion.div>
      </div>
    </section>
  )
}
