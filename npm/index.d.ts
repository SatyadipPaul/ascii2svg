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
  /** Tune the look. Colour tokens at the top apply to both themes; under `light` / `dark` to one. */
  tokens?: Tokens;
  /** Per box, by name (its title, as `describe` reports it): a link, a tooltip or a tint. */
  boxes?: Record<string, BoxOptions>;
  /** Keep these boxes and the lines between them bright; dim the rest. A list, or names separated by commas. */
  highlight?: string[] | string;
  /** Put data-name="<box name>" on each box's shapes, for your own CSS or scripts. */
  names?: boolean;
}

/** A hex colour such as "#0969da". */
export type Hex = string;

export interface Palette {
  ink?: Hex; bg?: Hex; accent?: Hex; neutral?: Hex; hover?: Hex; glow?: Hex;
  /** Box tints with color: [container, leaf] pairs, 1 to 6, repeated to fill 6. */
  hues?: [Hex, Hex][];
  /** Tree branch colours with color: [line, label tint] pairs, 1 to 6. */
  branch?: [Hex, Hex][];
}

export interface Tokens extends Palette {
  light?: Palette;
  dark?: Palette;
  /** Line width in px, 0.5 to 4 (default 1.4). */
  stroke?: number;
  /** Text size in px, 8 to 24 (default 14). Characters stay in their cells. */
  font_size?: number;
  /** Pulse speed in px/s, 20 to 2000 (default 150). */
  flow_speed?: number;
  /** Pause between pulses in seconds, 0 to 10 (default 0.9). */
  flow_rest?: number;
}

export interface BoxOptions {
  /** http(s), mailto or a relative URL. Works where the SVG is a page or <object>, not inside <img>. */
  link?: string;
  tooltip?: string;
  tint?: Hex | { light?: Hex; dark?: Hex };
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
