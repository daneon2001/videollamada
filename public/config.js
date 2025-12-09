const inferredOrigin = typeof window !== "undefined" && window.location
  ? window.location.origin
  : null;
const DEFAULT_BASE = inferredOrigin || "http://127.0.0.1:8100";

export const CONFIG = {
  API_BASE: "https://192.168.0.251",
  SIGNAL_URL: "https://192.168.0.251",   // 👈 importante
};
