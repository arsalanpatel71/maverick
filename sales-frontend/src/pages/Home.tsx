import { Link } from "react-router-dom";

const features = [
  { icon: "🧠", title: "Multi-Provider LLM", desc: "Google, OpenAI, Anthropic, Perplexity — swap any time.", border: "border-accent-light/60" },
  { icon: "📚", title: "RAG Pipeline",       desc: "Qdrant-backed vector search with 4 retrieval strategies.", border: "border-accent-light/60" },
  { icon: "🔍", title: "Real-time Tracing",  desc: "WebSocket traces show every step — memory, RAG, LLM.", border: "border-accent-light/60" },
];

export default function Home() {
  return (
    <div className="h-full flex flex-col overflow-y-auto scrollbar-thin">
      <div className="flex-1 flex flex-col items-center justify-center px-8 py-12 text-center gap-10">

        <div className="flex flex-col items-center gap-5">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-accent-faint border border-accent-light/40 flex items-center justify-center text-4xl shadow-card">
              🤖
            </div>
            <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-emerald-400 border-2 border-bg" />
          </div>
          <div>
            <h1 className="type-h1 mb-3">Maverick</h1>
            <p className="type-body-lg max-w-md">
              Build, deploy and observe intelligent agents with RAG, memory, and real-time tracing.
            </p>
          </div>
        </div>

        <div className="flex gap-3 flex-wrap justify-center">
          <Link to="/agents" className="px-5 py-2.5 bg-accent hover:bg-accent-muted text-white rounded-lg font-medium text-sm transition-colors shadow-sm">
            View Agents →
          </Link>
          <Link to="/rags" className="px-5 py-2.5 bg-surface hover:bg-surface-alt text-slate-700 rounded-lg font-medium text-sm transition-colors border border-border">
            View RAGs
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl w-full">
          {features.map((f) => (
            <div key={f.title} className={`bg-surface border ${f.border} rounded-xl p-5 text-left shadow-card hover:shadow-md transition-shadow`}>
              <div className="text-2xl mb-3">{f.icon}</div>
              <div className="type-h4 mb-1">{f.title}</div>
              <div className="type-body-sm">{f.desc}</div>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
