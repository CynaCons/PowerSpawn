import { Hero } from './components/Hero'
import { Features } from './components/Features'
import { HowItWorks } from './components/HowItWorks'
import { Comparison } from './components/Comparison'
import { Roadmap } from './components/Roadmap'
import { QuickStart } from './components/QuickStart'
import { Footer } from './components/Footer'

function App() {
  return (
    <div className="min-h-screen bg-[var(--ps-bg-dark)]">
      <Hero />
      <Features />
      <HowItWorks />
      <Comparison />
      <Roadmap />
      <QuickStart />
      <Footer />
    </div>
  )
}

export default App
