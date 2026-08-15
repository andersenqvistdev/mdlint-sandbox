/**
 * Forge Dashboard - Entry Point
 *
 * This file serves as the entry point referenced by index.html.
 * The main implementation is in main.js.
 *
 * @version 0.1.0
 */

// Import main dashboard functionality
// In a build system this would use ES modules, but for vanilla JS
// we simply ensure main.js is loaded first or include it inline.

// For standalone operation, this file can be used directly.
// When using a bundler, replace this with: export * from './main.js';

(function() {
  'use strict';

  // Check if main.js has already loaded the dashboard
  if (window.ForgeDashboard) {
    console.log('Forge Dashboard already initialized via main.js');
    return;
  }

  // If main.js hasn't loaded, this file contains the full implementation
  // This allows either file to work standalone

  // ============================================================================
  // Configuration
  // ============================================================================

  const CONFIG = {
    SSE_ENDPOINT: '/api/stream',
    API_ENDPOINT: '/api/dashboard',
    RECONNECT_BASE_DELAY: 1000,
    RECONNECT_MAX_DELAY: 30000,
    HEARTBEAT_TIMEOUT: 60000,
    THEME_STORAGE_KEY: 'forge-dashboard-theme',
    STATE_STORAGE_KEY: 'forge-dashboard-state'
  };

  // ============================================================================
  // State Management
  // ============================================================================

  const state = {
    eventSource: null,
    reconnectAttempts: 0,
    reconnectTimeout: null,
    lastHeartbeat: null,
    heartbeatTimer: null,
    cachedData: null,
    isConnected: false,
    currentPanel: 'health'
  };

  // ============================================================================
  // DOM Elements Cache
  // ============================================================================

  const elements = {
    // Connection status
    connectionIndicator: null,
    connectionText: null,
    lastUpdateTime: null,

    // Panels
    panels: null,
    navItems: null,

    // Health panel
    healthScore: null,
    healthProgress: null,
    healthFactors: null,

    // Tasks panel
    tasksPending: null,
    tasksActive: null,
    tasksBlocked: null,
    tasksCompleted: null,
    tasksBadge: null,
    velocityDaily: null,
    velocityWeekly: null,
    velocityTrend: null,

    // Organization panel
    economicsSummary: null,
    departmentsContainer: null,

    // Roadmap panel
    phaseList: null,

    // Errors panel
    escalationsTable: null,
    errorTimeline: null,
    errorsBadge: null,
    escalationCount: null,

    // Footer
    daemonStatus: null,
    daemonStatusText: null,

    // Daemon panel
    daemonRunningIndicator: null,
    daemonRunningText: null,
    daemonPidValue: null,
    daemonUptimeValue: null,
    daemonHeartbeatValue: null,
    daemonCompleted: null,
    daemonFailed: null,
    daemonSuccessRate: null,
    daemonCurrentCycle: null,
    daemonEventsCount: null,
    daemonTimeline: null,
    daemonStrategicInfo: null,
    daemonBadge: null,

    // Buttons
    refreshHealthBtn: null,
    refreshDaemonBtn: null
  };

  // ============================================================================
  // Initialization
  // ============================================================================

  function init() {
    cacheElements();
    loadThemePreference();
    loadCachedState();
    setupEventListeners();
    fetchInitialData();
    connectSSE();
  }

  function cacheElements() {
    // Connection status
    elements.connectionIndicator = document.getElementById('connection-indicator');
    elements.connectionText = document.getElementById('connection-text');
    elements.lastUpdateTime = document.getElementById('last-update-time');

    // Panels
    elements.panels = document.querySelectorAll('.panel');
    elements.navItems = document.querySelectorAll('.nav__item');

    // Health panel
    elements.healthScore = document.getElementById('health-score');
    elements.healthProgress = document.getElementById('health-progress');
    elements.healthFactors = document.getElementById('health-factors');

    // Tasks panel
    elements.tasksPending = document.getElementById('tasks-pending');
    elements.tasksActive = document.getElementById('tasks-active');
    elements.tasksBlocked = document.getElementById('tasks-blocked');
    elements.tasksCompleted = document.getElementById('tasks-completed');
    elements.tasksBadge = document.getElementById('tasks-badge');
    elements.velocityDaily = document.getElementById('velocity-daily');
    elements.velocityWeekly = document.getElementById('velocity-weekly');
    elements.velocityTrend = document.getElementById('velocity-trend');

    // Organization panel
    elements.economicsSummary = document.getElementById('economics-summary');
    elements.departmentsContainer = document.getElementById('departments-container');

    // Roadmap panel
    elements.phaseList = document.getElementById('phase-list');

    // Errors panel
    elements.escalationsTable = document.getElementById('escalations-table');
    elements.errorTimeline = document.getElementById('error-timeline');
    elements.errorsBadge = document.getElementById('errors-badge');
    elements.escalationCount = document.getElementById('escalation-count');

    // Footer
    elements.daemonStatus = document.getElementById('daemon-status');
    elements.daemonStatusText = document.getElementById('daemon-status-text');

    // Daemon panel
    elements.daemonRunningIndicator = document.getElementById('daemon-running-indicator');
    elements.daemonRunningText = document.getElementById('daemon-running-text');
    elements.daemonPidValue = document.getElementById('daemon-pid-value');
    elements.daemonUptimeValue = document.getElementById('daemon-uptime-value');
    elements.daemonHeartbeatValue = document.getElementById('daemon-heartbeat-value');
    elements.daemonCompleted = document.getElementById('daemon-completed');
    elements.daemonFailed = document.getElementById('daemon-failed');
    elements.daemonSuccessRate = document.getElementById('daemon-success-rate');
    elements.daemonCurrentCycle = document.getElementById('daemon-current-cycle');
    elements.daemonEventsCount = document.getElementById('daemon-events-count');
    elements.daemonTimeline = document.getElementById('daemon-timeline');
    elements.daemonStrategicInfo = document.getElementById('daemon-strategic-info');
    elements.daemonBadge = document.getElementById('daemon-badge');

    // Buttons
    elements.refreshHealthBtn = document.getElementById('refresh-health');
    elements.refreshDaemonBtn = document.getElementById('refresh-daemon');
  }

  // ============================================================================
  // Theme Management
  // ============================================================================

  function loadThemePreference() {
    const savedTheme = localStorage.getItem(CONFIG.THEME_STORAGE_KEY);
    if (savedTheme === 'light') {
      document.body.classList.add('theme--light');
    }
  }

  function toggleTheme() {
    const isLight = document.body.classList.toggle('theme--light');
    localStorage.setItem(CONFIG.THEME_STORAGE_KEY, isLight ? 'light' : 'dark');
  }

  // ============================================================================
  // Cached State Management
  // ============================================================================

  function loadCachedState() {
    try {
      const cached = localStorage.getItem(CONFIG.STATE_STORAGE_KEY);
      if (cached) {
        state.cachedData = JSON.parse(cached);
        // Render cached data immediately for instant display
        if (state.cachedData) {
          renderAllPanels(state.cachedData);
        }
      }
    } catch (e) {
      console.warn('Failed to load cached state:', e);
    }
  }

  function saveCachedState(data) {
    try {
      state.cachedData = data;
      localStorage.setItem(CONFIG.STATE_STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn('Failed to save cached state:', e);
    }
  }

  // ============================================================================
  // Event Listeners
  // ============================================================================

  function setupEventListeners() {
    // Tab navigation
    elements.navItems.forEach(function(item) {
      item.addEventListener('click', function() {
        navigateToPanel(this.getAttribute('data-panel'));
      });
    });

    // Refresh button
    if (elements.refreshHealthBtn) {
      elements.refreshHealthBtn.addEventListener('click', function() {
        fetchInitialData();
      });
    }

    // Daemon refresh button
    if (elements.refreshDaemonBtn) {
      elements.refreshDaemonBtn.addEventListener('click', function() {
        fetchDaemonData();
      });
    }

    // Theme toggle (if element exists)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', toggleTheme);
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
      // Press 'r' to refresh
      if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const activeElement = document.activeElement;
        if (activeElement.tagName !== 'INPUT' && activeElement.tagName !== 'TEXTAREA') {
          fetchInitialData();
        }
      }
    });
  }

  // ============================================================================
  // Tab Navigation
  // ============================================================================

  function navigateToPanel(panelId) {
    state.currentPanel = panelId;

    // Update active nav item
    elements.navItems.forEach(function(nav) {
      nav.classList.remove('nav__item--active');
      if (nav.getAttribute('data-panel') === panelId) {
        nav.classList.add('nav__item--active');
      }
    });

    // Show corresponding panel
    elements.panels.forEach(function(panel) {
      panel.classList.remove('panel--active');
    });

    const targetPanel = document.getElementById(panelId + '-panel');
    if (targetPanel) {
      targetPanel.classList.add('panel--active');
    }

    // Lazy-load daemon data when panel is activated
    if (panelId === 'daemon') {
      fetchDaemonData();
    }
  }

  // ============================================================================
  // SSE Connection Management
  // ============================================================================

  function connectSSE() {
    if (state.eventSource) {
      state.eventSource.close();
    }

    try {
      state.eventSource = new EventSource(CONFIG.SSE_ENDPOINT);

      state.eventSource.onopen = function() {
        state.isConnected = true;
        state.reconnectAttempts = 0;
        updateConnectionStatus('connected');
        startHeartbeatMonitor();
      };

      state.eventSource.onmessage = function(event) {
        handleSSEMessage(event);
      };

      state.eventSource.onerror = function() {
        state.isConnected = false;
        updateConnectionStatus('disconnected');
        scheduleReconnect();
      };

      // Custom event handlers
      state.eventSource.addEventListener('full', function(event) {
        handleFullUpdate(JSON.parse(event.data));
      });

      state.eventSource.addEventListener('update', function(event) {
        handlePartialUpdate(JSON.parse(event.data));
      });

      state.eventSource.addEventListener('heartbeat', function(event) {
        handleHeartbeat(JSON.parse(event.data));
      });

    } catch (e) {
      console.error('Failed to connect to SSE:', e);
      updateConnectionStatus('error');
      scheduleReconnect();
    }
  }

  function scheduleReconnect() {
    if (state.reconnectTimeout) {
      clearTimeout(state.reconnectTimeout);
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, ... up to 30s
    const delay = Math.min(
      CONFIG.RECONNECT_BASE_DELAY * Math.pow(2, state.reconnectAttempts),
      CONFIG.RECONNECT_MAX_DELAY
    );

    updateConnectionStatus('reconnecting', delay);

    state.reconnectTimeout = setTimeout(function() {
      state.reconnectAttempts++;
      connectSSE();
    }, delay);
  }

  function startHeartbeatMonitor() {
    if (state.heartbeatTimer) {
      clearTimeout(state.heartbeatTimer);
    }

    state.lastHeartbeat = Date.now();

    state.heartbeatTimer = setInterval(function() {
      const elapsed = Date.now() - state.lastHeartbeat;
      if (elapsed > CONFIG.HEARTBEAT_TIMEOUT) {
        console.warn('Heartbeat timeout, reconnecting...');
        state.isConnected = false;
        updateConnectionStatus('timeout');
        if (state.eventSource) {
          state.eventSource.close();
        }
        scheduleReconnect();
      }
    }, CONFIG.HEARTBEAT_TIMEOUT / 2);
  }

  // ============================================================================
  // SSE Message Handlers
  // ============================================================================

  function handleSSEMessage(event) {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'full':
          handleFullUpdate(data.payload);
          break;
        case 'update':
          handlePartialUpdate(data.payload);
          break;
        case 'heartbeat':
          handleHeartbeat(data);
          break;
        default:
          console.warn('Unknown message type:', data.type);
      }
    } catch (e) {
      console.error('Failed to parse SSE message:', e);
    }
  }

  function handleFullUpdate(data) {
    saveCachedState(data);
    renderAllPanels(data);
    updateTimestamp();
  }

  function handlePartialUpdate(data) {
    // Merge partial update with cached data
    if (state.cachedData) {
      Object.assign(state.cachedData, data);
    } else {
      state.cachedData = data;
    }
    saveCachedState(state.cachedData);

    // Only render affected panels
    if (data.health !== undefined) {
      renderHealth(data.health);
    }
    if (data.progress !== undefined) {
      renderProgress(data.progress);
    }
    if (data.workforce !== undefined) {
      renderWorkforce(data.workforce);
    }
    if (data.roadmap !== undefined) {
      renderRoadmap(data.roadmap);
    }
    if (data.errors !== undefined || data.escalations !== undefined) {
      renderErrors(data);
    }

    // Refresh daemon panel if it's active and daemon.log changed
    if (data.changed_files) {
      var daemonLogChanged = data.changed_files.some(function(f) {
        return f.indexOf('daemon.log') !== -1;
      });
      if (daemonLogChanged && state.currentPanel === 'daemon') {
        fetchDaemonData();
      }
    }

    updateTimestamp();
  }

  function handleHeartbeat(data) {
    state.lastHeartbeat = Date.now();

    // Update daemon status if provided
    if (data.daemon_status) {
      updateDaemonStatus(data.daemon_status);
    }
  }

  // ============================================================================
  // Connection Status UI
  // ============================================================================

  function updateConnectionStatus(status, reconnectDelay) {
    if (!elements.connectionIndicator || !elements.connectionText) return;

    // Remove all status classes
    elements.connectionIndicator.classList.remove(
      'connection-status__indicator--connected',
      'connection-status__indicator--disconnected',
      'connection-status__indicator--reconnecting',
      'connection-status__indicator--error'
    );

    switch (status) {
      case 'connected':
        elements.connectionIndicator.classList.add('connection-status__indicator--connected');
        elements.connectionText.textContent = 'Connected';
        break;
      case 'disconnected':
        elements.connectionIndicator.classList.add('connection-status__indicator--disconnected');
        elements.connectionText.textContent = 'Disconnected';
        break;
      case 'reconnecting':
        elements.connectionIndicator.classList.add('connection-status__indicator--reconnecting');
        const seconds = Math.round(reconnectDelay / 1000);
        elements.connectionText.textContent = 'Reconnecting in ' + seconds + 's...';
        break;
      case 'timeout':
        elements.connectionIndicator.classList.add('connection-status__indicator--error');
        elements.connectionText.textContent = 'Connection timeout';
        break;
      case 'error':
        elements.connectionIndicator.classList.add('connection-status__indicator--error');
        elements.connectionText.textContent = 'Connection error';
        break;
    }
  }

  function updateTimestamp() {
    if (!elements.lastUpdateTime) return;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    elements.lastUpdateTime.textContent = timeStr;
  }

  function updateDaemonStatus(status) {
    if (!elements.daemonStatus || !elements.daemonStatusText) return;

    elements.daemonStatus.classList.remove(
      'footer__daemon-status--running',
      'footer__daemon-status--stopped',
      'footer__daemon-status--error'
    );

    if (status === 'running') {
      elements.daemonStatus.classList.add('footer__daemon-status--running');
      elements.daemonStatusText.textContent = 'Running';
    } else if (status === 'stopped') {
      elements.daemonStatus.classList.add('footer__daemon-status--stopped');
      elements.daemonStatusText.textContent = 'Stopped';
    } else {
      elements.daemonStatus.classList.add('footer__daemon-status--error');
      elements.daemonStatusText.textContent = status || 'Unknown';
    }
  }

  // ============================================================================
  // Initial Data Fetch
  // ============================================================================

  function fetchInitialData() {
    fetch(CONFIG.API_ENDPOINT)
      .then(function(response) {
        if (!response.ok) {
          throw new Error('HTTP error ' + response.status);
        }
        return response.json();
      })
      .then(function(data) {
        handleFullUpdate(data);
      })
      .catch(function(error) {
        console.error('Failed to fetch initial data:', error);
        // If we have cached data, continue using it
        if (!state.cachedData) {
          showErrorMessage('Failed to load dashboard data. Retrying...');
        }
      });
  }

  // ============================================================================
  // Panel Rendering
  // ============================================================================

  function renderAllPanels(data) {
    if (!data) return;

    if (data.health) {
      renderHealth(data.health);
    }
    if (data.progress) {
      renderProgress(data.progress);
    }
    if (data.workforce) {
      renderWorkforce(data.workforce);
    }
    if (data.roadmap) {
      renderRoadmap(data.roadmap);
    }
    if (data.errors || data.escalations) {
      renderErrors(data);
    }
  }

  // ============================================================================
  // Health Panel Rendering
  // ============================================================================

  function renderHealth(data) {
    if (!data) return;

    // Update health score gauge
    if (data.score !== undefined) {
      updateHealthGauge(data.score);
    }

    // Update health factors
    if (data.factors && elements.healthFactors) {
      renderHealthFactors(data.factors);
    }
  }

  function updateHealthGauge(score) {
    if (!elements.healthScore || !elements.healthProgress) return;

    const circumference = 2 * Math.PI * 80;
    const offset = circumference - (score / 100) * circumference;

    elements.healthProgress.style.strokeDasharray = circumference;
    elements.healthProgress.style.strokeDashoffset = offset;

    // Update color based on score
    elements.healthProgress.classList.remove(
      'health-gauge__progress--warning',
      'health-gauge__progress--critical'
    );

    if (score < 60) {
      elements.healthProgress.classList.add('health-gauge__progress--critical');
    } else if (score < 80) {
      elements.healthProgress.classList.add('health-gauge__progress--warning');
    }

    elements.healthScore.textContent = Math.round(score);
  }

  function renderHealthFactors(factors) {
    if (!elements.healthFactors) return;

    let html = '';

    factors.forEach(function(factor) {
      const statusClass = getProgressBarClass(factor.value, factor.inverted);

      html += '<div class="progress-item">' +
        '<div class="progress-item__header">' +
          '<span class="progress-item__label">' + escapeHtml(factor.label) + '</span>' +
          '<span class="progress-item__value">' + factor.value + '%</span>' +
        '</div>' +
        '<div class="progress-bar">' +
          '<div class="progress-bar__fill ' + statusClass + '" style="width: ' + factor.value + '%"></div>' +
        '</div>' +
      '</div>';
    });

    elements.healthFactors.innerHTML = html;
  }

  function getProgressBarClass(value, inverted) {
    // For inverted metrics (like escalation rate), lower is better
    if (inverted) {
      if (value > 30) return 'progress-bar__fill--error';
      if (value > 15) return 'progress-bar__fill--warning';
      return 'progress-bar__fill--success';
    }

    // Normal metrics - higher is better
    if (value >= 80) return 'progress-bar__fill--success';
    if (value >= 60) return 'progress-bar__fill--warning';
    return 'progress-bar__fill--error';
  }

  // ============================================================================
  // Progress Panel Rendering
  // ============================================================================

  function renderProgress(data) {
    if (!data) return;

    // Update task counts
    if (data.pending !== undefined && elements.tasksPending) {
      elements.tasksPending.textContent = data.pending;
    }
    if (data.active !== undefined && elements.tasksActive) {
      elements.tasksActive.textContent = data.active;
    }
    if (data.blocked !== undefined && elements.tasksBlocked) {
      elements.tasksBlocked.textContent = data.blocked;
    }
    if (data.completed !== undefined && elements.tasksCompleted) {
      elements.tasksCompleted.textContent = data.completed;
    }

    // Update tasks badge
    if (elements.tasksBadge) {
      const activeCount = data.active || 0;
      if (activeCount > 0) {
        elements.tasksBadge.textContent = activeCount;
        elements.tasksBadge.style.display = 'inline';
      } else {
        elements.tasksBadge.style.display = 'none';
      }
    }

    // Update velocity metrics
    if (data.velocity) {
      if (data.velocity.daily !== undefined && elements.velocityDaily) {
        elements.velocityDaily.textContent = data.velocity.daily.toFixed(1);
      }
      if (data.velocity.weekly !== undefined && elements.velocityWeekly) {
        elements.velocityWeekly.textContent = data.velocity.weekly;
      }
      if (data.velocity.trend !== undefined && elements.velocityTrend) {
        const trendValue = data.velocity.trend;
        const prefix = trendValue >= 0 ? '+' : '';
        elements.velocityTrend.textContent = prefix + trendValue + '%';
      }
    }
  }

  // ============================================================================
  // Workforce Panel Rendering
  // ============================================================================

  function renderWorkforce(data) {
    if (!data) return;

    // Update economics summary if provided
    if (data.economics && elements.economicsSummary) {
      renderEconomicsSummary(data.economics);
    }

    // Update departments and employees
    if (data.departments && elements.departmentsContainer) {
      renderDepartments(data.departments);
    }
  }

  function renderEconomicsSummary(economics) {
    if (!elements.economicsSummary) return;

    let html = '';

    if (economics.total_budget !== undefined) {
      html += '<div class="economics-item">' +
        '<div class="economics-item__value">' + formatCurrency(economics.total_budget) + '</div>' +
        '<div class="economics-item__label">Total Budget</div>' +
      '</div>';
    }

    if (economics.spent !== undefined) {
      html += '<div class="economics-item">' +
        '<div class="economics-item__value">' + formatCurrency(economics.spent) + '</div>' +
        '<div class="economics-item__label">Spent</div>' +
      '</div>';
    }

    if (economics.remaining !== undefined) {
      html += '<div class="economics-item">' +
        '<div class="economics-item__value">' + formatCurrency(economics.remaining) + '</div>' +
        '<div class="economics-item__label">Remaining</div>' +
      '</div>';
    }

    if (economics.utilization !== undefined) {
      html += '<div class="economics-item">' +
        '<div class="economics-item__value">' + economics.utilization + '%</div>' +
        '<div class="economics-item__label">Utilization</div>' +
      '</div>';
    }

    elements.economicsSummary.innerHTML = html;
  }

  function renderDepartments(departments) {
    if (!elements.departmentsContainer) return;

    let html = '';

    departments.forEach(function(dept) {
      html += '<div class="department">' +
        '<div class="department__header">' +
          '<h3 class="department__title">' + escapeHtml(dept.name) + '</h3>' +
          '<span class="department__count">' + dept.employees.length + ' members</span>' +
        '</div>' +
        '<div class="grid grid--auto">';

      dept.employees.forEach(function(emp) {
        html += renderEmployeeCard(emp);
      });

      html += '</div></div>';
    });

    elements.departmentsContainer.innerHTML = html;
  }

  function renderEmployeeCard(employee) {
    const initials = getInitials(employee.name);
    const statusClass = 'employee-card__status--' + (employee.status || 'offline');
    const statusText = capitalizeFirst(employee.status || 'offline');

    return '<div class="employee-card">' +
      '<div class="employee-card__avatar">' + initials + '</div>' +
      '<div class="employee-card__info">' +
        '<div class="employee-card__name">' + escapeHtml(employee.name) + '</div>' +
        '<div class="employee-card__role">' + escapeHtml(employee.role) + '</div>' +
      '</div>' +
      '<span class="employee-card__status ' + statusClass + '">' + statusText + '</span>' +
    '</div>';
  }

  // ============================================================================
  // Roadmap Panel Rendering
  // ============================================================================

  function renderRoadmap(data) {
    if (!data || !elements.phaseList) return;

    let html = '';

    data.phases.forEach(function(phase) {
      const statusClass = 'phase-item__status--' + phase.status;
      const progressClass = phase.progress === 100 ? 'progress-bar__fill--success' : '';

      html += '<div class="phase-item">' +
        '<div class="phase-item__header">' +
          '<h3 class="phase-item__title">' + escapeHtml(phase.name) + '</h3>' +
          '<span class="phase-item__status ' + statusClass + '">' + getStatusLabel(phase.status) + '</span>' +
        '</div>' +
        '<div class="phase-item__meta">' +
          '<span>' + phase.task_count + ' tasks</span>' +
          '<span>' + (phase.target_date ? 'Target: ' + phase.target_date : '') + '</span>' +
        '</div>' +
        '<div class="phase-item__progress">' +
          '<div class="progress-item">' +
            '<div class="progress-item__header">' +
              '<span class="progress-item__label">Progress</span>' +
              '<span class="progress-item__value">' + phase.progress + '%</span>' +
            '</div>' +
            '<div class="progress-bar">' +
              '<div class="progress-bar__fill ' + progressClass + '" style="width: ' + phase.progress + '%"></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    });

    elements.phaseList.innerHTML = html;
  }

  function getStatusLabel(status) {
    switch (status) {
      case 'completed': return 'Completed';
      case 'active': return 'In Progress';
      case 'pending': return 'Pending';
      default: return capitalizeFirst(status);
    }
  }

  // ============================================================================
  // Errors Panel Rendering
  // ============================================================================

  function renderErrors(data) {
    if (!data) return;

    // Render escalations table
    if (data.escalations && elements.escalationsTable) {
      renderEscalationsTable(data.escalations);
    }

    // Render error timeline
    if (data.errors && elements.errorTimeline) {
      renderErrorTimeline(data.errors);
    }

    // Update error badge
    updateErrorBadge(data.escalations);
  }

  function renderEscalationsTable(escalations) {
    const tbody = elements.escalationsTable.querySelector('tbody');
    if (!tbody) return;

    let html = '';

    if (escalations.length === 0) {
      html = '<tr><td colspan="5" class="table__empty">No active escalations</td></tr>';
    } else {
      escalations.forEach(function(esc) {
        const severityClass = getSeverityBadgeClass(esc.severity);

        html += '<tr>' +
          '<td>' + escapeHtml(esc.id) + '</td>' +
          '<td>' + escapeHtml(esc.type) + '</td>' +
          '<td><span class="badge ' + severityClass + '">' + escapeHtml(esc.severity) + '</span></td>' +
          '<td>' + escapeHtml(esc.assigned || '-') + '</td>' +
          '<td>' + formatAge(esc.created_at) + '</td>' +
        '</tr>';
      });
    }

    tbody.innerHTML = html;

    // Update escalation count badge
    if (elements.escalationCount) {
      elements.escalationCount.textContent = escalations.length;
    }
  }

  function renderErrorTimeline(errors) {
    if (!elements.errorTimeline) return;

    let html = '';
    const shouldScroll = errors.length > 0;
    const previousFirstId = elements.errorTimeline.querySelector('.timeline__item')?.getAttribute('data-id');

    errors.forEach(function(error, index) {
      const markerClass = getTimelineMarkerClass(error.level);
      const isNew = index === 0 && error.id !== previousFirstId;

      html += '<div class="timeline__item' + (isNew ? ' timeline__item--new' : '') + '" data-id="' + (error.id || index) + '">' +
        '<div class="timeline__marker ' + markerClass + '"></div>' +
        '<div class="timeline__time">' + formatTime(error.timestamp) + '</div>' +
        '<div class="timeline__content">' +
          '<div class="timeline__title">' + escapeHtml(error.title) + '</div>' +
          '<div class="timeline__description">' + escapeHtml(error.description) + '</div>' +
        '</div>' +
      '</div>';
    });

    elements.errorTimeline.innerHTML = html;

    // Auto-scroll to new errors if panel is active
    if (shouldScroll && state.currentPanel === 'errors') {
      const newItem = elements.errorTimeline.querySelector('.timeline__item--new');
      if (newItem) {
        newItem.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  function updateErrorBadge(escalations) {
    if (!elements.errorsBadge) return;

    const count = escalations ? escalations.length : 0;
    if (count > 0) {
      elements.errorsBadge.textContent = count;
      elements.errorsBadge.style.display = 'inline';
    } else {
      elements.errorsBadge.style.display = 'none';
    }
  }

  function getSeverityBadgeClass(severity) {
    switch ((severity || '').toLowerCase()) {
      case 'critical': return 'badge--error';
      case 'high': return 'badge--error';
      case 'medium': return 'badge--warning';
      case 'low': return 'badge--info';
      default: return 'badge--info';
    }
  }

  function getTimelineMarkerClass(level) {
    switch ((level || '').toLowerCase()) {
      case 'error': return 'timeline__marker--error';
      case 'warning': return 'timeline__marker--warning';
      case 'info': return 'timeline__marker--info';
      default: return '';
    }
  }

  // ============================================================================
  // Daemon Panel
  // ============================================================================

  function fetchDaemonData() {
    fetch('/api/daemon')
      .then(function(response) {
        if (!response.ok) {
          throw new Error('HTTP error ' + response.status);
        }
        return response.json();
      })
      .then(function(data) {
        if (data.success) {
          renderDaemon(data);
        }
      })
      .catch(function(error) {
        console.error('Failed to fetch daemon data:', error);
      });
  }

  function renderDaemon(data) {
    if (!data) return;

    // Status indicator
    if (elements.daemonRunningIndicator) {
      elements.daemonRunningIndicator.classList.remove(
        'daemon-status-indicator--running',
        'daemon-status-indicator--stopped'
      );
      if (data.status === 'running') {
        elements.daemonRunningIndicator.classList.add('daemon-status-indicator--running');
      } else {
        elements.daemonRunningIndicator.classList.add('daemon-status-indicator--stopped');
      }
    }

    if (elements.daemonRunningText) {
      elements.daemonRunningText.textContent = data.status === 'running' ? 'Running' : 'Stopped';
    }

    // PID
    if (elements.daemonPidValue) {
      elements.daemonPidValue.textContent = data.pid || '--';
    }

    // Uptime
    if (elements.daemonUptimeValue) {
      elements.daemonUptimeValue.textContent = data.uptime_seconds
        ? formatDuration(data.uptime_seconds)
        : '--';
    }

    // Heartbeat
    if (elements.daemonHeartbeatValue) {
      if (data.heartbeat_age_seconds !== null && data.heartbeat_age_seconds !== undefined) {
        elements.daemonHeartbeatValue.textContent = data.heartbeat_age_seconds + 's ago';
        if (data.heartbeat_age_seconds > 120) {
          elements.daemonHeartbeatValue.style.color = 'var(--status-error)';
        } else {
          elements.daemonHeartbeatValue.style.color = '';
        }
      } else {
        elements.daemonHeartbeatValue.textContent = '--';
      }
    }

    // Stat cards
    var lifetime = data.lifetime || {};
    if (elements.daemonCompleted) {
      elements.daemonCompleted.textContent = lifetime.completed || 0;
    }
    if (elements.daemonFailed) {
      elements.daemonFailed.textContent = lifetime.failed || 0;
    }
    if (elements.daemonSuccessRate) {
      var rate = lifetime.success_rate;
      elements.daemonSuccessRate.textContent = (rate !== undefined && rate !== null)
        ? Math.round(rate * 100) + '%'
        : '--';
    }
    if (elements.daemonCurrentCycle) {
      elements.daemonCurrentCycle.textContent = data.current_cycle || 0;
    }

    // Update daemon badge with current cycle
    if (elements.daemonBadge && data.status === 'running') {
      elements.daemonBadge.textContent = 'C' + (data.current_cycle || 0);
      elements.daemonBadge.style.display = 'inline';
    }

    // Timeline
    if (elements.daemonTimeline && data.recent_events) {
      renderDaemonTimeline(data.recent_events);
      if (elements.daemonEventsCount) {
        elements.daemonEventsCount.textContent = data.recent_events.length + ' events';
      }
    }

    // Strategic planning
    if (elements.daemonStrategicInfo && data.strategic_planning) {
      renderStrategicPlanning(data.strategic_planning);
    }

    // Update footer daemon status
    updateDaemonStatus(data.status);
  }

  function renderDaemonTimeline(events) {
    if (!elements.daemonTimeline || !events || events.length === 0) return;

    var html = '';
    events.forEach(function(event) {
      var markerClass = getDaemonMarkerClass(event.type);
      var timeStr = '';
      if (event.timestamp) {
        try {
          var dt = new Date(event.timestamp);
          timeStr = dt.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
        } catch (e) {
          timeStr = event.timestamp.substring(11, 16);
        }
      }

      html += '<div class="timeline__item">' +
        '<div class="timeline__marker ' + markerClass + '"></div>' +
        '<div class="timeline__time">' + timeStr + '</div>' +
        '<div class="timeline__content">' +
          '<div class="timeline__title">' + escapeHtml(event.title || '') + '</div>';

      if (event.detail) {
        html += '<div class="timeline__description">' + escapeHtml(event.detail) + '</div>';
      }
      if (event.employee) {
        html += '<div class="timeline__description">' + escapeHtml(event.employee) + '</div>';
      }
      if (event.error) {
        html += '<div class="timeline__description text-error">' + escapeHtml(event.error) + '</div>';
      }

      html += '</div></div>';
    });

    elements.daemonTimeline.innerHTML = html;
  }

  function getDaemonMarkerClass(type) {
    switch (type) {
      case 'task_completed': return 'timeline__marker--completed';
      case 'task_failed': return 'timeline__marker--failed';
      case 'strategic_planning': return 'timeline__marker--strategic';
      case 'strategic_result': return 'timeline__marker--strategic';
      case 'executive_loop': return 'timeline__marker--executive';
      case 'proactive_scan': return 'timeline__marker--scan';
      case 'cycle_start': return 'timeline__marker--cycle';
      case 'cycle_done': return 'timeline__marker--cycle';
      case 'roadmap_schedule': return 'timeline__marker--roadmap';
      default: return 'timeline__marker--info';
    }
  }

  function renderStrategicPlanning(sp) {
    if (!elements.daemonStrategicInfo || !sp) return;

    var durationStr = sp.duration_seconds
      ? formatDuration(sp.duration_seconds)
      : 'Unknown';

    var lastRunStr = '';
    if (sp.last_run) {
      try {
        var dt = new Date(sp.last_run);
        lastRunStr = dt.toLocaleTimeString('en-US', { hour12: false });
      } catch (e) {
        lastRunStr = sp.last_run;
      }
    }

    var html = '<div class="strategic-summary">' +
      '<div class="strategic-summary__item">' +
        '<div class="strategic-summary__value">' + lastRunStr + '</div>' +
        '<div class="strategic-summary__label">Last Run</div>' +
      '</div>' +
      '<div class="strategic-summary__item">' +
        '<div class="strategic-summary__value">' + durationStr + '</div>' +
        '<div class="strategic-summary__label">Duration</div>' +
      '</div>' +
      '<div class="strategic-summary__item">' +
        '<div class="strategic-summary__value">' + (sp.initiatives_proposed || 0) + '</div>' +
        '<div class="strategic-summary__label">Initiatives</div>' +
      '</div>' +
      '<div class="strategic-summary__item">' +
        '<div class="strategic-summary__value">' + (sp.tasks_queued || 0) + '</div>' +
        '<div class="strategic-summary__label">Tasks Queued</div>' +
      '</div>' +
    '</div>';

    elements.daemonStrategicInfo.innerHTML = html;
  }

  function formatDuration(seconds) {
    if (seconds < 60) return seconds + 's';
    if (seconds < 3600) {
      var mins = Math.floor(seconds / 60);
      var secs = seconds % 60;
      return mins + 'm ' + secs + 's';
    }
    var hours = Math.floor(seconds / 3600);
    var mins = Math.floor((seconds % 3600) / 60);
    return hours + 'h ' + mins + 'm';
  }

  // ============================================================================
  // Utility Functions
  // ============================================================================

  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  function formatCurrency(value) {
    if (typeof value !== 'number') return '$0';
    return '$' + value.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    });
  }

  function formatAge(timestamp) {
    if (!timestamp) return '-';

    const created = new Date(timestamp);
    const now = new Date();
    const diffMs = now - created;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 60) {
      return diffMins + 'm';
    }

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return hours + 'h ' + mins + 'm';
  }

  function formatTime(timestamp) {
    if (!timestamp) return '--:--:--';

    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour12: false });
  }

  function getInitials(name) {
    if (!name) return '??';

    const words = name.split(/[\s-]+/);
    if (words.length >= 2) {
      return (words[0][0] + words[words.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  function capitalizeFirst(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  }

  function showErrorMessage(message) {
    // Simple error display - could be enhanced with a toast system
    console.error(message);
  }

  // ============================================================================
  // Public API (for debugging)
  // ============================================================================

  window.ForgeDashboard = {
    getState: function() { return state; },
    getCachedData: function() { return state.cachedData; },
    reconnect: connectSSE,
    refresh: fetchInitialData,
    toggleTheme: toggleTheme,
    navigateToPanel: navigateToPanel
  };

  // ============================================================================
  // Initialize on DOM Ready
  // ============================================================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
