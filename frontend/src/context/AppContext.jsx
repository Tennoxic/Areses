import { createContext, useContext, useReducer } from "react";

const AppStateContext = createContext(null);
const AppDispatchContext = createContext(null);

const isNarrowViewport = () => typeof window !== "undefined" && window.innerWidth <= 900;

const initialState = {
  activeFilter: { type: "all", sourceId: null, folderId: null, unreadOnly: false, starredOnly: false, readLaterOnly: false, summariesOnly: false, query: "" },
  activeArticleId: null,
  sidebarOpen: !isNarrowViewport(),
  view: "normal",
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_FILTER":
      return { ...state, activeFilter: { ...state.activeFilter, ...action.payload }, activeArticleId: null };
    case "SET_ACTIVE_ARTICLE":
      return { ...state, activeArticleId: action.payload };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case "SET_VIEW":
      return { ...state, view: action.payload };
    default:
      return state;
  }
}

export function AppStateProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const context = useContext(AppStateContext);
  if (!context) throw new Error("useAppState must be used within AppStateProvider");
  return context;
}

export function useAppDispatch() {
  const context = useContext(AppDispatchContext);
  if (!context) throw new Error("useAppDispatch must be used within AppStateProvider");
  return context;
}
