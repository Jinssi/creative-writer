import { useMemo } from "react";
import {
  BeakerIcon,
  AcademicCapIcon,
  PencilSquareIcon,
  ClipboardDocumentCheckIcon,
  ShieldCheckIcon,
  PhotoIcon,
  MegaphoneIcon,
  CheckCircleIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useAppSelector } from "../store/hooks";
import { IMessage } from "../store";

type AgentDef = {
  type: IMessage["type"];
  name: string;
  desc: string;
  icon: (cls: string) => JSX.Element;
};

// The order agents run in the orchestrator (each carries the -CW workload suffix).
const PIPELINE: AgentDef[] = [
  { type: "researcher", name: "Researcher", desc: "Finds & cites web sources", icon: (c) => <BeakerIcon className={c} /> },
  { type: "marketing", name: "References", desc: "Gathers reference material", icon: (c) => <AcademicCapIcon className={c} /> },
  { type: "writer", name: "Writer", desc: "Drafts the article", icon: (c) => <PencilSquareIcon className={c} /> },
  { type: "editor", name: "Editor", desc: "Reviews & gives feedback", icon: (c) => <ClipboardDocumentCheckIcon className={c} /> },
  { type: "factchecker", name: "Fact-checker", desc: "Verifies claims vs sources", icon: (c) => <ShieldCheckIcon className={c} /> },
  { type: "designer", name: "Illustrator", desc: "Creates a hero image", icon: (c) => <PhotoIcon className={c} /> },
  { type: "repurposer", name: "Repurposer", desc: "Social & newsletter posts", icon: (c) => <MegaphoneIcon className={c} /> },
];

const isComplete = (messages: IMessage[], type: string): boolean =>
  messages.some(
    (m) =>
      m.type === type &&
      m.data &&
      m.data.start !== true &&
      (type !== "writer" || m.data.complete === true)
  );

export const AgentsPanel = () => {
  const messages = useAppSelector((state) => state.message);

  const { statuses, active } = useMemo(() => {
    const started = messages.length > 0;
    const done = PIPELINE.map((a) => isComplete(messages, a.type));
    const allDone = done.every(Boolean);
    // The active agent is the first not-yet-done step once work has started.
    const activeIndex = started && !allDone ? done.findIndex((d) => !d) : -1;
    const statuses = done.map((d, i): "done" | "working" | "waiting" =>
      d ? "done" : i === activeIndex ? "working" : "waiting"
    );
    return { statuses, active: activeIndex };
  }, [messages]);

  return (
    <div className="rounded-2xl bg-white/70 ring-1 ring-purple-100 shadow-sm p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm font-semibold text-purple-900">Agent pipeline</span>
        <span className="text-xs text-purple-500/70">· Microsoft Agent Framework · Foundry</span>
        {active >= 0 && (
          <span className="ml-auto flex items-center gap-1 text-xs text-purple-600">
            <ArrowPathIcon className="w-4 animate-spin" /> working…
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-2">
        {PIPELINE.map((a, i) => {
          const status = statuses[i];
          const tone =
            status === "done"
              ? "bg-green-50 ring-green-200"
              : status === "working"
              ? "bg-purple-50 ring-purple-300"
              : "bg-white/60 ring-purple-100";
          const iconColor =
            status === "done" ? "text-green-600" : status === "working" ? "text-purple-600" : "text-purple-300";
          return (
            <div key={a.type} className={`relative rounded-xl ring-1 ${tone} p-2.5 flex flex-col gap-1`}>
              <div className="flex items-center justify-between">
                {a.icon(`w-5 h-5 ${iconColor}`)}
                {status === "done" ? (
                  <CheckCircleIcon className="w-4 h-4 text-green-600" />
                ) : status === "working" ? (
                  <ArrowPathIcon className="w-4 h-4 text-purple-500 animate-spin" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-purple-200" />
                )}
              </div>
              <div className="text-xs font-semibold text-purple-900 leading-tight">{a.name}</div>
              <div className="text-[11px] text-purple-500/80 leading-tight">{a.desc}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AgentsPanel;
