import React from 'react'
import ReactDOM from 'react-dom/client'
import { store } from "./store/store";
import { Provider } from "react-redux";
import App from './App.tsx'
import { ThemeProvider } from './theme-context';

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Provider store={store}>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </Provider>
  </React.StrictMode>
);
