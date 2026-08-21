import { BrowserRouter } from "react-router-dom";

import { AppRouter } from "./router";
import { Providers } from "./providers";
import { NavShell } from "./NavShell";

export function App() {
  return (
    <Providers>
      <BrowserRouter>
        <NavShell>
          <AppRouter />
        </NavShell>
      </BrowserRouter>
    </Providers>
  );
}
