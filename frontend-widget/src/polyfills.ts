import { Buffer } from "buffer";

declare global {
  interface Window {
    Buffer?: typeof Buffer;
  }
}

if (typeof globalThis.Buffer === "undefined") {
  globalThis.Buffer = Buffer;
}
