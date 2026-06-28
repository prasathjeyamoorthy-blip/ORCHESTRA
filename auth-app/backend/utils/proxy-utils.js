// utils/proxy-utils.js
// Enhanced proxy utilities for pan-rag communication with resilience patterns

const { CircuitBreaker } = require('./circuit-breaker');
const { retryWithBackoff, categorizeError } = require('./retry-logic');

/**
 * Performance metrics tracker
 */
class ProxyMetrics {
  constructor() {
    this.requests = 0;
    this.successes = 0;
    this.failures = 0;
    this.totalLatency = 0;
    this.averageLatency = 0;
    this.maxLatency = 0;
    this.minLatency = Infinity;
    this.errorsByCategory = new Map();
    this.startTime = Date.now();
  }

  recordRequest(latency, success, errorCategory = null) {
    this.requests++;
    this.totalLatency += latency;
    this.averageLatency = this.totalLatency / this.requests;
    this.maxLatency = Math.max(this.maxLatency, latency);
    this.minLatency = Math.min(this.minLatency, latency);

    if (success) {
      this.successes++;
    } else {
      this.failures++;
      if (errorCategory) {
        const count = this.errorsByCategory.get(errorCategory) || 0;
        this.errorsByCategory.set(errorCategory, count + 1);
      }
    }
  }

  getStats() {
    const uptime = Date.now() - this.startTime;
    const successRate = this.requests > 0 ? (this.successes / this.requests) * 100 : 100;

    return {
      requests: this.requests,
      successes: this.successes,
      failures: this.failures,
      successRate: Math.round(successRate * 100) / 100,
      averageLatency: Math.round(this.averageLatency),
      maxLatency: this.maxLatency === -Infinity ? 0 : this.maxLatency,
      minLatency: this.minLatency === Infinity ? 0 : this.minLatency,
      errorsByCategory: Object.fromEntries(this.errorsByCategory),
      uptimeMs: uptime
    };
  }

  reset() {
    this.requests = 0;
    this.successes = 0;
    this.failures = 0;
    this.totalLatency = 0;
    this.averageLatency = 0;
    this.maxLatency = 0;
    this.minLatency = Infinity;
    this.errorsByCategory.clear();
    this.startTime = Date.now();
  }
}

// Global metrics and circuit breaker instances
const metrics = new ProxyMetrics();
const circuitBreakers = new Map();

/**
 * Get or create a circuit breaker for a service
 * @param {string} serviceName Service identifier
 * @param {Object} options Circuit breaker options
 * @returns {CircuitBreaker} Circuit breaker instance
 */
function getCircuitBreaker(serviceName, options = {}) {
  if (!circuitBreakers.has(serviceName)) {
    const defaultOptions = {
      name: serviceName,
      failureThreshold: 3,
      recoveryTimeout: 30000, // 30 seconds
      monitoringPeriod: 60000  // 1 minute
    };
    
    circuitBreakers.set(serviceName, new CircuitBreaker({ ...defaultOptions, ...options }));
  }
  
  return circuitBreakers.get(serviceName);
}

/**
 * Generate fallback responses for different service failures
 * @param {string} intent Request intent if known
 * @param {Error} error The error that occurred
 * @returns {Object} Fallback response structure
 */
function generateFallbackResponse(intent, error) {
  const category = categorizeError(error);
  
  // Fallback responses by intent type
  const FALLBACK_RESPONSES = {
    DEFAULT: "I'm temporarily unable to process your request. Please try again in a few moments, or contact support if the issue persists.",
    
    PAN_APPLICATION: "The PAN application service is temporarily unavailable. You can continue with your application later, or visit the official NSDL/UTI website directly.",
    
    DOCUMENT_UPLOAD: "Document processing is temporarily offline. Your file has been saved and will be processed when the service returns.",
    
    STATUS_CHECK: "I can't check your PAN status right now. Please try the official NSDL or UTI websites, or check back later.",
    
    CHAT: "The AI assistant is temporarily overloaded. Please try again in a few minutes."
  };
  
  if (category === 'CIRCUIT_OPEN') {
    return {
      answer: "Our AI assistant is temporarily overloaded. Please try again in a few minutes.",
      sources: [],
      followups: ["Try again", "Contact support", "Continue without AI"],
      intent: "service_unavailable",
      service_error: true,
      error_category: category
    };
  }
  
  // Intent-specific fallbacks
  const fallbackMessage = FALLBACK_RESPONSES[intent?.toUpperCase()] || FALLBACK_RESPONSES.DEFAULT;
  
  return {
    answer: fallbackMessage,
    sources: [],
    followups: ["Retry", "Continue later", "Contact support"],
    intent: "service_degraded",
    service_error: true,
    error_category: category
  };
}

/**
 * Create an enhanced HTTP request with timeout, logging, and resilience patterns
 * @param {string} url Target URL
 * @param {Object} data Request payload
 * @param {Object} options Request options
 * @param {number} options.timeout Request timeout in ms (default: 30000)
 * @param {string} options.method HTTP method (default: 'POST')
 * @param {Object} options.headers Additional headers
 * @param {string} options.serviceName Service name for circuit breaker (default: 'pan-rag')
 * @param {Object} options.circuitBreakerOptions Circuit breaker configuration
 * @param {Object} options.retryOptions Retry configuration
 * @param {boolean} options.enableLogging Enable request/response logging (default: true)
 * @param {string} options.context Additional context for logging
 * @returns {Promise<Object>} Response data
 */
async function createProxyRequest(url, data = null, options = {}) {
  const {
    timeout = 30000,
    method = 'POST',
    headers = {},
    serviceName = 'pan-rag',
    circuitBreakerOptions = {},
    retryOptions = {},
    enableLogging = true,
    context = ''
  } = options;

  const requestId = Math.random().toString(36).substr(2, 9);
  const startTime = Date.now();
  
  // Default retry options
  const defaultRetryOptions = {
    maxRetries: 2,
    baseDelay: 1000,
    maxDelay: 10000,
    onRetry: enableLogging ? (error, attempt, delay) => {
      console.log(`[proxy-utils] ${requestId} Retry ${attempt + 1} after ${delay}ms - ${error.message}`);
    } : null
  };

  const finalRetryOptions = { ...defaultRetryOptions, ...retryOptions };
  
  // Get circuit breaker for this service
  const circuitBreaker = getCircuitBreaker(serviceName, circuitBreakerOptions);

  if (enableLogging) {
    console.log(`[proxy-utils] ${requestId} ${method} ${url} ${context ? `(${context})` : ''}`);
    if (data && method !== 'GET') {
      console.log(`[proxy-utils] ${requestId} Request payload: ${JSON.stringify(data).slice(0, 200)}${JSON.stringify(data).length > 200 ? '...' : ''}`);
    }
  }

  try {
    // Execute request with circuit breaker and retry logic
    const result = await circuitBreaker.call(async () => {
      return retryWithBackoff(async () => {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
          const requestOptions = {
            method,
            headers: {
              'Content-Type': 'application/json',
              'User-Agent': 'auth-backend-proxy/1.0',
              ...headers
            },
            signal: controller.signal
          };

          // Add body for non-GET requests
          if (data && method !== 'GET') {
            requestOptions.body = JSON.stringify(data);
          }

          const response = await fetch(url, requestOptions);
          clearTimeout(timeoutId);

          // Handle non-2xx responses
          if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error');
            const error = new Error(`HTTP ${response.status}: ${errorText}`);
            error.status = response.status;
            error.response = { status: response.status, statusText: response.statusText };
            throw error;
          }

          // Parse JSON response
          let responseData;
          try {
            responseData = await response.json();
          } catch (parseError) {
            throw new Error(`Invalid JSON response: ${parseError.message}`);
          }

          return responseData;

        } catch (fetchError) {
          clearTimeout(timeoutId);
          
          // Handle abort/timeout
          if (fetchError.name === 'AbortError') {
            const timeoutError = new Error(`Request timeout after ${timeout}ms`);
            timeoutError.code = 'ETIMEDOUT';
            throw timeoutError;
          }
          
          throw fetchError;
        }
      }, finalRetryOptions);
    });

    // Record successful request
    const latency = Date.now() - startTime;
    metrics.recordRequest(latency, true);

    if (enableLogging) {
      console.log(`[proxy-utils] ${requestId} Success in ${latency}ms`);
      if (result) {
        console.log(`[proxy-utils] ${requestId} Response: ${JSON.stringify(result).slice(0, 200)}${JSON.stringify(result).length > 200 ? '...' : ''}`);
      }
    }

    return result;

  } catch (error) {
    // Record failed request
    const latency = Date.now() - startTime;
    const errorCategory = categorizeError(error);
    metrics.recordRequest(latency, false, errorCategory);

    if (enableLogging) {
      console.error(`[proxy-utils] ${requestId} Failed in ${latency}ms (${errorCategory}): ${error.message}`);
    }

    // Add request context to error
    error.requestId = requestId;
    error.url = url;
    error.serviceName = serviceName;
    error.latency = latency;
    error.category = errorCategory;

    throw error;
  }
}

/**
 * Create a streaming proxy request for SSE endpoints
 * @param {string} url Target SSE URL
 * @param {Object} data Request payload
 * @param {Object} options Request options
 * @param {Function} onEvent Callback for each SSE event
 * @param {Function} onError Callback for errors
 * @param {Function} onComplete Callback when stream completes
 * @returns {Promise<void>} Resolves when stream completes
 */
async function createStreamingProxyRequest(url, data = null, options = {}, onEvent, onError, onComplete) {
  const {
    timeout = 60000, // Longer timeout for streaming
    headers = {},
    serviceName = 'pan-rag-stream',
    enableLogging = true,
    context = ''
  } = options;

  const requestId = Math.random().toString(36).substr(2, 9);
  const startTime = Date.now();
  
  if (enableLogging) {
    console.log(`[proxy-utils] ${requestId} SSE ${url} ${context ? `(${context})` : ''}`);
  }

  const circuitBreaker = getCircuitBreaker(serviceName, { failureThreshold: 2, recoveryTimeout: 15000 });

  try {
    await circuitBreaker.call(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            ...headers
          },
          body: data ? JSON.stringify(data) : undefined,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`SSE request failed: ${response.status} ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('No response body for SSE stream');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            if (enableLogging) {
              console.log(`[proxy-utils] ${requestId} SSE stream completed in ${Date.now() - startTime}ms`);
            }
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim() === '') continue;
            
            if (line.startsWith('data: ')) {
              const eventData = line.slice(6);
              
              try {
                const parsed = JSON.parse(eventData);
                await onEvent(parsed);
              } catch (parseError) {
                console.warn(`[proxy-utils] ${requestId} Failed to parse SSE data: ${eventData}`);
                continue;
              }
            }
          }
        }

        // Record successful streaming request
        metrics.recordRequest(Date.now() - startTime, true);
        
        if (onComplete) {
          await onComplete();
        }

      } catch (streamError) {
        clearTimeout(timeoutId);
        throw streamError;
      }
    });

  } catch (error) {
    const latency = Date.now() - startTime;
    const errorCategory = categorizeError(error);
    metrics.recordRequest(latency, false, errorCategory);

    if (enableLogging) {
      console.error(`[proxy-utils] ${requestId} SSE failed in ${latency}ms (${errorCategory}): ${error.message}`);
    }

    error.requestId = requestId;
    error.url = url;
    error.serviceName = serviceName;
    error.latency = latency;
    error.category = errorCategory;

    if (onError) {
      await onError(error);
    } else {
      throw error;
    }
  }
}

/**
 * Create a specialized proxy request for pan-rag chat API
 * @param {Object} questionRequest PAN-rag question request payload
 * @param {Object} options Request options
 * @returns {Promise<Object>} PAN-rag response
 */
async function createPanRagChatRequest(questionRequest, options = {}) {
  const ragUrl = process.env.RAG_URL || 'http://localhost:8000';
  const endpoint = `${ragUrl}/api/ask`;
  
  return createProxyRequest(endpoint, questionRequest, {
    serviceName: 'pan-rag-chat',
    context: `user:${questionRequest.user_id?.slice(0, 8) || 'unknown'}, session:${questionRequest.session_id?.slice(0, 8) || 'new'}`,
    ...options
  });
}

/**
 * Create a specialized streaming proxy request for pan-rag chat API
 * @param {Object} questionRequest PAN-rag question request payload
 * @param {Function} onEvent Callback for each SSE event
 * @param {Function} onError Callback for errors
 * @param {Function} onComplete Callback when stream completes
 * @param {Object} options Request options
 * @returns {Promise<void>}
 */
async function createPanRagStreamRequest(questionRequest, onEvent, onError, onComplete, options = {}) {
  const ragUrl = process.env.RAG_URL || 'http://localhost:8000';
  const endpoint = `${ragUrl}/api/ask-stream`;
  
  return createStreamingProxyRequest(endpoint, questionRequest, {
    serviceName: 'pan-rag-stream',
    context: `user:${questionRequest.user_id?.slice(0, 8) || 'unknown'}, session:${questionRequest.session_id?.slice(0, 8) || 'new'}`,
    ...options
  }, onEvent, onError, onComplete);
}

/**
 * Create a proxy request for document upload to pan-rag
 * @param {FormData} formData Document upload form data
 * @param {Object} options Request options
 * @returns {Promise<Object>} Upload response
 */
async function createPanRagUploadRequest(formData, options = {}) {
  const ragUrl = process.env.RAG_URL || 'http://localhost:8000';
  const endpoint = `${ragUrl}/api/upload`;
  
  // Override headers for multipart/form-data
  const uploadOptions = {
    ...options,
    method: 'POST',
    headers: {
      // Don't set Content-Type for FormData, let fetch handle it
      ...options.headers
    },
    serviceName: 'pan-rag-upload',
    timeout: 60000, // Longer timeout for file uploads
    context: 'document-upload'
  };

  // Use fetch directly for FormData
  const requestId = Math.random().toString(36).substr(2, 9);
  const startTime = Date.now();
  
  console.log(`[proxy-utils] ${requestId} POST ${endpoint} (document-upload)`);

  const circuitBreaker = getCircuitBreaker('pan-rag-upload', { failureThreshold: 2, recoveryTimeout: 30000 });

  try {
    const result = await circuitBreaker.call(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), uploadOptions.timeout);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
          headers: uploadOptions.headers
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error');
          const error = new Error(`Upload failed: HTTP ${response.status}: ${errorText}`);
          error.status = response.status;
          throw error;
        }

        return await response.json();

      } catch (fetchError) {
        clearTimeout(timeoutId);
        
        if (fetchError.name === 'AbortError') {
          const timeoutError = new Error(`Upload timeout after ${uploadOptions.timeout}ms`);
          timeoutError.code = 'ETIMEDOUT';
          throw timeoutError;
        }
        
        throw fetchError;
      }
    });

    const latency = Date.now() - startTime;
    metrics.recordRequest(latency, true);
    console.log(`[proxy-utils] ${requestId} Upload success in ${latency}ms`);

    return result;

  } catch (error) {
    const latency = Date.now() - startTime;
    const errorCategory = categorizeError(error);
    metrics.recordRequest(latency, false, errorCategory);

    console.error(`[proxy-utils] ${requestId} Upload failed in ${latency}ms (${errorCategory}): ${error.message}`);
    
    error.requestId = requestId;
    error.url = endpoint;
    error.serviceName = 'pan-rag-upload';
    error.latency = latency;
    error.category = errorCategory;

    throw error;
  }
}

/**
 * Get proxy performance metrics
 * @returns {Object} Metrics data
 */
function getProxyMetrics() {
  const stats = metrics.getStats();
  const circuitBreakerStats = {};
  
  for (const [name, breaker] of circuitBreakers) {
    circuitBreakerStats[name] = breaker.getStatus();
  }

  return {
    ...stats,
    circuitBreakers: circuitBreakerStats
  };
}

/**
 * Reset all proxy metrics and circuit breakers
 */
function resetProxyMetrics() {
  metrics.reset();
  for (const breaker of circuitBreakers.values()) {
    breaker.reset();
  }
}

/**
 * Format user context string from profile data
 * @param {Object} profile User profile object
 * @returns {string} Formatted user context string
 */
function formatUserContextString(profile) {
  if (!profile || Object.keys(profile).length === 0) {
    return '';
  }

  const lines = [];
  
  // Personal information
  if (profile.full_name || profile.name) {
    lines.push(`- Full Name (as in Aadhaar): ${profile.full_name || profile.name}`);
  }
  if (profile.mother_name) {
    lines.push(`- Mother's Name: ${profile.mother_name}`);
  }
  if (profile.email) {
    lines.push(`- Email: ${profile.email}`);
  }
  if (profile.phone) {
    lines.push(`- Phone: ${profile.phone}`);
  }
  if (profile.income || profile.annual_income) {
    lines.push(`- Annual Income: ${profile.income || profile.annual_income}`);
  }
  if (profile.dob || profile.date_of_birth) {
    lines.push(`- Date of Birth: ${profile.dob || profile.date_of_birth}`);
  }
  
  // PAN application preferences
  if (profile.residential_status) {
    lines.push(`- Residential Status: ${profile.residential_status}`);
  }
  if (profile.source_of_income) {
    lines.push(`- Source of Income: ${profile.source_of_income}`);
  }
  if (profile.submission_mode) {
    lines.push(`- Preferred Submission Mode: ${profile.submission_mode}`);
  }
  if (profile.delivery_mode) {
    lines.push(`- Preferred Delivery Mode: ${profile.delivery_mode}`);
  }
  if (profile.applicant_type) {
    lines.push(`- Applicant Type: ${profile.applicant_type}`);
  }

  return lines.join('\n');
}

module.exports = {
  createProxyRequest,
  createStreamingProxyRequest,
  createPanRagChatRequest,
  createPanRagStreamRequest,
  createPanRagUploadRequest,
  generateFallbackResponse,
  getProxyMetrics,
  resetProxyMetrics,
  formatUserContextString,
  getCircuitBreaker,
  ProxyMetrics
};