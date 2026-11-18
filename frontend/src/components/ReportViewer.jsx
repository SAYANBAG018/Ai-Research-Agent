
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  FileText,
  MessageSquareText,
  Globe2,
  ExternalLink,
} from 'lucide-react'

const tabs = [
  { id: 'report', label: 'Research report', icon: FileText },
  { id: 'review', label: 'Critic review', icon: MessageSquareText },
  { id: 'sources', label: 'Sources', icon: Globe2 },
]

function MarkdownContent({ children }) {
  const content =
    typeof children === 'string' ? children : ''

  return (
    <div className="prose prose-slate max-w-none prose-headings:font-display prose-headings:font-extrabold prose-headings:tracking-tight prose-a:text-indigo-600 prose-a:no-underline hover:prose-a:underline prose-pre:overflow-x-auto prose-pre:rounded-xl prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-table:text-sm prose-th:bg-slate-50">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || 'No content is available yet.'}
      </ReactMarkdown>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="grid min-h-[330px] place-items-center rounded-2xl border border-dashed border-slate-300 bg-white/70 p-8 text-center">
      <div>
        <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
          <FileText size={22} />
        </div>

        <h3 className="font-display font-bold text-slate-700">
          Your report will appear here
        </h3>

        <p className="mt-1 max-w-xs text-sm text-slate-400">
          Start a research project and the completed report, review,
          and sources will be displayed in this workspace.
        </p>
      </div>
    </div>
  )
}

function SourcesContent({ sources }) {
  if (!Array.isArray(sources) || sources.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        No source validation details are available.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      {sources.map((source, index) => {
        const domain = source?.domain || source?.url || `Source ${index + 1}`
        const warnings = Array.isArray(source?.warnings)
          ? source.warnings
          : []

        return (
          <div
            key={`${domain}-${index}`}
            className="rounded-xl border border-slate-100 p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="break-all text-sm font-bold text-slate-800">
                {domain}
              </p>

              <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-bold text-indigo-700">
                {source?.category || 'Uncategorized'}
                {' · '}
                {source?.score ?? 'N/A'}/10
              </span>
            </div>

            {source?.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline"
              >
                Visit source <ExternalLink size={12} />
              </a>
            )}

            {source?.note && (
              <p className="mt-2 text-xs leading-5 text-slate-500">
                {source.note}
              </p>
            )}

            {warnings.length > 0 && (
              <p className="mt-2 text-xs text-amber-700">
                {warnings.join(' · ')}
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function ReportViewer({ job }) {
  const [tab, setTab] = useState('report')

  if (!job || (!job.report && !job.feedback && !job.sources?.length)) {
    return <EmptyState />
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-4 sm:px-6">
        <div>
          <p className="font-display font-extrabold text-ink">
            Research output
          </p>

          <p className="mt-0.5 text-xs text-slate-400">
            {job.topic || 'Research results'}
          </p>
        </div>

        <div className="flex rounded-xl bg-slate-100 p-1">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition ${
                tab === id
                  ? 'bg-white text-indigo-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Icon size={14} />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-[380px] p-5 sm:p-7">
        {tab === 'report' && (
          <MarkdownContent>
            {job.report}
          </MarkdownContent>
        )}

        {tab === 'review' && (
          <MarkdownContent>
            {job.feedback || 'No critic feedback was returned.'}
          </MarkdownContent>
        )}

        {tab === 'sources' && (
          <SourcesContent sources={job.sources} />
        )}
      </div>
    </section>
  )
}
