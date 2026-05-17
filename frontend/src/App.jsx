import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CandidateDetail from './pages/CandidateDetail'
import LinkedInCallback from './pages/LinkedInCallback'
import LandingPage from './pages/LandingPage'

function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const isActive = (path) => location.pathname === path

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'bg-[#0F172A]/95 backdrop-blur-md shadow-lg shadow-black/20' : 'bg-transparent'}`}>
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-1.5 shadow-lg shadow-blue-500/30 group-hover:shadow-blue-500/50 transition-shadow">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-lg font-bold text-white tracking-tight">TalentRank <span className="text-blue-400">AI</span></span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {[['/', 'Home'], ['/dashboard', 'Dashboard'], ['/about', 'About']].map(([path, label]) => (
              <Link key={path} to={path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${isActive(path) ? 'bg-white/10 text-white' : 'text-slate-300 hover:text-white hover:bg-white/5'}`}>
                {label}
              </Link>
            ))}
            <Link to="/dashboard"
              className="ml-3 px-4 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-400 hover:to-indigo-500 transition-all shadow-lg shadow-blue-500/25">
              View Candidates →
            </Link>
          </nav>

          {/* Mobile menu button */}
          <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden text-slate-300 hover:text-white">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden bg-[#0F172A]/95 backdrop-blur-md border-t border-white/10 py-4 space-y-1">
            {[['/', 'Home'], ['/dashboard', 'Dashboard'], ['/about', 'About']].map(([path, label]) => (
              <Link key={path} to={path} onClick={() => setMenuOpen(false)}
                className="block px-4 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/5 rounded-lg">
                {label}
              </Link>
            ))}
          </div>
        )}
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-[#0F172A] border-t border-white/10 mt-auto">
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg p-1.5">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-sm font-bold text-white">TalentRank <span className="text-blue-400">AI</span></span>
          </div>
          <p className="text-sm text-slate-500">© 2026 TalentRank AI. Automated Candidate Enrichment.</p>
          <div className="flex gap-6 text-sm text-slate-500">
            <Link to="/" className="hover:text-slate-300 transition-colors">Home</Link>
            <Link to="/dashboard" className="hover:text-slate-300 transition-colors">Dashboard</Link>
            <Link to="/about" className="hover:text-slate-300 transition-colors">About</Link>
          </div>
        </div>
      </div>
    </footer>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-[#F8FAFF] flex flex-col">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={
              <div className="pt-24 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
                <Dashboard />
              </div>
            } />
            <Route path="/candidate/:id" element={
              <div className="pt-24 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
                <CandidateDetail />
              </div>
            } />
            <Route path="/about" element={
              <div className="pt-24 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
                <AboutPage />
              </div>
            } />
            <Route path="/linkedin-success" element={
              <div className="pt-24 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
                <LinkedInCallback />
              </div>
            } />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  )
}

function AboutPage() {
  const features = [
    { icon: '🤖', title: 'AI-Powered Profiling', desc: 'Groq LLM analyzes every candidate and generates a structured executive summary, skill tags, and domain classification automatically.' },
    { icon: '🐙', title: 'GitHub Analysis', desc: 'We scan public repositories, count stars, detect primary languages, and surface the top projects that define a developer\'s real-world output.' },
    { icon: '🔗', title: 'LinkedIn Integration', desc: 'OAuth-based LinkedIn connection pulls verified profile data — name, headline, and profile picture — directly from the source.' },
    { icon: '📊', title: 'Google Sheets Ingestion', desc: 'Candidates submit via a simple Google Form. Our poller reads the sheet every 5 minutes and automatically queues new applicants for enrichment.' },
    { icon: '⚡', title: 'Real-time Processing', desc: 'A background job queue processes candidates asynchronously. The dashboard refreshes to show results as soon as profiles are ready.' },
    { icon: '🔍', title: 'Skill & Domain Filtering', desc: 'Filter candidates by specific skills or tech domains like Frontend, ML/AI, DevOps, and more to surface the right talent instantly.' },
  ]

  const stack = ['FastAPI', 'PostgreSQL', 'SQLAlchemy', 'Alembic', 'React', 'Vite', 'TailwindCSS', 'Docker', 'Groq LLM', 'asyncpg', 'APScheduler', 'httpx']

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-extrabold text-[#0F172A] tracking-tight mb-4">About TalentRank AI</h1>
        <p className="text-lg text-slate-500 max-w-2xl mx-auto">An automated talent intelligence platform that enriches candidate profiles using AI, GitHub data, and LinkedIn — so recruiters can focus on people, not paperwork.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-16">
        {features.map((f, i) => (
          <div key={i} className="bg-white rounded-2xl p-6 border border-slate-100 shadow-sm hover:shadow-md transition-shadow">
            <div className="text-3xl mb-3">{f.icon}</div>
            <h3 className="font-bold text-[#0F172A] mb-2">{f.title}</h3>
            <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>

      <div className="bg-[#0F172A] rounded-2xl p-8 text-center">
        <h2 className="text-xl font-bold text-white mb-6">Built With</h2>
        <div className="flex flex-wrap justify-center gap-3">
          {stack.map(s => (
            <span key={s} className="px-3 py-1.5 rounded-full text-sm font-medium bg-white/10 text-slate-300 border border-white/10">{s}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App
