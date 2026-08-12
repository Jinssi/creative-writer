import './app.css';
import { version } from "./version";
import Toolbar from "./components/toolbar";
import Article from "./components/article";
import Task from './components/task';
import ThemeMenu from './components/theme-menu';
import { useTheme } from './theme-context';

function App() {
  const { theme } = useTheme();

  return (
    <div className="cw-desktop min-h-screen w-full flex flex-col">
      {/* Desktop menu bar */}
      <div className="cw-menubar sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 h-11 backdrop-blur bg-white/40 border-b border-white/40">
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
      <div className="flex-1 px-4 sm:px-8 py-6 sm:py-10 flex justify-center">
        <div className="w-full max-w-6xl">
          {/* App window */}
          <div className="cw-window rounded-2xl overflow-hidden bg-white/80 backdrop-blur shadow-2xl ring-1 ring-white/60">
            {/* Window title bar */}
            <div className="flex items-center gap-2 px-4 h-10 bg-white/60 border-b border-purple-100">
              <span className="w-3 h-3 rounded-full bg-red-400/90" />
              <span className="w-3 h-3 rounded-full bg-yellow-400/90" />
              <span className="w-3 h-3 rounded-full bg-green-400/90" />
              <span className="ml-3 text-sm text-purple-800/80 font-medium truncate">
                {theme.emoji} {theme.name} — Creative Writer
              </span>
            </div>

            {/* Window content */}
            <div className="p-5 sm:p-8">
              <header className="mb-6">
                <h1 className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-purple-700 to-fuchsia-600 bg-clip-text text-transparent">
                  What shall we write today?
                </h1>
                <p className="text-purple-700/70 mt-2">
                  {theme.tagline}. Pick a theme in the menu bar, describe your idea, and the
                  agents research, draft and edit it for you.
                </p>
              </header>

              <div className="flex flex-col lg:flex-row lg:space-x-8">
                {/* Task panel */}
                <div className="lg:w-1/3">
                  <div className="rounded-2xl bg-purple-50/70 ring-1 ring-purple-100 p-5">
                    <h3 className="text-lg font-semibold text-purple-900 mb-3">Create your article</h3>
                    <Task />
                    <div className="text-center mt-4">
                      <Toolbar />
                    </div>
                  </div>
                </div>

                {/* Article panel */}
                <section className="lg:w-2/3 flex-grow mt-8 lg:mt-0">
                  <div className="rounded-2xl bg-white ring-1 ring-purple-100 shadow-sm p-6 min-h-[24rem]">
                    <h2 className="text-2xl font-semibold text-purple-900 mb-4">Your article</h2>
                    <Article />
                  </div>
                </section>
              </div>
            </div>
          </div>

          <div className="text-center text-white/70 text-xs mt-4">
            Creative Writer · {version}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

