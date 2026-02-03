/**
 * Utility Functions - Validators
 * 
 * Common validation utilities used across modules.
 */

/**
 * Validates email format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validates phone number format
 */
export function isValidPhone(phone: string): boolean {
  const phoneRegex = /^\+?[\d\s\-()]{10,}$/;
  return phoneRegex.test(phone);
}

/**
 * Validates URL format
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Checks if value is empty (null, undefined, empty string, empty array)
 */
export function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim().length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * Checks if value is a valid number
 */
export function isValidNumber(value: unknown): boolean {
  if (typeof value === 'number') return !isNaN(value) && isFinite(value);
  if (typeof value === 'string') return !isNaN(parseFloat(value)) && isFinite(parseFloat(value));
  return false;
}

/**
 * Validates date format
 */
export function isValidDate(date: unknown): boolean {
  if (date instanceof Date) return !isNaN(date.getTime());
  if (typeof date === 'string') return !isNaN(new Date(date).getTime());
  return false;
}

/**
 * Validates minimum length
 */
export function hasMinLength(value: string, minLength: number): boolean {
  return value.length >= minLength;
}

/**
 * Validates maximum length
 */
export function hasMaxLength(value: string, maxLength: number): boolean {
  return value.length <= maxLength;
}

/**
 * Validates number range
 */
export function isInRange(value: number, min: number, max: number): boolean {
  return value >= min && value <= max;
}

/**
 * Validates alphanumeric string
 */
export function isAlphanumeric(value: string): boolean {
  return /^[a-zA-Z0-9]+$/.test(value);
}

/**
 * Validates that string contains only letters
 */
export function isAlpha(value: string): boolean {
  return /^[a-zA-Z]+$/.test(value);
}

/**
 * Validates password strength
 * - At least 8 characters
 * - Contains uppercase
 * - Contains lowercase
 * - Contains number
 * - Contains special character
 */
export function isStrongPassword(password: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (password.length < 8) errors.push('Must be at least 8 characters');
  if (!/[A-Z]/.test(password)) errors.push('Must contain uppercase letter');
  if (!/[a-z]/.test(password)) errors.push('Must contain lowercase letter');
  if (!/[0-9]/.test(password)) errors.push('Must contain number');
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push('Must contain special character');
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Creates a validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors: Record<string, string[]>;
}

/**
 * Combines multiple validation results
 */
export function combineValidations(...results: ValidationResult[]): ValidationResult {
  const combined: ValidationResult = { valid: true, errors: {} };
  
  for (const result of results) {
    if (!result.valid) {
      combined.valid = false;
      for (const [field, errors] of Object.entries(result.errors)) {
        if (!combined.errors[field]) {
          combined.errors[field] = [];
        }
        combined.errors[field].push(...errors);
      }
    }
  }
  
  return combined;
}
