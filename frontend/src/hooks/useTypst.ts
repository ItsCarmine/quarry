import { useCallback, useRef, useState } from "react";

// URLs to the WASM files — Vite serves node_modules as-is in dev
const RENDERER_WASM_URL =
  "/node_modules/@myriaddreamin/typst-ts-renderer/pkg/typst_ts_renderer_bg.wasm";
const COMPILER_WASM_URL =
  "/node_modules/@myriaddreamin/typst-ts-web-compiler/pkg/typst_ts_web_compiler_bg.wasm";

let initPromise: Promise<void> | null = null;
let $typstInstance: any = null;

async function initTypst() {
  const { $typst } = await import("@myriaddreamin/typst.ts");

  $typst.setCompilerInitOptions({
    getModule: () => fetch(COMPILER_WASM_URL),
  });
  $typst.setRendererInitOptions({
    getModule: () => fetch(RENDERER_WASM_URL),
  });

  $typstInstance = $typst;
}

function getTypst() {
  if (!initPromise) {
    initPromise = initTypst();
  }
  return initPromise;
}

export function useTypst() {
  const [svg, setSvg] = useState<string>("");
  const [compiling, setCompiling] = useState(false);
  const [error, setError] = useState<string>("");
  const lastSource = useRef<string>("");

  const compile = useCallback(async (source: string) => {
    if (!source || source === lastSource.current) return;
    lastSource.current = source;
    setCompiling(true);
    setError("");

    try {
      await getTypst();
      const result = await $typstInstance.svg({ mainContent: source });
      setSvg(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Typst compilation failed");
    } finally {
      setCompiling(false);
    }
  }, []);

  return { svg, compiling, error, compile };
}
