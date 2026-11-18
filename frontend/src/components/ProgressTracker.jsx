
import {
  Check,
  Circle,
  LoaderCircle,
  XCircle,
} from 'lucide-react'

const steps = [
  ['search', 'Web research', 'Finding relevant information'],
  ['sources', 'Source discovery', 'Collecting source links'],
  ['validation', 'Source screening', 'Reviewing source domains'],
  ['scraping', 'Content extraction', 'Reading source material'],
  ['writing', 'Report drafting', 'Building the research report'],
  ['review', 'Quality review', 'Checking evidence and citations'],
  ['export', 'Export', 'Preparing your files'],
]

export default function ProgressTracker({
  events = [],
  status = 'running',
}) {
  const safeEvents = Array.isArray(events) ? events : []

  const latest = Object.fromEntries(
    safeEvents.map((event) => [event.step, event])
  )

  const finished = status === 'completed'
  const failed = status === 'failed'
  const running = status === 'running'

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-soft sm:p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display font-extrabold text-ink">
            Agent activity
          </h3>

          <p className="mt-1 text-xs text-slate-500">
            Your research workflow, step by step
          </p>
        </div>

        <span
          className={`shrink-0 rounded-full px-3 py-1 text-[11px] font-bold capitalize ${
            finished
              ? 'bg-emerald-50 text-emerald-700'
              : failed
                ? 'bg-rose-50 text-rose-700'
                : 'bg-indigo-50 text-indigo-700'
          }`}
        >
          {status}
        </span>
      </div>

      {/* Workflow steps */}
      <div className="space-y-4">
        {steps.map(([key, title, subtitle], index) => {
          const event = latest[key]

          const stepFailed = event?.status === 'failed'
          const active = event?.status === 'running'

          const done =
            event?.status === 'completed' ||
            (finished && !event)

          const pending = !done && !active && !stepFailed

          return (
            <div className="flex gap-3" key={key}>
              {/* Step icon and connector */}
              <div className="relative flex w-7 shrink-0 justify-center">
                {index < steps.length - 1 && (
                  <span
                    className={`absolute top-7 h-[calc(100%+10px)] w-px ${
                      done ? 'bg-emerald-200' : 'bg-slate-100'
                    }`}
                  />
                )}

                <span
                  className={`relative z-10 grid h-7 w-7 place-items-center rounded-full transition-colors ${
                    done
                      ? 'bg-emerald-100 text-emerald-700'
                      : active
                        ? 'bg-indigo-100 text-indigo-600'
                        : stepFailed
                          ? 'bg-rose-100 text-rose-600'
                          : 'bg-slate-100 text-slate-400'
                  }`}
                >
                  {done && <Check size={14} />}

                  {active && (
                    <LoaderCircle
                      className="animate-spin"
                      size={15}
                    />
                  )}

                  {stepFailed && <XCircle size={15} />}

                  {pending && <Circle size={12} />}
                </span>
              </div>

              {/* Step details */}
              <div className="min-w-0 flex-1 pb-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p
                    className={`text-sm font-semibold ${
                      done
                        ? 'text-emerald-700'
                        : active
                          ? 'text-indigo-700'
                          : stepFailed
                            ? 'text-rose-700'
                            : 'text-slate-400'
                    }`}
                  >
                    {title}
                  </p>

                  {done && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">
                      Completed
                    </span>
                  )}

                  {active && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-600">
                      In progress
                    </span>
                  )}

                  {stepFailed && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-rose-600">
                      Failed
                    </span>
                  )}
                </div>

                <p className="mt-0.5 break-words text-xs leading-5 text-slate-400">
                  {event?.message ||
                    (stepFailed
                      ? 'This stage could not be completed.'
                      : subtitle)}
                </p>
              </div>
            </div>
          )
        })}
      </div>

      {/* Completion message */}
      {finished && (
        <div className="mt-5 flex items-start gap-2 rounded-xl border border-emerald-100 bg-emerald-50 p-3">
          <Check
            size={16}
            className="mt-0.5 shrink-0 text-emerald-600"
          />

          <p className="text-xs leading-5 text-emerald-700">
            All research stages have been marked complete. Your report
            is ready to review.
          </p>
        </div>
      )}

      {/* Running message */}
      {running && (
        <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50 p-3">
          <p className="text-xs leading-5 text-indigo-700">
            Your research pipeline is working. Please wait while the
            agents complete their tasks.
          </p>
        </div>
      )}

      {/* Failure message */}
      {failed && (
        <div className="mt-5 rounded-xl border border-rose-100 bg-rose-50 p-3">
          <p className="text-xs font-bold text-rose-700">
            Research workflow failed
          </p>

          <p className="mt-1 text-xs leading-5 text-rose-600">
            The workflow stopped before completion. Check the error
            details displayed in the main workspace.
          </p>
        </div>
      )}
    </div>
  )
}
