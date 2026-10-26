/**
 * @param {number} delay
 * @param {(key: string) => void} run
 */
function debouncer(delay, run) {
  /** @type {Map<string, ReturnType<typeof setTimeout>>} */
  const pending = new Map();
  return {
    /** @param {string} key */
    schedule(key) {
      clearTimeout(pending.get(key));
      pending.set(
        key,
        setTimeout(() => {
          pending.delete(key);
          run(key);
        }, delay),
      );
    },
    /** @param {string} key */
    cancel(key) {
      clearTimeout(pending.get(key));
      pending.delete(key);
    },
    clear() {
      for (const timer of pending.values()) clearTimeout(timer);
      pending.clear();
    },
  };
}

module.exports = { debouncer };
