
import { ArrowUpRight, Sparkles } from 'lucide-react'

const examples = [
  'How is generative AI changing healthcare?',
  'The global transition to renewable energy',
  'Recent advances in battery technology',
]

export default function ResearchForm({
  topic,
  setTopic,
  onSubmit,
  loading,
}) {
  const characterCount = topic.length
  const isValid = topic.trim().length >= 3
  const isTooLong = characterCount > 500

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-7">
      {/* Heading */}
      <div className="mb-5 flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-indigo-50 text-indigo-600">
          <Sparkles size={19} />
        </div>

        <div>
          <h2 className="font-display text-lg font-extrabold text-ink">
            Start a research project
          </h2>

          <p className="text-sm text-slate-500">
            Give your research agents a topic to investigate.
          </p>
        </div>
      </div>

      <form onSubmit={onSubmit}>
        {/* Topic label */}
        <label
          htmlFor="topic"
          className="mb-2 block text-xs font-bold uppercase tracking-[.12em] text-slate-500"
        >
          Research topic
        </label>

        {/* Topic input */}
        <textarea
          id="topic"
          name="topic"
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          placeholder="e.g. The impact of AI on education over the next decade..."
          rows={4}
          maxLength={500}
          disabled={loading}
          required
          minLength={3}
          aria-describedby="topic-help topic-count"
          className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 text-sm leading-6 text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-indigo-300 focus:bg-white focus:ring-4 focus:ring-indigo-50 disabled:cursor-not-allowed disabled:opacity-60"
        />

        {/* Input helper */}
        <div
          className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs"
        >
          <span id="topic-help" className="text-slate-400">
            Be specific for more focused findings.
          </span>

          <span
            id="topic-count"
            className={
              isTooLong
                ? 'font-semibold text-rose-600'
                : 'text-slate-400'
            }
          >
            {characterCount}/500
          </span>
        </div>

        {/* Example topics */}
        <div className="mt-5">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[.13em] text-slate-400">
            Try an example
          </p>

          <div className="flex flex-wrap gap-2">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                disabled={loading}
                onClick={() => setTopic(example)}
                className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-500 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-slate-400">
            {loading
              ? 'Your AI research agents are working. Please wait...'
              : 'Your research may take a few minutes to complete.'}
          </p>

          <button
            type="submit"
            disabled={loading || !isValid || isTooLong}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:-translate-y-0.5 hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Research running...
              </>
            ) : (
              <>
                Start research
                <ArrowUpRight size={16} />
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  )
}
