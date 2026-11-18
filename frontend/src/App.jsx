
import { useState } from 'react'
import {
  Activity,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  FlaskConical,
  Layers3,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react'

import ResearchForm from './components/ResearchForm'
import ProgressTracker from './components/ProgressTracker'
import ReportViewer from './components/ReportViewer'
import ExportButtons from './components/ExportButtons'
import { startResearch } from './api'

export default function App() {
  const [topic, setTopic] = useState('')
  const [job, setJob] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  async function handleSubmit(event) {
    event.preventDefault()

    const researchTopic = topic.trim()

    if (researchTopic.length < 3 || loading) return

    setLoading(true)
    setError('')
    setJob(null)
    setEvents([])

    setEvents([
      {
        step: 'search',
        status: 'running',
        message: 'Starting your research pipeline...',
      },
    ])

    try {
      const response = await startResearch(researchTopic)

      if (response?.success === false) {
        throw new Error(response.message || 'Research could not be completed.')
      }

      // FastAPI returns the pipeline result inside response.result.
      const result = response?.result || response

      const report = result?.report || ''
      const feedback = result?.feedback || ''

      if (!report && !feedback) {
        throw new Error(
          'The backend responded, but no report or critic feedback was returned. Check your FastAPI response.'
        )
      }

      const completedJob = {
        ...result,
        id: Date.now().toString(),
        topic: result?.topic || response?.topic || researchTopic,
        report,
        feedback,
        sources: Array.isArray(result?.sources) ? result.sources : [],
        markdown_file: result?.markdown_file || null,
        pdf_file: result?.pdf_file || null,
        status: 'completed',
      }

      setJob(completedJob)

      setEvents([
        {
          step: 'search',
          status: 'completed',
          message: 'Web research completed.',
        },
        {
          step: 'sources',
          status: 'completed',
          message: 'Source discovery completed.',
        },
        {
          step: 'validation',
          status: 'completed',
          message: 'Source screening completed.',
        },
        {
          step: 'scraping',
          status: 'completed',
          message: 'Source extraction completed.',
        },
        {
          step: 'writing',
          status: 'completed',
          message: 'Research report generated.',
        },
        {
          step: 'review',
          status: 'completed',
          message: 'Critic review completed.',
        },
        {
          step: 'export',
          status: 'completed',
          message: 'Report exports are ready.',
        },
      ])
    } catch (requestError) {
      setError(
        requestError?.message ||
          'Something went wrong while running your research.'
      )

      setJob({
        topic: researchTopic,
        status: 'failed',
        error:
          requestError?.message ||
          'An unexpected error occurred.',
      })

      setEvents([
        {
          step: 'search',
          status: 'failed',
          message: 'The research request failed.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const completed = job?.status === 'completed'
  const busy = loading

  return (
    <div className="min-h-screen bg-[#f7f8fc] text-ink">
      <div className="flex min-h-screen">
        {/* Sidebar */}
        <aside
          className={`${
            sidebarOpen ? 'w-[252px]' : 'w-[76px]'
          } hidden shrink-0 flex-col border-r border-slate-200/80 bg-white transition-all duration-300 lg:flex`}
        >
          <div className="flex h-[76px] items-center gap-3 border-b border-slate-100 px-5">
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
              <FlaskConical size={20} />
            </div>

            {sidebarOpen && (
              <div className="min-w-0">
                <p className="font-display text-sm font-extrabold tracking-tight text-ink">
                  Research Studio
                </p>
                <p className="text-[10px] font-semibold uppercase tracking-[.16em] text-slate-400">
                  Multi-agent workspace
                </p>
              </div>
            )}
          </div>

          <div className="flex-1 px-3 py-6">
            {sidebarOpen && (
              <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[.16em] text-slate-400">
                Workspace
              </p>
            )}

            <div className="flex items-center gap-3 rounded-xl bg-indigo-50 px-3 py-3 text-sm font-bold text-indigo-700">
              <Layers3 size={17} />
              <span className={sidebarOpen ? '' : 'sr-only'}>
                Research dashboard
              </span>
            </div>

            <div className="mt-2 flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-400">
              <BookOpen size={17} />
              <span className={sidebarOpen ? '' : 'sr-only'}>
                Research library
              </span>
              {sidebarOpen && (
                <span className="ml-auto rounded-md bg-slate-100 px-1.5 py-0.5 text-[9px]">
                  Soon
                </span>
              )}
            </div>
          </div>

          <div className="border-t border-slate-100 p-4">
            <div className="rounded-xl bg-slate-50 p-3">
              {sidebarOpen ? (
                <>
                  <div className="mb-2 flex items-center gap-2 text-xs font-bold text-slate-700">
                    <ShieldCheck
                      size={15}
                      className="text-emerald-500"
                    />
                    Evidence-first workflow
                  </div>

                  <p className="text-[11px] leading-5 text-slate-400">
                    Sources are screened and extracted before the report is
                    drafted and reviewed.
                  </p>
                </>
              ) : (
                <ShieldCheck
                  size={18}
                  className="mx-auto text-emerald-500"
                />
              )}
            </div>

            <button
              type="button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg py-2 text-xs font-semibold text-slate-400 hover:bg-slate-50 hover:text-slate-700"
            >
              {sidebarOpen ? (
                <>
                  <PanelLeftClose size={15} />
                  Collapse
                </>
              ) : (
                <PanelLeftOpen size={16} />
              )}
            </button>
          </div>
        </aside>

        {/* Main workspace */}
        <main className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200/70 bg-white/85 px-5 backdrop-blur-xl sm:px-8">
            <div className="flex items-center gap-3">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-white lg:hidden">
                <FlaskConical size={18} />
              </div>

              <div>
                <p className="font-display text-sm font-extrabold text-ink">
                  Research workspace
                </p>
                <p className="text-[11px] text-slate-400">
                  Discover insights. Build evidence. Create reports.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                {loading ? 'Research running' : 'Workspace ready'}
              </span>
            </div>
          </header>

          <div className="mx-auto max-w-[1440px] px-4 py-7 sm:px-7 sm:py-9 xl:px-10">
            {/* Hero */}
            <section className="relative mb-7 overflow-hidden rounded-3xl bg-[#171d3b] px-6 py-8 text-white shadow-xl shadow-indigo-950/10 sm:px-9 sm:py-10">
              <div className="hero-orb hero-orb-one" />
              <div className="hero-orb hero-orb-two" />

              <div className="relative z-10 max-w-2xl">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.16em] text-indigo-100">
                  <Sparkles size={12} />
                  AI-powered research system
                </div>

                <h1 className="font-display text-3xl font-extrabold leading-tight tracking-tight sm:text-[40px]">
                  Turn complex questions
                  <br className="hidden sm:block" />
                  into <span className="text-indigo-300">clear research.</span>
                </h1>

                <p className="mt-3 max-w-xl text-sm leading-6 text-indigo-100/75">
                  A team of AI agents searches the web, screens sources,
                  extracts evidence, writes a structured report and reviews
                  its quality.
                </p>

                <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[11px] font-medium text-indigo-100/80">
                  <span className="inline-flex items-center gap-1.5">
                    <Search size={13} />
                    Web discovery
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <ShieldCheck size={13} />
                    Source screening
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <Zap size={13} />
                    Multi-agent review
                  </span>
                </div>
              </div>

              <div className="relative z-10 mt-7 grid max-w-2xl grid-cols-3 gap-2 sm:absolute sm:bottom-9 sm:right-9 sm:mt-0 sm:w-[350px]">
                {[
                  ['01', 'Search'],
                  ['02', 'Synthesize'],
                  ['03', 'Review'],
                ].map(([number, label]) => (
                  <div
                    key={number}
                    className="rounded-xl border border-white/10 bg-white/[.07] p-3 backdrop-blur-sm"
                  >
                    <p className="text-[10px] font-bold tracking-widest text-indigo-300">
                      {number}
                    </p>
                    <p className="mt-1 text-xs font-semibold text-white">
                      {label}
                    </p>
                  </div>
                ))}
              </div>
            </section>

            {/* Overview cards */}
            <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-600">
                  <Activity size={18} />
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Workflow
                  </p>
                  <p className="mt-0.5 text-sm font-bold text-slate-700">
                    7 research stages
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-violet-50 text-violet-600">
                  <BookOpen size={18} />
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Output
                  </p>
                  <p className="mt-0.5 text-sm font-bold text-slate-700">
                    Report + critic review
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-soft">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-600">
                  <Clock3 size={18} />
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Exports
                  </p>
                  <p className="mt-0.5 text-sm font-bold text-slate-700">
                    Markdown and PDF
                  </p>
                </div>
              </div>
            </div>

            {/* Main content */}
            <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(310px,.8fr)]">
              <div className="space-y-6">
                <ResearchForm
                  topic={topic}
                  setTopic={setTopic}
                  onSubmit={handleSubmit}
                  loading={busy}
                />

                {error && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {error}
                  </div>
                )}

                {job?.status === 'failed' && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                    <p className="text-sm font-bold text-rose-800">
                      Research could not be completed
                    </p>
                    <p className="mt-1 whitespace-pre-wrap text-xs leading-5 text-rose-700">
                      {job.error || 'An unexpected error occurred.'}
                    </p>
                    <p className="mt-2 text-[11px] text-rose-600">
                      Check your backend terminal and confirm your API keys
                      and Python dependencies are configured.
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="font-display text-lg font-extrabold text-ink">
                      Your research report
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                      Read the findings, inspect source screening and review
                      the critic feedback.
                    </p>
                  </div>

                  {completed && <ExportButtons job={job} />}
                </div>

                <ReportViewer job={completed ? job : null} />
              </div>

              {/* Activity panel */}
              <div className="space-y-5 xl:sticky xl:top-[96px]">
                {job ? (
                  <ProgressTracker
                    events={events}
                    status={job.status}
                  />
                ) : (
                  <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-soft">
                    <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-indigo-50 text-indigo-600">
                      <Activity size={20} />
                    </div>

                    <h3 className="font-display font-extrabold text-ink">
                      Agent activity
                    </h3>

                    <p className="mt-1 text-sm leading-6 text-slate-500">
                      Once you start a project, your research workflow will
                      appear here.
                    </p>

                    <div className="mt-5 space-y-3">
                      {[
                        'Search the web',
                        'Screen source quality',
                        'Extract article content',
                        'Write the report',
                        'Critically review',
                        'Export your files',
                      ].map((item) => (
                        <div
                          className="flex items-center gap-2 text-xs text-slate-400"
                          key={item}
                        >
                          <span className="h-1.5 w-1.5 rounded-full bg-slate-200" />
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {completed && (
                  <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5">
                    <div className="flex items-center gap-2 text-emerald-700">
                      <CheckCircle2 size={17} />
                      <p className="text-sm font-bold">
                        Research completed
                      </p>
                    </div>

                    <p className="mt-1 text-xs leading-5 text-emerald-700/80">
                      Your report and critic evaluation are ready. Download
                      either format or review the source screening.
                    </p>

                    <button
                      type="button"
                      onClick={() => {
                        setTopic('')
                        setJob(null)
                        setEvents([])
                        setError('')
                        document.querySelector('#topic')?.focus()
                      }}
                      className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-emerald-800 hover:underline"
                    >
                      Start another topic
                      <ArrowRight size={13} />
                    </button>
                  </div>
                )}

                <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft">
                  <p className="text-xs font-bold text-slate-700">
                    Research integrity
                  </p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    Source-domain scores and successful extraction are
                    screening signals, not proof that a claim is true.
                    Always review evidence and citations before relying on
                    a report.
                  </p>
                </div>
              </div>
            </div>

            <footer className="mt-10 flex flex-col justify-between gap-2 border-t border-slate-200/70 pt-5 text-[10px] text-slate-400 sm:flex-row">
              <span>Research Studio · Multi-agent research workspace</span>
              <span>
                Built with React, FastAPI and your Python research pipeline
              </span>
            </footer>
          </div>
        </main>
      </div>
    </div>
  )
}
