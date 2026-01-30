type ClassValue = string | number | boolean | undefined | null | ClassValue[];
type ClassObject = Record<string, boolean | undefined | null>;

/**
 * Utility for conditionally joining classNames together
 */
export function classNames(...args: (ClassValue | ClassObject)[]): string {
  const classes: string[] = [];

  for (const arg of args) {
    if (!arg) continue;

    if (typeof arg === 'string' || typeof arg === 'number') {
      classes.push(String(arg));
    } else if (Array.isArray(arg)) {
      const inner = classNames(...arg);
      if (inner) classes.push(inner);
    } else if (typeof arg === 'object') {
      for (const [key, value] of Object.entries(arg)) {
        if (value) classes.push(key);
      }
    }
  }

  return classes.join(' ');
}

/**
 * Alias for classNames (commonly used as cn)
 */
export const cn = classNames;
