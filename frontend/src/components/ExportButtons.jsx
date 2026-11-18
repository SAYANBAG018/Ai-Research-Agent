
import { Download, FileText, FileType2 } from 'lucide-react'
import { downloadUrl } from '../api'

export default function ExportButtons({ job }) {
  const markdownPath = job?.markdown_file
  const pdfPath = job?.pdf_file

  const buttonClass =
    'inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold transition'

  return (
    <div className="flex flex-wrap gap-2">
      <a
        href={markdownPath ? downloadUrl(markdownPath, 'markdown') : undefined}
        aria-disabled={!markdownPath}
        onClick={(event) => {
          if (!markdownPath) event.preventDefault()
        }}
        className={`${buttonClass} ${
          markdownPath
            ? 'border border-slate-200 bg-white text-slate-600 hover:border-indigo-200 hover:text-indigo-700'
            : 'pointer-events-none border border-slate-200 text-slate-300'
        }`}
      >
        <FileText size={15} />
        Markdown
        <Download size={13} />
      </a>

      <a
        href={pdfPath ? downloadUrl(pdfPath, 'pdf') : undefined}
        aria-disabled={!pdfPath}
        onClick={(event) => {
          if (!pdfPath) event.preventDefault()
        }}
        className={`${buttonClass} ${
          pdfPath
            ? 'bg-slate-900 text-white hover:bg-slate-700'
            : 'pointer-events-none bg-slate-100 text-slate-300'
        }`}
      >
        <FileType2 size={15} />
        PDF
        <Download size={13} />
      </a>
    </div>
  )
}
