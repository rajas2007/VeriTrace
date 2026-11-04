import React from "react";
import { App } from "./App";

// Application route definitions for Tauri desktop shell
export const routes = [
  {
    path: "/",
    element: <App />,
  },
];
