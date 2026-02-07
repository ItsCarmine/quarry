import { useCallback, useEffect, useRef, useState } from "react";

let typstPromise: Promise<typeof import("@myriaddreamin/typst.ts")> | null = null;

function getTypst() {
  if (!typstPromise) {
    typstPromise = import("@myriaddreamin/typst.ts");
  }
  return typstPromise;
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
      const { $typst } = await getTypst();
      const result = await $typst.svg({ mainContent: source });
      setSvg(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Typst compilation failed");
      // On compile error, don't clear previous SVG
    } finally {
      setCompiling(false);
    }
  }, []);

  return { svg, compiling, error, compile };
}
