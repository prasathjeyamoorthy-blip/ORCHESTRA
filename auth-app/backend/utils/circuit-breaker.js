// utils/circuit-breaker.js
// Circuit breaker implementation for service resilience

/**
 * Circuit breaker states:
 * - CLOSED: Normal operation, requests pass through
 * - OPEN: Service is failing, requests fail fast
 * - HALF_OPEN: Testing if service has recovered
 */
const CIRCUIT_STATES = {
  CLOSED: 'CLOSED',
  OPEN: 'OPEN',
  HALF_OPEN: 'HALF_OPEN'
};

class CircuitBreaker {
  /**
   * Create a new circuit breaker
   * @param {Object} options Configuration options
   * @param {string} options.name Circuit breaker identifier
   * @param {number} options.failureThreshold Number of failures before opening
   * @param {number} options.recoveryTimeout Time in ms before attempting recovery
   * @param {number} options.monitoringPeriod Time in ms for monitoring window
   */
  constructor(options = {}) {
    this.name = options.name || 'default';
    this.failureThreshold = options.failureThreshold || 5;
    this.recoveryTimeout = options.recoveryTimeout || 60000; // 60 seconds
    this.monitoringPeriod = options.monitoringPeriod || 120000; // 2 minutes
    
    // Circuit state
    this.state = CIRCUIT_STATES.CLOSED;
    this.failures = 0;
    this.nextAttempt = Date.now();
    
    // Monitoring metrics
    this.monitor = {
      requests: 0,
      successes: 0,
      failures: 0,
      lastReset: Date.now()
    };

    console.log(`[circuit-breaker] Initialized ${this.name} - threshold: ${this.failureThreshold}, recovery: ${this.recoveryTimeout}ms`);
  }

  /**
   * Execute a function with circuit breaker protection
   * @param {Function} fn Async function to execute
   * @returns {Promise} Function result or circuit breaker error
   */
  async call(fn) {
    this._resetMonitoringIfNeeded();
    this.monitor.requests++;

    // Check if circuit is open
    if (this.state === CIRCUIT_STATES.OPEN) {
      if (Date.now() < this.nextAttempt) {
        const error = new Error(`Circuit breaker is OPEN - service temporarily unavailable (${this.name})`);
        error.circuitBreakerOpen = true;
        throw error;
      }
      // Time to try recovery
      this.state = CIRCUIT_STATES.HALF_OPEN;
      console.log(`[circuit-breaker] ${this.name} transitioning to HALF_OPEN for recovery attempt`);
    }

    try {
      const result = await fn();
      this._onSuccess();
      return result;
    } catch (error) {
      this._onFailure(error);
      throw error;
    }
  }

  /**
   * Handle successful request
   * @private
   */
  _onSuccess() {
    this.failures = 0;
    this.monitor.successes++;
    
    if (this.state === CIRCUIT_STATES.HALF_OPEN) {
      console.log(`[circuit-breaker] ${this.name} recovered - transitioning to CLOSED`);
    }
    
    this.state = CIRCUIT_STATES.CLOSED;
  }

  /**
   * Handle failed request
   * @param {Error} error The error that occurred
   * @private
   */
  _onFailure(error) {
    this.failures++;
    this.monitor.failures++;
    
    console.log(`[circuit-breaker] ${this.name} failure ${this.failures}/${this.failureThreshold}: ${error.message}`);
    
    if (this.failures >= this.failureThreshold) {
      this.state = CIRCUIT_STATES.OPEN;
      this.nextAttempt = Date.now() + this.recoveryTimeout;
      console.log(`[circuit-breaker] ${this.name} opened - will retry at ${new Date(this.nextAttempt).toISOString()}`);
    }
  }

  /**
   * Reset monitoring metrics if period has elapsed
   * @private
   */
  _resetMonitoringIfNeeded() {
    const now = Date.now();
    if (now - this.monitor.lastReset >= this.monitoringPeriod) {
      this.monitor = {
        requests: 0,
        successes: 0,
        failures: 0,
        lastReset: now
      };
    }
  }

  /**
   * Get current circuit breaker status
   * @returns {Object} Status information
   */
  getStatus() {
    return {
      name: this.name,
      state: this.state,
      failures: this.failures,
      failureThreshold: this.failureThreshold,
      nextAttempt: this.nextAttempt,
      monitor: { ...this.monitor },
      healthPercent: this.monitor.requests > 0 
        ? Math.round((this.monitor.successes / this.monitor.requests) * 100)
        : 100
    };
  }

  /**
   * Manually reset the circuit breaker
   */
  reset() {
    this.state = CIRCUIT_STATES.CLOSED;
    this.failures = 0;
    this.nextAttempt = Date.now();
    console.log(`[circuit-breaker] ${this.name} manually reset`);
  }

  /**
   * Force the circuit breaker open
   */
  forceOpen() {
    this.state = CIRCUIT_STATES.OPEN;
    this.nextAttempt = Date.now() + this.recoveryTimeout;
    console.log(`[circuit-breaker] ${this.name} forced open`);
  }
}

module.exports = {
  CircuitBreaker,
  CIRCUIT_STATES
};