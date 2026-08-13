import './app.css';
import { version } from "./version";
import Toolbar from "./components/toolbar";
import Article from "./components/article";
import AgentsPanel from "./components/agents-panel";
import StudioExtras from "./components/studio-extras";
import Task from './components/task';
import ThemeMenu from './components/theme-menu';
import { useTheme } from './theme-context';

function App() {
  const { theme } = useTheme();

  return (
    <div className="cw-desktop h-screen flex flex-col overflow-hidden">
      {/* Desktop menu bar */}
      <div className="cw-menubar shrink-0 flex items-center justify-between px-4 sm:px-6 h-11 backdrop-blur bg-white/40 border-b border-white/40">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center w-6 h-6 rounded-md bg-gradient-to-br from-purple-500 to-fuchsia-500 text-white text-xs font-bold shadow">✎</span>
          <span className="font-semibold text-purple-900">Creative Writer</span>
          <span className="hidden md:inline text-purple-500/80 text-sm">· Studio</span>
        </div>
        <div className="flex items-center gap-3">
          <ThemeMenu />
        </div>
      </div>

      {/* Desktop workspace */}
      <div className="flex-1 min-h-0 px-3 sm:px-6 py-3 sm:py-4 flex justify-center">
        <div className="w-full max-w-[110rem] h-full">
          {/* App window */}
          <div className="cw-window rounded-2xl overflow-hidden bg-white/80 backdrop-blur shadow-2xl ring-1 ring-white/60 h-full flex flex-col">
            {/* Window title bar */}
            <div className="shrink-0 flex items-center gap-2 px-4 h-9 bg-white/60 border-b border-purple-100">
              <span className="w-3 h-3 rounded-full bg-red-400/90" />
              <span className="w-3 h-3 rounded-full bg-yellow-400/90" />
              <span className="w-3 h-3 rounded-full bg-green-400/90" />
              <span className="ml-3 text-sm text-purple-800/80 font-medium truncate">
                {theme.emoji} {theme.name} — Creative Writer
              </span>
            </div>

            {/* Window content */}
            <div className="flex-1 min-h-0 flex flex-col p-3 sm:p-4">
              {/* Compact header */}
              <header className="shrink-0 flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
                <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-purple-700 to-fuchsia-600 bg-clip-text text-transparent">
                  What shall we write today?
                </h1>
                <p className="text-purple-700/60 text-sm">{theme.tagline}</p>
              </header>

              {/* Agent pipeline bar (always visible) */}
              <div className="shrink-0 mb-3">
                <AgentsPanel />
              </div>

              {/* Three-pane workspace: Compose · Article · Insights */}
              <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-4 overflow-y-auto lg:overflow-hidden">
                {/* Compose */}
                <div className="lg:w-80 xl:w-96 shrink-0 min-h-0 lg:overflow-y-auto">
                  <div className="rounded-2xl bg-purple-50/70 ring-1 ring-purple-100 p-4">
                    <h3 className="text-base font-semibold text-purple-900 mb-2">Create your article</h3>
                    <Task />
                    <div className="text-center mt-3">
                      <Toolbar />
                    </div>
                  </div>
                </div>

                {/* Article */}
                <section className="flex-1 min-w-0 min-h-0 lg:overflow-y-auto">
                  <div className="rounded-2xl bg-white ring-1 ring-purple-100 shadow-sm p-5 min-h-full">
                    <h2 className="text-lg font-semibold text-purple-900 mb-3">Your article</h2>
                    <Article />
                  </div>
                </section>

                {/* Insights */}
                <aside className="lg:w-96 shrink-0 min-h-0 lg:overflow-y-auto">
                  <StudioExtras />
                </aside>
              </div>

              <div className="shrink-0 text-center text-purple-400/70 text-[11px] pt-2">
                Creative Writer · {version}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

