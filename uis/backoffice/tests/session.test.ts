import { clearToken, getToken, setToken } from "../src/lib/session";

function installStorage() {
  const store = new Map<string, string>();
  Object.defineProperty(global, "window", {
    configurable: true,
    value: {
      localStorage: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => {
          store.set(key, value);
        },
        removeItem: (key: string) => {
          store.delete(key);
        },
      },
    },
  });
}

beforeEach(() => {
  installStorage();
});

test("getToken returns the stored session token", () => {
  setToken("session-token");
  expect(getToken()).toBe("session-token");
});

test("getToken returns null when no token is stored", () => {
  expect(getToken()).toBeNull();
});

test("setToken stores the session token", () => {
  setToken("session-token");
  expect(window.localStorage.getItem("healthcore.session.token")).toBe("session-token");
});

test("setToken fails when no browser storage exists", () => {
  // @ts-expect-error failure case is a missing browser global
  delete global.window;
  expect(() => setToken("session-token")).toThrow();
});

test("clearToken removes the stored session token", () => {
  setToken("session-token");
  clearToken();
  expect(getToken()).toBeNull();
});

test("clearToken leaves storage empty when no token was stored", () => {
  clearToken();
  expect(getToken()).toBeNull();
});
