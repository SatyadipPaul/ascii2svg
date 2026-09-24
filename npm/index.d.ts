export interface RenderOptions {
  /** A look for a destination: readme, slides, chat, print, dark, page. Explicit options still win. */
  preset?: "readme" | "slides" | "chat" | "print" | "dark" | "page" | "explore";
  style?: "glow" | "shadow" | "flat";
  square?: boolean;
  theme?: "light" | "dark" | "auto";
  color?: boolean;
  animate?: "none" | "draw" | "flow" | "scroll";
  /** Return a standalone web page instead of an SVG. */
  html?: boolean;
  /** Accent colour, e.g. "#0969da". */
  accent?: string;
  font?: string;
  /** Scale the output to this width in pixels. */
  width?: number;
  title?: string;
  tabSize?: number;
  /** Add report.diagram: boxes and edges (which box each arrow connects, and how). */
  describe?: boolean;
  /** Turn literal \n, \t, \" and \\ into real characters first. */
  unescape?: boolean;
  strict?: boolean;
  /** Fix typical LLM misalignment first; report.repair lists every edit and the corrected text. */
  repair?: boolean;
  /** Trees and mind maps fold when a node is clicked (where scripts run: a page, <object>, the file itself). */
  interactive?: boolean;
  /** With interactive: start with nodes at this depth folded (1 = only the root's children show). */
  fold?: number;
  /** One <text> per character, for design tools (Inkscape, Figma); browsers don't need it. */
  portable?: boolean;
}

export interface Warning {
  code: string;
  row: number;
  col: number;
  char: string;
  line: string;
  issue: string;
  hint: string;
}

export interface Report {
  status: "ok" | "warnings" | "self_check_failed";
  summary: string;
  exit_code: number;
  ok: boolean;
  boxes: number;
  arrowheads: number;
  roundtrip: "exact" | "MISMATCH";
  warnings: Warning[];
  version: string;
  repair?: { edits: { line: number; col: number; fix: string }[]; text?: string };
  /** The number of nodes that fold (0 without interactive, or when no tree was found). */
  folds?: number;
  /** Size of the SVG in bytes. */
  bytes?: number;
  diagram?: { boxes: object[]; edges: object[]; tree?: TreeNode[] };
  [field: string]: unknown;
}

export interface TreeNode {
  name: string;
  /** The box id, when the node is a box. */
  box?: string;
  row: number;
  col: number;
  children?: TreeNode[];
}

export interface LoadOptions {
  /** Where Pyodide's files are served from, for browser bundles, e.g.
   *  "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/". Node finds them in node_modules. */
  indexURL?: string;
  stdout?: (line: string) => void;
  stderr?: (line: string) => void;
}

/** Start Python and load ascii2svg (render() does this for you; call it early to hide the start-up). */
export function load(options?: LoadOptions): Promise<unknown>;
/** Render a text diagram: the SVG (or page) and the report `ascii2svg --json` prints. */
export function render(text: string, options?: RenderOptions): Promise<{ markup: string; report: Report }>;
/** Validate without keeping the drawing: the report, with boxes and edges. */
export function check(text: string, options?: RenderOptions): Promise<Report>;
/** The ascii2svg version inside, the same as the Python package's. */
export function version(): Promise<string>;
