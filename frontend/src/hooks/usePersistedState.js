import { useState, useEffect, useCallback } from 'react';

const STORAGE_PREFIX = 'studenthub_';

/**
 * Custom hook that persists state to localStorage.
 * Behaves exactly like useState but survives page refresh.
 *
 * @param {string} key   Unique key (auto-prefixed with 'studenthub_')
 * @param {*} defaultValue  Fallback if nothing stored
 * @param {object} options  Optional config
 * @param {number} options.maxAgeMs  Max staleness in ms (default: none)
 * @param {boolean} options.useSession  Use sessionStorage instead (default: false)
 */
export function usePersistedState(key, defaultValue, options = {}) {
    const { maxAgeMs = null, useSession = false } = options;
    const storageKey = STORAGE_PREFIX + key;
    const storage = useSession ? sessionStorage : localStorage;

    const [state, setState] = useState(() => {
        try {
            const raw = storage.getItem(storageKey);
            if (raw === null) return defaultValue;
            const parsed = JSON.parse(raw);

            // Check staleness
            if (maxAgeMs && parsed._ts) {
                if (Date.now() - parsed._ts > maxAgeMs) {
                    storage.removeItem(storageKey);
                    return defaultValue;
                }
                return parsed.value;
            }

            // Legacy entries without _ts wrapper
            return parsed._ts !== undefined ? parsed.value : parsed;
        } catch {
            storage.removeItem(storageKey);
            return defaultValue;
        }
    });

    useEffect(() => {
        try {
            const payload = maxAgeMs
                ? JSON.stringify({ value: state, _ts: Date.now() })
                : JSON.stringify(state);
            storage.setItem(storageKey, payload);
        } catch (e) {
            // QuotaExceededError — degrade gracefully
            if (e.name === 'QuotaExceededError') {
                console.warn(`[usePersistedState] Storage full, skipping persist for "${key}"`);
            }
        }
    }, [storageKey, state, storage, maxAgeMs, key]);

    return [state, setState];
}

/**
 * Clears ALL studenthub_ keys from both localStorage and sessionStorage.
 * Call this on logout.
 */
export function clearAllPersistedState() {
    [localStorage, sessionStorage].forEach(store => {
        const keysToRemove = [];
        for (let i = 0; i < store.length; i++) {
            const k = store.key(i);
            if (k && k.startsWith(STORAGE_PREFIX)) {
                keysToRemove.push(k);
            }
        }
        keysToRemove.forEach(k => store.removeItem(k));
    });
}
