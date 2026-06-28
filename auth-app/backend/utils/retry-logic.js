// utils/retry-logic.js
// Exponential backoff retry logic with jitter and error categorization

/**
 * Error categories for retry decision making
 */
const ERROR_CATEGORIES = {
  // Network errors - retry with backoff
  NETWORK: ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ECONNRESET', 'EPIPE'],
  
  // Rate limiting - retry with longer delay  
  RATE_LIMIT: [429],
  
  // Server errors - retry with backoff
  SERVER_ERROR: [500, 502, 503, 504],
  
  // Client errors - don't retry
  CLIENT_ERROR: [400, 401, 403, 404, 422],
  
  // Circuit breaker - fail fast
  CIRCUIT_OPEN: ['Circuit breaker is OPEN']
};

/**
 * Categorize an error to determine retry strategy
 * @param {Error} error The error to categorize
 * @returns {string} Error category
 */
function categorizeError(error) {
  // Check for network errors
  if (error.code && ERROR_CATEGORIES.NETWORK.includes(error.code)) {
    return 'NETWORK';
  }
  
  // Check for HTTP status codes
  const status = error.response?.status || error.status;
  if (status) {
    if (ERROR_CATEGORIES.RATE_LIMIT.includes(status)) {
      return 'RATE_LIMIT';
    }
    if (ERROR_CATEGORIES.SERVER_ERROR.includes(status)) {
      return 'SERVER_ERROR';
    }
    if (ERROR_CATEGORIES.CLIENT_ERROR.includes(status)) {
      return 'CLIENT_ERROR';
    }
  }
  
  // Check for circuit breaker errors
  if (error.circuitBreakerOpen || error.message?.includes('Circuit breaker')) {
    return 'CIRCUIT_OPEN';
  }
  
  // Check for timeout errors
  if (error.message?.includes('timeout') || error.code === 'ETIMEDOUT') {
    return 'TIMEOUT';
  }
  
  return 'UNKNOWN';
}

/**
 * Determine if an error should be retried
 * @param {Error} error The error that occurred
 * @param {number} attempt Current attempt number (0-based)
 * @param {number} maxRetries Maximum retry attempts
 * @returns {boolean} Whether to retry
 */
function shouldRetry(error, attempt, maxRetries) {
  if (attempt >= maxRetries) {
    return false;
  }
  
  const category = categorizeError(error);
  
  switch (category) {
    case 'NETWORK':
    case 'SERVER_ERROR':
    case 'TIMEOUT':
      return true;
    
    case 'RATE_LIMIT':
      // Limit rate limit retries to prevent overwhelming the service
      return attempt < Math.min(maxRetries, 2);
    
    case 'CLIENT_ERROR':
    case 'CIRCUIT_OPEN':
      return false;
    
    case 'UNKNOWN':
      // Only retry once for unknown errors
      return attempt < 1;
    
    default:
      return false;
  }
}

/**
 * Calculate delay for exponential backoff with jitter
 * @param {number} attempt Current attempt number (0-based)
 * @param {number} baseDelay Base delay in milliseconds
 * @param {number} maxDelay Maximum delay in milliseconds
 * @param {number} jitterFactor Jitter factor (0-1)
 * @returns {number} Delay in milliseconds
 */
function calculateDelay(attempt, baseDelay = 1000, maxDelay = 30000, jitterFactor = 0.1) {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = baseDelay * Math.pow(2, attempt);
  
  // Cap at maximum delay
  const cappedDelay = Math.min(exponentialDelay, maxDelay);
  
  // Add jitter to prevent thundering herd
  const jitter = cappedDelay * jitterFactor * Math.random();
  
  return Math.round(cappedDelay + jitter);
}

/**
 * Retry a function with exponential backoff
 * @param {Function} fn Async function to retry
 * @param {Object} options Retry configuration
 * @param {number} options.maxRetries Maximum number of retries (default: 3)
 * @param {number} options.baseDelay Base delay in ms (default: 1000)
 * @param {number} options.maxDelay Maximum delay in ms (default: 30000)
 * @param {number} options.jitterFactor Jitter factor 0-1 (default: 0.1)
 * @param {Function} options.onRetry Callback called on each retry
 * @returns {Promise} Function result or final error
 */
async function retryWithBackoff(fn, options = {}) {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 30000,
    jitterFactor = 0.1,
    onRetry = null
  } = options;

  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await fn();
      
      if (attempt > 0) {
        console.log(`[retry] Success on attempt ${attempt + 1}/${maxRetries + 1}`);
      }
      
      return result;
    } catch (error) {
      lastError = error;
      
      // Check if we should retry
      if (!shouldRetry(error, attempt, maxRetries)) {
        console.log(`[retry] Not retrying ${categorizeError(error)} error: ${error.message}`);
        throw error;
      }
      
      // Calculate delay for next attempt
      const delay = calculateDelay(attempt, baseDelay, maxDelay, jitterFactor);
      
      console.log(`[retry] Attempt ${attempt + 1}/${maxRetries + 1} failed (${categorizeError(error)}): ${error.message}. Retrying in ${delay}ms`);
      
      // Call retry callback if provided
      if (onRetry) {
        try {
          await onRetry(error, attempt, delay);
        } catch (callbackError) {
          console.warn(`[retry] onRetry callback failed: ${callbackError.message}`);
        }
      }
      
      // Wait before retry (unless it's the last attempt)
      if (attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  // All retries exhausted
  console.error(`[retry] All ${maxRetries + 1} attempts failed. Final error: ${lastError.message}`);
  throw lastError;
}

/**
 * Retry with simple linear backoff (for simpler use cases)
 * @param {Function} fn Async function to retry
 * @param {number} maxRetries Maximum retries (default: 2)
 * @param {number} delay Delay between retries in ms (default: 1000)
 * @returns {Promise} Function result or final error
 */
async function retryWithLinearBackoff(fn, maxRetries = 2, delay = 1000) {
  return retryWithBackoff(fn, {
    maxRetries,
    baseDelay: delay,
    maxDelay: delay,
    jitterFactor: 0
  });
}

/**
 * Create a retry-enabled version of a function
 * @param {Function} fn Function to wrap with retry logic
 * @param {Object} retryOptions Retry configuration
 * @returns {Function} Wrapped function with retry logic
 */
function withRetry(fn, retryOptions = {}) {
  return async function(...args) {
    return retryWithBackoff(() => fn.apply(this, args), retryOptions);
  };
}

module.exports = {
  retryWithBackoff,
  retryWithLinearBackoff,
  withRetry,
  categorizeError,
  shouldRetry,
  calculateDelay,
  ERROR_CATEGORIES
};