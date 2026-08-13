import { useMemo } from "react";
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  QuestionMarkCircleIcon,
  PhotoIcon,
  ShieldCheckIcon,
  MegaphoneIcon,
} from "@heroicons/react/24/outline";
import { useAppSelector } from "../store/hooks";
import { IMessage } from "../store";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const lastOf = (messages: IMessage[], type: string): any | null => {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].type === type) return messages[i].data ?? null;
  }
  return null;
};

const statusStyle = (status: string) => {
  switch ((status || "").toLowerCase()) {
    case "supported":
      return "bg-green-100 text-green-800 ring-green-200";
    case "unsupported":
      return "bg-red-100 text-red-800 ring-red-200";
    case "mixed":
      return "bg-amber-100 text-amber-800 ring-amber-200";
    default:
      return "bg-purple-100 text-purple-800 ring-purple-200";
  }
};

const claimIcon = (status: string) => {
  switch ((status || "").toLowerCase()) {
    case "supported":
      return <CheckCircleIcon className="w-5 h-5 text-green-600 shrink-0" />;
    case "unsupported":
      return <ExclamationTriangleIcon className="w-5 h-5 text-red-600 shrink-0" />;
    default:
      return <QuestionMarkCircleIcon className="w-5 h-5 text-amber-500 shrink-0" />;
  }
};

export const StudioExtras = () => {
  const messages = useAppSelector((state) => state.message);

  const design = useMemo(() => lastOf(messages, "designer"), [messages]);
  const factcheck = useMemo(() => lastOf(messages, "factchecker"), [messages]);
  const repurposed = useMemo(() => lastOf(messages, "repurposer"), [messages]);

  if (!design && !factcheck && !repurposed) {
    return (
      <div className="rounded-2xl ring-1 ring-purple-100 bg-white/60 p-5 text-sm text-purple-500/70">
        <div className="flex items-center gap-2 mb-1 text-purple-700 font-medium">
          <PhotoIcon className="w-5 h-5" />
          Insights
        </div>
        The illustrator, fact-checker and repurposer results will appear here once an
        article is generated.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Illustrator */}
      {design?.image && (
        <div className="rounded-2xl overflow-hidden ring-1 ring-purple-100 bg-white shadow-sm">
          <img src={design.image} alt={design.prompt || "Article illustration"} className="w-full object-cover" />
          <div className="flex items-center gap-2 px-4 py-2 text-xs text-purple-700/70 bg-purple-50/60">
            <PhotoIcon className="w-4 h-4" />
            <span className="truncate">{design.prompt}</span>
          </div>
        </div>
      )}

      {/* Fact-checker */}
      {factcheck && (
        <div className="rounded-2xl ring-1 ring-purple-100 bg-white shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheckIcon className="w-5 h-5 text-purple-700" />
            <h3 className="text-lg font-semibold text-purple-900">Fact check</h3>
            <span className={`ml-auto text-xs font-medium px-2.5 py-1 rounded-full ring-1 ${statusStyle(factcheck.status)}`}>
              {factcheck.status || "reviewed"}
            </span>
          </div>
          {factcheck.summary && <p className="text-sm text-gray-600 mb-3">{factcheck.summary}</p>}
          <ul className="space-y-2">
            {(factcheck.claims || []).map(
              (c: { claim: string; status: string; source?: string }, i: number) => (
                <li key={`claim_${i}`} className="flex items-start gap-2 text-sm">
                  {claimIcon(c.status)}
                  <span className="text-gray-800">
                    {c.claim}
                    {c.source && (
                      <a href={c.source} target="_blank" rel="noreferrer" className="ml-1 text-purple-600 underline">
                        source
                      </a>
                    )}
                  </span>
                </li>
              )
            )}
          </ul>
        </div>
      )}

      {/* Repurposer */}
      {repurposed && (
        <div className="rounded-2xl ring-1 ring-purple-100 bg-white shadow-sm p-5">
          <div className="flex items-center gap-2 mb-3">
            <MegaphoneIcon className="w-5 h-5 text-purple-700" />
            <h3 className="text-lg font-semibold text-purple-900">Repurpose &amp; share</h3>
          </div>
          <div className="grid gap-3">
            {repurposed.linkedin && (
              <div className="rounded-xl bg-purple-50/70 ring-1 ring-purple-100 p-3">
                <div className="text-xs font-semibold text-purple-700 mb-1">LinkedIn</div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{repurposed.linkedin}</p>
              </div>
            )}
            {Array.isArray(repurposed.x_thread) && repurposed.x_thread.length > 0 && (
              <div className="rounded-xl bg-purple-50/70 ring-1 ring-purple-100 p-3">
                <div className="text-xs font-semibold text-purple-700 mb-1">X thread</div>
                <ol className="text-sm text-gray-700 space-y-2 list-decimal list-inside">
                  {repurposed.x_thread.map((t: string, i: number) => (
                    <li key={`x_${i}`}>{t}</li>
                  ))}
                </ol>
              </div>
            )}
            {repurposed.newsletter && (
              <div className="rounded-xl bg-purple-50/70 ring-1 ring-purple-100 p-3">
                <div className="text-xs font-semibold text-purple-700 mb-1">Newsletter</div>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{repurposed.newsletter}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudioExtras;
