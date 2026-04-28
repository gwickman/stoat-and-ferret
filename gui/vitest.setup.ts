import "@testing-library/jest-dom/vitest";

// Node 22+ ships an experimental built-in `localStorage` global that shadows
// jsdom's Storage implementation when vitest runs under jsdom. The Node
// version is a plain object missing the standard Storage methods
// (`clear`, `getItem`, `setItem`, etc.), which breaks tests that round-trip
// through localStorage. Replace it with a Storage-compatible shim.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

const storageDescriptor: PropertyDescriptor = {
  configurable: true,
  enumerable: true,
  get(): Storage {
    return memoryLocalStorage;
  },
};

const memoryLocalStorage = new MemoryStorage();
const memorySessionStorage = new MemoryStorage();

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  enumerable: true,
  get(): Storage {
    return memoryLocalStorage;
  },
});

Object.defineProperty(globalThis, "sessionStorage", {
  configurable: true,
  enumerable: true,
  get(): Storage {
    return memorySessionStorage;
  },
});

if (typeof window !== "undefined") {
  Object.defineProperty(window, "localStorage", storageDescriptor);
  Object.defineProperty(window, "sessionStorage", {
    configurable: true,
    enumerable: true,
    get(): Storage {
      return memorySessionStorage;
    },
  });
}

// jsdom does not implement ResizeObserver, used by react-resizable-panels.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

if (typeof globalThis.ResizeObserver === "undefined") {
  // @ts-expect-error -- assigning a stub to a structural type
  globalThis.ResizeObserver = ResizeObserverStub;
}

// jsdom does not implement DOMRect, also used by react-resizable-panels.
if (typeof globalThis.DOMRect === "undefined") {
  class DOMRectStub {
    x: number;
    y: number;
    width: number;
    height: number;
    constructor(x = 0, y = 0, width = 0, height = 0) {
      this.x = x;
      this.y = y;
      this.width = width;
      this.height = height;
    }
    get top(): number {
      return this.y;
    }
    get bottom(): number {
      return this.y + this.height;
    }
    get left(): number {
      return this.x;
    }
    get right(): number {
      return this.x + this.width;
    }
    toJSON(): Record<string, number> {
      return { x: this.x, y: this.y, width: this.width, height: this.height };
    }
    static fromRect(other?: { x?: number; y?: number; width?: number; height?: number }): DOMRectStub {
      return new DOMRectStub(other?.x, other?.y, other?.width, other?.height);
    }
  }
  // @ts-expect-error -- assigning a stub to a structural type
  globalThis.DOMRect = DOMRectStub;
}
